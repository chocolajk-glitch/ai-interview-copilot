"""RAGAS 评估模块：离线评估 RAG 管线的忠实度/相关性/精确率/召回率。"""
import json
from pathlib import Path

from app.core.config import settings
from app.core.logging import logger

# === Monkey-patch: 兼容 transformers 5.x（移除 prepare_for_model） ===
# 旧版 transformers 的 XLMRobertaTokenizer.prepare_for_model 在 4.43+ 被移除，
# 但 sentence-transformers / FlagEmbedding 仍依赖它。
# 这里给 PreTrainedTokenizerBase 补一个 shim：把 [q_ids, d_ids] 拼接成 [CLS] q [SEP] d [SEP]，
# 截断到 max_length，返回带 attention_mask / token_type_ids 的 BatchEncoding。
try:
    from transformers.tokenization_utils_base import PreTrainedTokenizerBase, BatchEncoding
    if not hasattr(PreTrainedTokenizerBase, "prepare_for_model"):
        def _prepare_for_model(
            self,
            ids,
            pair_ids=None,
            add_special_tokens=True,
            padding=None,  # noqa: ARG001
            truncation=None,
            max_length=None,
            stride=0,  # noqa: ARG001
            return_tensors=None,
            return_token_type_ids=None,
            return_attention_mask=None,
            return_overflowing_tokens=False,  # noqa: ARG001
            return_special_tokens_mask=False,  # noqa: ARG001
            return_offsets_mapping=False,  # noqa: ARG001
            return_length=False,  # noqa: ARG001
            verbose=True,  # noqa: ARG001
            prepend_batch_axis=False,
            **kwargs,  # noqa: ARG001
        ):
            # 1) 拼接 special tokens（XLM-RoBERTa 默认 [CLS] ids [SEP] / [CLS] ids [SEP] pair_ids [SEP]）
            if add_special_tokens:
                # 找 cls/sep token ids（XLM-RoBERTa 标准：<s>=0, </s>=2）
                cls_id = (
                    self.cls_token_id
                    if self.cls_token_id is not None
                    else self.bos_token_id
                )
                sep_id = (
                    self.sep_token_id
                    if self.sep_token_id is not None
                    else self.eos_token_id
                )
                if pair_ids is not None:
                    combined = [cls_id] + list(ids) + [sep_id] + list(pair_ids) + [sep_id]
                    q_len = 1 + len(ids) + 1
                    # XLM-RoBERTa 只有 1 个 token_type（type_vocab_size=1），全填 0
                    type_ids = [0] * len(combined)
                else:
                    combined = [cls_id] + list(ids) + [sep_id]
                    type_ids = [0] * len(combined)
            else:
                combined = list(ids) + (list(pair_ids) if pair_ids else [])
                type_ids = [0] * len(combined)

            # 2) 截断
            if max_length is not None and truncation in (True, "longest_first", "only_first", "only_second"):
                if len(combined) > max_length:
                    if truncation == "only_second" and pair_ids is not None:
                        # 保留 q 部分（CLS + ids + SEP），截断 pair
                        q_with_special = [cls_id] + list(ids) + [sep_id]
                        if len(q_with_special) > max_length:
                            combined = q_with_special[:max_length]
                            type_ids = type_ids[:max_length]
                        else:
                            remaining = max_length - len(q_with_special)
                            combined = q_with_special + list(pair_ids)[:remaining]
                            type_ids = type_ids[:len(q_with_special)] + [0] * remaining
                    else:
                        combined = combined[:max_length]
                        type_ids = type_ids[:max_length]

            # 3) 构造返回
            result = {
                "input_ids": combined,
                "attention_mask": [1] * len(combined),
            }
            if return_token_type_ids is None or return_token_type_ids:
                result["token_type_ids"] = type_ids

            # 4) 转 tensor
            if return_tensors is not None and return_tensors != "np":
                try:
                    import torch  # noqa: PLC0415
                    result = {k: torch.as_tensor(v) for k, v in result.items()}
                except Exception:
                    pass

            if prepend_batch_axis and isinstance(result.get("input_ids"), list):
                if result["input_ids"] and not isinstance(result["input_ids"][0], list):
                    result["input_ids"] = [result["input_ids"]]
                    result["attention_mask"] = [result["attention_mask"]]
                    if "token_type_ids" in result:
                        result["token_type_ids"] = [result["token_type_ids"]]

            return BatchEncoding(result)
        PreTrainedTokenizerBase.prepare_for_model = _prepare_for_model
        logger.info("Monkey-patched PreTrainedTokenizerBase.prepare_for_model (shim for transformers 5.x)")
except Exception as _e:
    logger.warning(f"prepare_for_model monkey-patch 失败: {_e}")
# === End monkey-patch ===

_EVAL_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "eval"


def load_qa_dataset(path: str | Path | None = None) -> list[dict]:
    """加载评估数据集。"""
    path = Path(path) if path else _EVAL_DATA_DIR / "qa_dataset.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


async def run_ragas_eval(
    questions: list[str] | None = None,
    provider: str | None = None,
    sample_size: int | None = None,
) -> dict:
    """运行 RAGAS 评估，返回四个核心指标。

    Args:
        questions: 指定评估的问题列表（None=用全量数据集）
        provider: LLM 提供商（用于 RAG 生成答案）
        sample_size: 随机抽样数量（None=全量）

    Returns:
        {
            "faithfulness": float,
            "answer_relevancy": float,
            "context_precision": float,
            "context_recall": float,
            "sample_count": int,
        }
    """
    from datasets import Dataset
    from ragas import evaluate
    from ragas.metrics import (
        faithfulness,
        answer_relevancy,
        context_precision,
        context_recall,
    )

    # 加载数据集
    qa_data = load_qa_dataset()

    # 过滤：只评估有 expected_source 的问题（排除 chitchat/adversarial）
    qa_data = [q for q in qa_data if q.get("expected_source") != "none"]

    if questions:
        qa_set = {q for q in questions}
        qa_data = [q for q in qa_data if q["question"] in qa_set]

    if sample_size and sample_size < len(qa_data):
        import random
        qa_data = random.sample(qa_data, sample_size)

    # 用 RAG 管线生成答案和检索上下文
    from app.rag.chain import _get_hybrid_retriever, _format_docs
    from app.llm.factory import get_llm
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.prompts import ChatPromptTemplate

    retriever = _get_hybrid_retriever()
    llm = get_llm(provider)

    PROMPT_TEMPLATE = """你是 AI 面试助手。基于以下文档内容回答用户问题。

【文档内容】
{context}

【用户问题】
{question}

【要求】
1. 严格基于文档内容回答，不要编造
2. 简洁、清晰、像面试官讲题
3. 如果文档没有相关内容，回答"文档中没有找到相关信息"
"""

    prompt = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    chain = prompt | llm | StrOutputParser()

    user_questions = []
    ground_truths = []
    answers = []
    contexts = []

    import time
    eval_start = time.perf_counter()
    for idx, item in enumerate(qa_data, 1):
        q = item["question"]
        gt = item["ground_truth"]

        # 检索
        docs = retriever.search(q, top_k=3)
        ctx = [d.page_content for d in docs]

        # 生成
        context_text = _format_docs(docs)
        answer = chain.invoke({"context": context_text, "question": q})

        user_questions.append(q)
        ground_truths.append(gt)
        answers.append(answer)
        contexts.append(ctx)

        elapsed = time.perf_counter() - eval_start
        logger.info(
            f"[ragas_eval] gen {idx}/{len(qa_data)} done in {elapsed:.1f}s "
            f"({elapsed/idx:.1f}s/sample) - q={q[:30]!r}"
        )

    # 构建 RAGAS 数据集
    eval_data = {
        "user_input": user_questions,
        "response": answers,
        "reference": ground_truths,
        "retrieved_contexts": contexts,
    }
    dataset = Dataset.from_dict(eval_data)

    # 用 DeepSeek 作为评判 LLM（与生成 LLM 分离更客观）
    from langchain_openai import ChatOpenAI
    judge_llm = ChatOpenAI(
        model=settings.DEEPSEEK_MODEL,
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_BASE_URL,
    )

    # 用本地 BGE embedding（避免 RAGAS 默认去调 OpenAI）
    from app.rag.embeddings.bge import get_embeddings
    judge_embeddings = get_embeddings()

    # 运行评估（RAGAS 内部对每个 metric × 每个 sample 调 judge LLM，很慢）
    logger.info(
        f"[ragas_eval] gen phase done in {time.perf_counter()-eval_start:.1f}s, "
        f"starting RAGAS evaluate on {len(qa_data)} samples × 4 metrics"
    )
    ragas_start = time.perf_counter()
    result = evaluate(
        dataset=dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        llm=judge_llm,
        embeddings=judge_embeddings,
    )
    logger.info(f"[ragas_eval] RAGAS evaluate done in {time.perf_counter()-ragas_start:.1f}s")

    # RAGAS 返回每个样本一个分数（list），取均值
    def _mean(v):
        if isinstance(v, list):
            return round(float(sum(v) / len(v)), 4) if v else 0.0
        return round(float(v), 4)

    return {
        "faithfulness": _mean(result["faithfulness"]),
        "answer_relevancy": _mean(result["answer_relevancy"]),
        "context_precision": _mean(result["context_precision"]),
        "context_recall": _mean(result["context_recall"]),
        "sample_count": len(qa_data),
    }
