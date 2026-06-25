"""RAGAS 评估模块测试。"""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


_EVAL_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "eval"


def test_load_qa_dataset():
    """测试数据集可以正常加载。"""
    from app.eval import load_qa_dataset
    data = load_qa_dataset()
    assert len(data) > 0
    assert "question" in data[0]
    assert "ground_truth" in data[0]
    assert "category" in data[0]


def test_load_qa_dataset_fields():
    """测试数据集字段完整性。"""
    from app.eval import load_qa_dataset
    data = load_qa_dataset()
    for item in data:
        assert "id" in item
        assert "question" in item
        assert "ground_truth" in item
        assert "category" in item
        assert "expected_source" in item


def test_eval_dataset_endpoint(client: TestClient):
    """测试 /api/eval/dataset 端点。"""
    r = client.get("/api/eval/dataset")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] > 0
    assert "categories" in data
    assert "array" in data["categories"]


def test_eval_run_endpoint_schema(client: TestClient):
    """测试 /api/eval/run 端点请求 schema 校验（不实际运行，只验证参数校验）。"""
    # sample_size 超范围
    r = client.post("/api/eval/run", json={"sample_size": 100})
    assert r.status_code == 422  # validation error
