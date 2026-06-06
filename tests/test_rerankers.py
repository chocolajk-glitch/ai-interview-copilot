"""测试 BGE Reranker 精排。"""
import pytest

from app.rag.loaders.markdown_loader import load_markdown_docs
from app.rag.rerankers.bge_reranker import rerank
from app.rag.splitters.text_splitter import split_docs

CORPUS_DIR = "data/corpus"


@pytest.fixture(scope="module")
def chunks():
    docs = load_markdown_docs(CORPUS_DIR)
    return split_docs(docs, chunk_size=500, chunk_overlap=50)


def test_rerank_two_sum_top1(chunks):
    """Rerank '两数之和'，top-1 应是 01_two_sum.md。"""
    results = rerank("两数之和怎么解", chunks, top_k=5)
    assert "01_two_sum" in results[0].metadata["source"]


def test_rerank_returns_fewer_than_input(chunks):
    """Rerank top_k=5 应返回 ≤ 5 个。"""
    results = rerank("栈", chunks, top_k=5)
    assert len(results) <= 5


def test_rerank_empty_input():
    """空输入应返回空列表。"""
    results = rerank("test", [], top_k=5)
    assert results == []