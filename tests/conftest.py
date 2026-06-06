"""pytest 共享 fixtures。"""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client() -> TestClient:
    """FastAPI TestClient（整个测试会话共享）。"""
    return TestClient(app)