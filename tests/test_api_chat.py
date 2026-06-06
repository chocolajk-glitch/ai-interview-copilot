"""测试 HTTP API（/chat/ask 端到端，调用真实 LLM）。"""
from fastapi.testclient import TestClient


def test_ask_endpoint_success(client: TestClient):
    """POST /api/chat/ask 应返回 200 + answer + sources。"""
    r = client.post(
        "/api/chat/ask",
        json={"question": "两数之和怎么解", "provider": "deepseek", "top_k": 3},
    )
    assert r.status_code == 200
    data = r.json()
    assert "answer" in data
    assert "sources" in data
    assert len(data["sources"]) >= 1
    assert data["provider"] == "deepseek"


def test_ask_endpoint_empty_question_validation(client: TestClient):
    """空 question 应返回 422（Pydantic 校验）。"""
    r = client.post("/api/chat/ask", json={"question": "", "provider": "deepseek"})
    assert r.status_code == 422


def test_ask_endpoint_invalid_provider_validation(client: TestClient):
    """非法 provider 应返回 422。"""
    r = client.post("/api/chat/ask", json={"question": "hi", "provider": "claude"})
    assert r.status_code == 422


"""测试 HTTP API（/chat/ask 端到端，调用真实 LLM）。"""
import json
from fastapi.testclient import TestClient


def test_ask_endpoint_success(client: TestClient):
    """POST /api/chat/ask 应返回 200 + answer + sources。"""
    r = client.post(
        "/api/chat/ask",
        json={"question": "两数之和怎么解", "provider": "deepseek", "top_k": 3},
    )
    assert r.status_code == 200
    data = r.json()
    assert "answer" in data
    assert "sources" in data
    assert len(data["sources"]) >= 1
    assert data["provider"] == "deepseek"


def test_ask_endpoint_empty_question_validation(client: TestClient):
    """空 question 应返回 422（Pydantic 校验）。"""
    r = client.post("/api/chat/ask", json={"question": "", "provider": "deepseek"})
    assert r.status_code == 422


def test_ask_endpoint_invalid_provider_validation(client: TestClient):
    """非法 provider 应返回 422。"""
    r = client.post("/api/chat/ask", json={"question": "hi", "provider": "claude"})
    assert r.status_code == 422


# ---------- SSE 流式测试 ----------

def test_stream_endpoint_returns_sse_format(client: TestClient):
    """POST /api/chat/stream 应返回 text/event-stream + data: 格式。"""
    with client.stream("POST", "/api/chat/stream", json={
        "question": "两数之和怎么解", "provider": "qwen", "top_k": 3,
    }) as r:
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream"), \
            f"Content-Type 应是 text/event-stream，实际 {r.headers['content-type']}"

        chunks = []
        sources = []
        done_received = False

        for line in r.iter_lines():
            if not line.startswith("data: "):
                continue
            payload = line[6:]  # 去 "data: " 前缀
            if payload == "[DONE]":
                done_received = True
                break
            data = json.loads(payload)
            if "chunk" in data:
                chunks.append(data["chunk"])
            elif "sources" in data:
                sources = data["sources"]

        assert done_received, "必须收到 [DONE] 结束标记"
        assert len(chunks) >= 1, f"至少 1 个 chunk，实际 {len(chunks)}"
        assert sum(len(c) for c in chunks) > 0, "chunks 总长 > 0"
        assert len(sources) >= 1, "至少 1 个 source"


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