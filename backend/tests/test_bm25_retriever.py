"""测试 BM25 关键词检索器。"""
import pytest

from app.rag.loaders.markdown_loader import load_markdown_docs
from app.rag.retrievers.bm25_retriever import BM25Retriever
from app.rag.splitters.text_splitter import split_docs

CORPUS_DIR = "data/corpus"


@pytest.fixture(scope="module")
def bm25():
    docs = load_markdown_docs(CORPUS_DIR)
    chunks = split_docs(docs, chunk_size=500, chunk_overlap=50)
    retriever = BM25Retriever()
    retriever.index(chunks)
    return retriever


def test_bm25_search_two_sum(bm25):
    """BM25 搜'两数之和' top-1 应是 01。"""
    results = bm25.search("两数之和", k=3)
    assert "01_two_sum" in results[0][0].metadata["source"]


def test_bm25_search_keyword_hash(bm25):
    """BM25 关键词精确匹配：搜'哈希'应能找到 Two Sum（哈希表相关）。"""
    results = bm25.search("哈希", k=3)
    sources = [doc.metadata["source"] for doc, _ in results]
    assert any("01_two_sum" in s for s in sources)


def test_bm25_unindexed_raises():
    """未 index 的 retriever 调 search 应抛 ValueError。"""
    retriever = BM25Retriever()
    with pytest.raises(ValueError, match="not indexed"):
        retriever.search("test", k=3)