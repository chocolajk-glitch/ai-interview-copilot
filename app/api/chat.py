"""聊天路由（HTTP handler）。"""
import json
import time

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.llm.factory import chat, get_llm
from app.models import Feedback, get_db
from app.rag.chain import ask as rag_ask
from app.rag.chain import astream as rag_astream
from app.schemas.chat import (
    AgentAskRequest,
    AgentAskResponse,
    AskRequest,
    AskResponse,
    ChatRequest,
    ChatResponse,
    FeedbackRequest,
    FeedbackResponse,
    StreamAskRequest,
)


_NO_INFO_PATTERNS = (
    "无相关", "无相关信息", "没有找到", "没有找到相关", "未提供", "未找到",
    "文档中没有", "抱歉", "不能回答", "无法回答", "无法基于", "不能基于",
    "未提及", "没有提到", "不涉及", "不相关", "无关", "仅有",
)


def _is_no_info_answer(answer: str) -> bool:
    """检测 LLM 是否给出了"无相关信息"式的回答。

    这种情况下不应再发 citations，否则用户会看到 LLM 明明说没找到，
    却还挂着几条引用源，造成认知冲突（"你好"被挂着 Leetcode.md 引用）。
    """
    if not answer:
        return False
    head = answer[:300]  # 只看开头
    return any(p in head for p in _NO_INFO_PATTERNS)

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/test", response_model=ChatResponse)
async def chat_test(req: ChatRequest) -> ChatResponse:
    provider = req.provider or settings.LLM_PROVIDER
    start = time.perf_counter()
    try:
        reply = chat(req.message, provider=provider, temperature=req.temperature)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM 调用失败: {str(e)[:200]}")
    latency_ms = int((time.perf_counter() - start) * 1000)

    llm = get_llm(provider, temperature=req.temperature)
    model_name = getattr(llm, "model", None) or getattr(llm, "model_name", "?")

    return ChatResponse(
        reply=reply,
        provider=provider,
        model=model_name,
    )


@router.post("/ask", response_model=AskResponse)
async def chat_ask(req: AskRequest) -> AskResponse:
    from app.core.config import settings as cfg
    provider = req.provider or cfg.LLM_PROVIDER
    try:
        result = rag_ask(
            req.question,
            provider=provider,
            k=req.top_k,
            session_id=req.session_id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG 问答失败: {str(e)[:200]}")
    return AskResponse(
        answer=result["answer"],
        citations=result["citations"],
        provider=provider,
    )


@router.post(
    "/stream",
    response_class=StreamingResponse,
    responses={
        200: {
            "content": {"text/event-stream": {}},
            "description": "SSE stream of RAG answer",
        }
    },
)
async def chat_stream(req: StreamAskRequest):
    from app.core.config import settings as cfg
    provider = req.provider or cfg.LLM_PROVIDER

    async def event_generator():
        async for event in rag_astream(
            req.question,
            provider=provider,
            k=req.top_k,
            session_id=req.session_id,
        ):
            if event["type"] == "chunk":
                payload = json.dumps({"chunk": event["content"]}, ensure_ascii=False)
                yield f"data: {payload}\n\n"
            elif event["type"] == "citations":
                payload = json.dumps({"citations": event["citations"]}, ensure_ascii=False)
                yield f"data: {payload}\n\n"
            elif event["type"] == "done":
                yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/history/{session_id}")
async def get_history(session_id: str) -> dict:
    """调试端点：查看某个 session 的对话历史，用于排查记忆问题。"""
    from app.memory import get_history_store
    store = get_history_store()
    msgs = store.get_messages(session_id)
    return {
        "session_id": session_id,
        "backend": settings.HISTORY_BACKEND,
        "count": len(msgs),
        "messages": [
            {"type": m.type, "content": m.content}
            for m in msgs
        ],
    }


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    req: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
) -> FeedbackResponse:
    """用户反馈端点：👍/👎 评分 + 可选文字反馈。"""
    fb = Feedback(
        session_id=req.session_id,
        question=req.question,
        answer=req.answer,
        rating=req.rating,
        comment=req.comment,
    )
    db.add(fb)
    await db.commit()
    return FeedbackResponse(message="反馈已记录")


@router.post("/agent", response_model=AgentAskResponse)
async def chat_agent(req: AgentAskRequest) -> AgentAskResponse:
    """Agentic RAG 端点：LangGraph 4 节点状态图（query_analyzer → 路由 → retriever → reranker → generator）。"""
    from app.core.config import settings as cfg
    from app.graph.workflow import get_workflow

    provider = req.provider or cfg.LLM_PROVIDER
    try:
        result = get_workflow().invoke({
            "question": req.question,
            "rewritten_query": "",
            "provider": provider,
            "k": req.top_k,
            "session_id": req.session_id,
            "docs": [],
            "citations": [],
            "answer": "",
            "intent": "factual",
            "reflection_count": 0,
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent 问答失败: {str(e)[:200]}")
    return AgentAskResponse(
        answer=result["answer"],
        intent=result["intent"],
        citations=result["citations"],
        provider=provider,
    )


@router.post(
    "/agent/stream",
    response_class=StreamingResponse,
    responses={
        200: {
            "content": {"text/event-stream": {}},
            "description": "SSE stream of Agentic RAG answer",
        }
    },
)
async def chat_agent_stream(req: StreamAskRequest):
    """Agentic RAG 流式端点：先走 LangGraph 状态图拿到意图和检索结果，再流式生成答案。"""
    from app.core.config import settings as cfg
    from app.graph.nodes import query_analyzer, query_rewriter, retriever, reranker_node, generator
    from app.graph.nodes import _load_history, _format_history
    from app.rag.citations import extract_citations, format_docs_with_citations

    provider = req.provider or cfg.LLM_PROVIDER

    # 加载对话历史
    history = _load_history(req.session_id)
    history_text = _format_history(history)
    logger.info(
        f"[chat_agent_stream] session={req.session_id!r} loaded {len(history)} history msgs "
        f"(question={req.question!r})"
    )

    # 1. 意图分析（同步，很快）
    state = {
        "question": req.question,
        "rewritten_query": "",
        "provider": provider,
        "k": req.top_k,
        "session_id": req.session_id,
        "docs": [],
        "citations": [],
        "answer": "",
        "intent": "factual",
        "reflection_count": 0,
    }
    state = query_analyzer(state)

    # 2. 查询改写（结合对话历史补全追问）
    if state["intent"] != "chat":
        state = query_rewriter(state)

    # 3. 检索 + Rerank（同步）
    if state["intent"] != "chat":
        state = retriever(state)
        state = reranker_node(state)

    # 3. 流式生成
    async def event_generator():
        # 发送意图
        yield f"data: {json.dumps({'intent': state['intent']}, ensure_ascii=False)}\n\n"

        from langchain_core.output_parsers import StrOutputParser
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.messages import AIMessage, HumanMessage

        has_docs = bool(state.get("docs"))

        if state["intent"] == "chat":
            prompt = ChatPromptTemplate.from_template(
                "根据对话历史，回答用户的问题。\n\n{chat_history}\n\n【用户】\n{question}"
            )
        elif not has_docs:
            # 没召回任何文档：fallback 到 chat + history（用对话上下文回答）
            prompt = ChatPromptTemplate.from_template(
                "根据对话历史，回答用户的问题。\n\n{chat_history}\n\n【用户】\n{question}"
            )
        else:
            context = format_docs_with_citations(state["docs"])
            prompt = ChatPromptTemplate.from_template(
                "你是 AI 面试助手。基于以下文档内容回答用户问题。\n"
                "{chat_history}\n"
                "【文档内容】\n{context}\n\n【用户问题】\n{question}\n\n"
                "1. 严格基于文档内容回答，不要编造\n2. 回答中引用的事实点用 [1] [2] [3] 标注来源"
            )

        llm = get_llm(provider)
        chain = prompt | llm | StrOutputParser()

        invoke_kwargs = {"question": req.question, "chat_history": history_text}
        if state["intent"] != "chat" and state.get("docs"):
            invoke_kwargs["context"] = context

        full_answer = ""
        async for chunk in chain.astream(invoke_kwargs):
            full_answer += chunk
            yield f"data: {json.dumps({'chunk': chunk}, ensure_ascii=False)}\n\n"

        # 发送引用：仅在 RAG 真正用到了 doc 且 LLM 没明确说"无相关"时发送
        if has_docs and not _is_no_info_answer(full_answer):
            citations = extract_citations(state["docs"])
            yield f"data: {json.dumps({'citations': citations}, ensure_ascii=False)}\n\n"

        # 保存到对话历史
        if req.session_id:
            from app.memory import get_history_store
            store = get_history_store()
            store.add_message(req.session_id, HumanMessage(content=req.question))
            store.add_message(req.session_id, AIMessage(content=full_answer))
            logger.info(
                f"[chat_agent_stream] session={req.session_id!r} saved 2 msgs "
                f"(answer_len={len(full_answer)})"
            )

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )