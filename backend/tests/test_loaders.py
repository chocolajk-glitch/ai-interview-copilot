"""测试 Markdown 文档加载。"""
from app.rag.loaders.markdown_loader import load_markdown_docs

CORPUS_DIR = "data/corpus"


def test_load_markdown_docs_returns_5_documents():
    """加载 corpus 目录应返回 5 个 Document。"""
    docs = load_markdown_docs(CORPUS_DIR)
    assert len(docs) == 5
    for doc in docs:
        assert doc.page_content  # 非空
        assert "source" in doc.metadata
        assert doc.metadata["source"].endswith(".md")