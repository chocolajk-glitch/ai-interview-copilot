"""pytest 共享 fixtures。"""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client() -> TestClient:
    """FastAPI TestClient（整个测试会话共享，触发 lifespan 以初始化数据库）。"""
    with TestClient(app) as c:
        yield c
