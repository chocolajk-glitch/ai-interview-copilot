"""评估路由：RAGAS 离线评估接口。"""
import asyncio
import json
import time

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.logging import logger
from app.eval import load_qa_dataset, run_ragas_eval

router = APIRouter(prefix="/api/eval", tags=["eval"])


class EvalRequest(BaseModel):
    provider: str | None = Field(default=None, description="LLM 提供商（None=默认）")
    sample_size: int | None = Field(default=None, ge=1, le=50, description="抽样数量（None=全量）")


class EvalResponse(BaseModel):
    faithfulness: float = Field(..., description="忠实度")
    answer_relevancy: float = Field(..., description="答案相关性")
    context_precision: float = Field(..., description="上下文精确率")
    context_recall: float = Field(..., description="上下文召回率")
    sample_count: int = Field(..., description="评估样本数")


class DatasetInfoResponse(BaseModel):
    total: int
    categories: dict[str, int]


@router.get("/dataset", response_model=DatasetInfoResponse)
async def get_dataset_info() -> DatasetInfoResponse:
    """查看评估数据集概况。"""
    data = load_qa_dataset()
    categories: dict[str, int] = {}
    for item in data:
        cat = item.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1
    return DatasetInfoResponse(total=len(data), categories=categories)


@router.post("/run", response_model=EvalResponse)
async def run_eval(req: EvalRequest) -> EvalResponse:
    """运行 RAGAS 评估（耗时操作，建议 sample_size <= 10 快速验证）。"""
    try:
        result = await run_ragas_eval(
            provider=req.provider,
            sample_size=req.sample_size,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"评估失败: {str(e)[:200]}")
    return EvalResponse(**result)


@router.post("/run/stream")
async def run_eval_stream(req: EvalRequest):
    """流式评估：每完成一个 sample 推送一次进度事件，最后给结果。

    避免前端 axios 60s 超时；用户能实时看到「3/5 已完成」。
    """
    from app.eval.ragas_eval import (
        _EVAL_DATA_DIR,
        load_qa_dataset,
    )
    from datasets import Dataset
    from ragas import evaluate
    from ragas.metrics import (
        answer_relevancy,
        context_precision,
        context_recall,
        faithfulness,
    )
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_openai import ChatOpenAI

    from app.core.config import settings
    from app.llm.factory import get_llm
    from app.rag.chain import _format_docs, _get_hybrid_retriever
    from app.rag.embeddings.bge import get_embeddings

    def _event(payload: dict) -> str:
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    async def event_generator():
        # 1. 准备数据
        qa_data = load_qa_dataset()
        qa_data = [q for q in qa_data if q.get("expected_source") != "none"]
        if req.sample_size and req.sample_size < len(qa_data):
            import random
            qa_data = random.sample(qa_data, req.sample_size)

        yield _event({
            "type": "start",
            "total": len(qa_data),
            "phase": "gen",
        })

        # 2. 生成阶段：RAG 检索 + LLM 答
        retriever = _get_hybrid_retriever()
        llm = get_llm(req.provider)
        prompt = ChatPromptTemplate.from_template(
            "你是 AI 面试助手。基于以下文档内容回答用户问题。\n\n"
            "【文档内容】\n{context}\n\n【用户问题】\n{question}\n\n"
            "1. 严格基于文档内容回答，不要编造\n2. 简洁、清晰、像面试官讲题\n"
            "3. 如果文档没有相关内容，回答'文档中没有找到相关信息'"
        )
        chain = prompt | llm | StrOutputParser()

        user_questions, ground_truths, answers, contexts = [], [], [], []
        eval_start = time.perf_counter()
        for idx, item in enumerate(qa_data, 1):
            q = item["question"]
            gt = item["ground_truth"]
            docs = retriever.search(q, top_k=3)
            ctx = [d.page_content for d in docs]
            context_text = _format_docs(docs)
            answer = chain.invoke({"context": context_text, "question": q})
            user_questions.append(q)
            ground_truths.append(gt)
            answers.append(answer)
            contexts.append(ctx)
            elapsed = time.perf_counter() - eval_start
            yield _event({
                "type": "progress",
                "phase": "gen",
                "current": idx,
                "total": len(qa_data),
                "elapsed_sec": round(elapsed, 1),
                "message": f"生成 {idx}/{len(qa_data)}",
            })

        # 3. RAGAS 评估阶段
        eval_data = {
            "user_input": user_questions,
            "response": answers,
            "reference": ground_truths,
            "retrieved_contexts": contexts,
        }
        dataset = Dataset.from_dict(eval_data)

        judge_llm = ChatOpenAI(
            model=settings.DEEPSEEK_MODEL,
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
        )
        judge_embeddings = get_embeddings()

        yield _event({
            "type": "phase_change",
            "phase": "ragas",
            "message": "开始 RAGAS 指标计算（最慢的阶段）",
        })
        ragas_start = time.perf_counter()

        # RAGAS evaluate 在内部跑 4 个 metric × N 个 sample，对每个都调 judge LLM。
        # 这是个 CPU 密集 + I/O 密集的阻塞调用，丢到线程池里跑。
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                None,
                lambda: evaluate(
                    dataset=dataset,
                    metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
                    llm=judge_llm,
                    embeddings=judge_embeddings,
                ),
            )
        except Exception as e:
            logger.error(f"[eval/stream] RAGAS evaluate failed: {e!r}")
            yield _event({"type": "error", "message": f"RAGAS 评估失败: {str(e)[:200]}"})
            return

        ragas_elapsed = time.perf_counter() - ragas_start
        logger.info(f"[eval/stream] RAGAS done in {ragas_elapsed:.1f}s")

        def _mean(v):
            if isinstance(v, list):
                return round(float(sum(v) / len(v)), 4) if v else 0.0
            return round(float(v), 4)

        final = {
            "faithfulness": _mean(result["faithfulness"]),
            "answer_relevancy": _mean(result["answer_relevancy"]),
            "context_precision": _mean(result["context_precision"]),
            "context_recall": _mean(result["context_recall"]),
            "sample_count": len(qa_data),
        }
        total_elapsed = time.perf_counter() - eval_start
        yield _event({
            "type": "result",
            "data": final,
            "total_elapsed_sec": round(total_elapsed, 1),
        })
        yield _event({"type": "done"})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
