"""测试文档切分。"""
from app.rag.loaders.markdown_loader import load_markdown_docs
from app.rag.splitters.text_splitter import split_docs

CORPUS_DIR = "data/corpus"


def test_split_docs_returns_expected_chunk_count():
    """5 道题 12 chunk 附近（允许 ±2）。"""
    docs = load_markdown_docs(CORPUS_DIR)
    chunks = split_docs(docs, chunk_size=500, chunk_overlap=50)
    assert 10 <= len(chunks) <= 15


def test_chunks_preserve_source_metadata():
    """切分后 chunk 应保留 source metadata（用于引用展示）。"""
    docs = load_markdown_docs(CORPUS_DIR)
    chunks = split_docs(docs)
    for chunk in chunks:
        assert "source" in chunk.metadata