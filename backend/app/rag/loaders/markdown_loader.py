"""Markdown 文档加载器：把 .md 文件读成 LangChain Document 对象。"""
from pathlib import Path

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_core.documents import Document


def load_markdown_docs(corpus_dir: str | Path) -> list[Document]:
    """加载 corpus_dir 下所有 .md 文件。

    Args:
        corpus_dir: 语料目录路径（绝对路径或相对 cwd）

    Returns:
        Document 列表。每个 Document 含：
        - page_content: 文件文本内容
        - metadata: {"source": 绝对路径, ...}
    """
    loader = DirectoryLoader(
        path=str(corpus_dir),
        glob="**/*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
        show_progress=False,
    )
    return loader.load()