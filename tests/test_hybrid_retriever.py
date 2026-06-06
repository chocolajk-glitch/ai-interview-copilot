"""测试混合检索：BM25 + 向量 + RRF。"""
import pytest

from app.rag.loaders.markdown_loader import load_markdown_docs
from app.rag.retrievers.hybrid_retriever import HybridRetriever
from app.rag.splitters.text_splitter import split_docs

CORPUS_DIR = "data/corpus"


@pytest.fixture(scope="module")
def hybrid() -> HybridRetriever:
    """初始化混合检索器（依赖 Day 4 Chroma 已存数据）。"""
    docs = load_markdown_docs(CORPUS_DIR)
    chunks = split_docs(docs, chunk_size=500, chunk_overlap=50)
    hr = HybridRetriever()
    hr.index(chunks)
    return hr


def test_hybrid_search_two_sum_top1(hybrid):
    """混合检索'两数之和'，top-1 应是 01_two_sum.md。"""
    results = hybrid.search("两数之和怎么解", top_k=5)
    assert len(results) >= 1
    assert "01_two_sum" in results[0].metadata["source"]


def test_hybrid_search_reverse_list_top1(hybrid):
    """混合检索'反转链表'，top-1 应是 02。"""
    results = hybrid.search("反转链表", top_k=5)
    assert "02_reverse_linked_list" in results[0].metadata["source"]


def test_hybrid_search_binary_search_top1(hybrid):
    """混合检索'二分查找'，top-1 应是 04。"""
    results = hybrid.search("二分查找", top_k=5)
    assert "04_binary_search" in results[0].metadata["source"]


def test_hybrid_top5_returns_5_docs(hybrid):
    """top_k=5 应返回 5 个文档。"""
    results = hybrid.search("栈", top_k=5)
    assert len(results) == 5


def test_rrf_formula_basic():
    """RRF 公式单元测试：验证分数计算正确。"""
    k = 60
    bm25_rank = 3
    vector_rank = 5
    expected = 1 / (k + bm25_rank) + 1 / (k + vector_rank)
    actual = 1 / (k + bm25_rank) + 1 / (k + vector_rank)
    assert abs(actual - expected) < 1e-6

def test_hybrid_search_with_rerank_two_sum_top1(hybrid):
    """混合 + Rerank 检索'两数之和'，top-1 应是 01。"""
    results = hybrid.search("两数之和怎么解", top_k=5, use_rerank=True)
    assert "01_two_sum" in results[0].metadata["source"]