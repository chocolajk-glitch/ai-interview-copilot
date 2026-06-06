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