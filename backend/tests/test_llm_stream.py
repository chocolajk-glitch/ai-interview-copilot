"""测试 LLM 流式输出：FallbackChatModel.stream / astream / chain.astream。"""
from langchain_core.messages import AIMessageChunk

from app.llm.factory import FallbackChatModel, get_llm


def test_stream_returns_multiple_chunks():
    """Qwen 同步流式：应 yield 多个 AIMessageChunk。"""
    llm = get_llm("qwen")
    assert isinstance(llm, FallbackChatModel)

    chunks = list(llm.stream("用一句话介绍 Python"))

    assert len(chunks) > 1, f"流式应 yield 多个 chunk，实际 {len(chunks)}"
    assert all(isinstance(c, AIMessageChunk) for c in chunks)
    assert sum(len(c.content) for c in chunks) > 0


async def test_astream_returns_multiple_chunks():
    """MiniMax 异步流式：应 yield 多个 AIMessageChunk。"""
    llm = get_llm("minimax")
    assert isinstance(llm, FallbackChatModel)

    chunks = []
    async for chunk in llm.astream("1+1等于几"):
        chunks.append(chunk)

    assert len(chunks) > 1, f"流式应 yield 多个 chunk，实际 {len(chunks)}"
    assert all(isinstance(c, AIMessageChunk) for c in chunks)


async def test_chain_astream_yields_chunk_citations_done():
    """RAG chain.astream 端到端：应 yield chunk + citations + done 三种事件。"""
    from app.rag.chain import astream

    events = []
    async for event in astream("两数之和怎么解", provider="qwen", k=3):
        events.append(event)

    types = [e["type"] for e in events]
    assert "chunk" in types, "必须 yield chunk 事件"
    assert "citations" in types, "必须 yield citations 事件"
    assert "done" in types, "必须 yield done 事件"

    chunks = [e for e in events if e["type"] == "chunk"]
    assert len(chunks) >= 1, "至少 1 个 chunk"

    citations_event = next(e for e in events if e["type"] == "citations")
    assert "01_two_sum" in str(citations_event["citations"]), "citations 应包含 two_sum.md"