"""测试 HTTP API（/chat/ask + /chat/stream 端到端，调用真实 LLM）。"""
import json
from fastapi.testclient import TestClient


def test_ask_endpoint_success(client: TestClient):
    """POST /api/chat/ask 应返回 200 + answer + citations。"""
    r = client.post(
        "/api/chat/ask",
        json={"question": "两数之和怎么解", "provider": "deepseek", "top_k": 3},
    )
    assert r.status_code == 200
    data = r.json()
    assert "answer" in data
    assert "citations" in data
    assert len(data["citations"]) >= 1
    c0 = data["citations"][0]
    assert "index" in c0
    assert "chunk_id" in c0
    assert "source" in c0
    assert "position" in c0
    assert "end" in c0
    assert data["provider"] == "deepseek"


def test_ask_endpoint_empty_question_validation(client: TestClient):
    """空 question 应返回 422（Pydantic 校验）。"""
    r = client.post("/api/chat/ask", json={"question": "", "provider": "deepseek"})
    assert r.status_code == 422


def test_ask_endpoint_invalid_provider_validation(client: TestClient):
    """非法 provider 应返回 422。"""
    r = client.post("/api/chat/ask", json={"question": "hi", "provider": "claude"})
    assert r.status_code == 422


def test_stream_endpoint_returns_sse_format(client: TestClient):
    """POST /api/chat/stream 应返回 text/event-stream + data: 格式。"""
    with client.stream("POST", "/api/chat/stream", json={
        "question": "两数之和怎么解", "provider": "qwen", "top_k": 3,
    }) as r:
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream"), \
            f"Content-Type 应是 text/event-stream，实际 {r.headers['content-type']}"

        chunks = []
        citations = []
        done_received = False

        for line in r.iter_lines():
            if not line.startswith("data: "):
                continue
            payload = line[6:]
            if payload == "[DONE]":
                done_received = True
                break
            data = json.loads(payload)
            if "chunk" in data:
                chunks.append(data["chunk"])
            elif "citations" in data:
                citations = data["citations"]

        assert done_received, "必须收到 [DONE] 结束标记"
        assert len(chunks) >= 1, f"至少 1 个 chunk，实际 {len(chunks)}"
        assert sum(len(c) for c in chunks) > 0, "chunks 总长 > 0"
        assert len(citations) >= 1, "至少 1 个 citation"
        assert "index" in citations[0]
        assert "chunk_id" in citations[0]


def test_stream_endpoint_concatenates_to_full_answer(client: TestClient):
    """SSE 累积 chunks 应等于完整答案。"""
    with client.stream("POST", "/api/chat/stream", json={
        "question": "栈", "provider": "qwen", "top_k": 2,
    }) as r:
        assert r.status_code == 200

        full_answer = ""
        for line in r.iter_lines():
            if not line.startswith("data: "):
                continue
            payload = line[6:]
            if payload == "[DONE]":
                break
            data = json.loads(payload)
            if "chunk" in data:
                full_answer += data["chunk"]

        assert len(full_answer) > 0, "累积 chunks 应有内容"
        assert "栈" in full_answer or "括号" in full_answer, "答案应涉及栈/括号"


def test_agent_stream_memory_apple_followup(client: TestClient):
    """复现用户报告的多轮记忆 bug：

    turn 1: "三个苹果三个人怎么分"  → 闲聊
    turn 2: "六个苹果呢"              → 必须引用 turn 1 的"每人一个"

    修复前：turn 2 被分类成 factual → RAG 没 doc → "无相关信息"
    修复后：intent 提示词改进 + generator fallback 到 chat + history。
    """
    import uuid
    sid = f"mem-test-{uuid.uuid4().hex[:8]}"

    def collect(question: str) -> str:
        with client.stream("POST", "/api/chat/agent/stream", json={
            "question": question,
            "session_id": sid,
            "top_k": 3,
        }) as r:
            assert r.status_code == 200
            full = ""
            for line in r.iter_lines():
                if not line.startswith("data: "):
                    continue
                payload = line[6:]
                if payload == "[DONE]":
                    break
                data = json.loads(payload)
                if "chunk" in data:
                    full += data["chunk"]
            return full

    turn1 = collect("三个苹果三个人怎么分")
    turn2 = collect("六个苹果呢")

    # turn 1 应该是 chat 模式，没引用但给出了分法
    assert len(turn1) > 0
    # turn 2 必须引用 turn 1（"三个" / "每人" / "每人一个" / "平均" 等）
    refers = any(kw in turn2 for kw in ["三个", "每人", "之前", "刚才", "平均", "上一"])
    assert refers, (
        f"turn 2 应引用 turn 1，但完全没上下文：\n  turn1: {turn1[:200]}\n  turn2: {turn2[:200]}"
    )