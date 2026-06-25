"""HybridRetriever 的 Parent-Child 展开行为测试。"""
from langchain_core.documents import Document

from app.rag.retrievers import hybrid_retriever as hr_module
from app.rag.retrievers.hybrid_retriever import HybridRetriever
from app.rag.retrievers.vector_retriever import reset_parent_store


def _stub_bm25_and_vector(monkeypatch, *, vector_docs):
    """stub 掉 BM25Retriever.search 与 vector_retriever.similarity_search。"""
    class _StubBM25:
        def search(self, query, k=5):
            return [(d, 1.0) for d in vector_docs[:k]]

    monkeypatch.setattr(hr_module, "BM25Retriever", lambda: _StubBM25())
    monkeypatch.setattr(hr_module, "similarity_search", lambda q, k=20: vector_docs[:k])


def test_hybrid_search_expand_parent_default(monkeypatch):
    parent = Document(
        page_content="哈希表思路\n完整上下文",
        metadata={
            "doc_kind": "parent",
            "source": "a.md",
            "chunk_id": "p1",
            "child_ids": ["c1"],
        },
    )
    child = Document(
        page_content="哈希表思路片段",
        metadata={
            "doc_kind": "child",
            "source": "a.md",
            "chunk_id": "c1",
            "parent_id": "p1",
        },
    )
    reset_parent_store([parent])
    _stub_bm25_and_vector(monkeypatch, vector_docs=[child])

    hr = HybridRetriever()
    out = hr.search("哈希表", top_k=3, use_rerank=False)
    assert len(out) == 1
    assert out[0].metadata["doc_kind"] == "parent"
    assert out[0].page_content == "哈希表思路\n完整上下文"


def test_hybrid_search_expand_parent_disabled(monkeypatch):
    parent = Document(
        page_content="PARENT_BODY",
        metadata={
            "doc_kind": "parent",
            "source": "a.md",
            "chunk_id": "p1",
            "child_ids": ["c1"],
        },
    )
    child = Document(
        page_content="CHILD_BODY",
        metadata={
            "doc_kind": "child",
            "source": "a.md",
            "chunk_id": "c1",
            "parent_id": "p1",
        },
    )
    reset_parent_store([parent])
    _stub_bm25_and_vector(monkeypatch, vector_docs=[child])

    hr = HybridRetriever()
    out = hr.search("哈希表", top_k=3, use_rerank=False, expand_parent=False)
    assert len(out) == 1
    assert out[0].page_content == "CHILD_BODY"


def test_hybrid_search_dedupes_same_parent(monkeypatch):
    parent = Document(
        page_content="FULL PARENT",
        metadata={
            "doc_kind": "parent",
            "source": "a.md",
            "chunk_id": "p1",
            "child_ids": ["c1", "c2"],
        },
    )
    c1 = Document(page_content="A", metadata={"doc_kind": "child", "source": "a.md", "chunk_id": "c1", "parent_id": "p1"})
    c2 = Document(page_content="B", metadata={"doc_kind": "child", "source": "a.md", "chunk_id": "c2", "parent_id": "p1"})
    reset_parent_store([parent])
    # BM25 和向量各召回两个 child → RRF 后两条都进 RRF top → 展开去重为 1
    _stub_bm25_and_vector(monkeypatch, vector_docs=[c1, c2])

    hr = HybridRetriever()
    out = hr.search("q", top_k=3, use_rerank=False)
    assert len(out) == 1
    assert out[0].metadata["chunk_id"] == "p1"
