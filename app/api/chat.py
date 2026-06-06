"""聊天路由（HTTP handler）。"""
import time
from app.rag.chain import ask as rag_ask
from app.schemas.chat import AskRequest, AskResponse
from fastapi import APIRouter, HTTPException
import json
from fastapi.responses import StreamingResponse
from app.rag.chain import astream as rag_astream
from app.schemas.chat import StreamAskRequest
from app.core.config import settings
from app.llm.factory import chat, get_llm
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/test", response_model=ChatResponse)
async def chat_test(req: ChatRequest) -> ChatResponse:
    """单轮聊天测试接口：传 message + provider，返回 AI 回复。"""
    provider = req.provider or settings.LLM_PROVIDER
    start = time.perf_counter()
    try:
        reply = chat(req.message, provider=provider, temperature=req.temperature)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM 调用失败: {str(e)[:200]}")
    latency_ms = int((time.perf_counter() - start) * 1000)

    # 拿实际 model 名（ChatTongyi 用 model_name，ChatDeepSeek 用 model）
    llm = get_llm(provider, temperature=req.temperature)
    model_name = getattr(llm, 'model', None) or getattr(llm, 'model_name', '?')

    return ChatResponse(
        reply=reply,
        provider=provider,
        model=model_name,
    )

@router.post("/ask", response_model=AskResponse)
async def chat_ask(req: AskRequest) -> AskResponse:
    """RAG 问答：基于语料库检索 + LLM 生成答案（带引用）。"""
    from app.core.config import settings as cfg
    provider = req.provider or cfg.LLM_PROVIDER
    try:
        result = rag_ask(req.question, provider=provider, k=req.top_k)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG 问答失败: {str(e)[:200]}")
    return AskResponse(
        answer=result["answer"],
        sources=result["sources"],
        provider=provider,
    )

@router.post(
    "/stream",
    response_class=StreamingResponse,  # ← 新增：Swagger UI 识别 SSE
    responses={
        200: {
            "content": {"text/event-stream": {}},  # ← 新增：告诉 OpenAPI 响应类型
            "description": "SSE stream of RAG answer",
        }
    },
)
async def chat_stream(req: StreamAskRequest):
    """SSE 流式 RAG 问答：边检索边生成，chunk 级别推送。"""
    from app.core.config import settings as cfg
    provider = req.provider or cfg.LLM_PROVIDER

    async def event_generator():
        """SSE 事件生成器：把 astream() 输出转 SSE 格式。"""
        async for event in rag_astream(req.question, provider=provider, k=req.top_k):
            if event["type"] == "chunk":
                payload = json.dumps({"chunk": event["content"]}, ensure_ascii=False)
                yield f"data: {payload}\n\n"
            elif event["type"] == "sources":
                payload = json.dumps({"sources": event["sources"]}, ensure_ascii=False)
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
