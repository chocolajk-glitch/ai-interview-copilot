"""文档加载器统一入口：根据文件后缀自动选择加载器。"""
from pathlib import Path

from langchain_core.documents import Document

from app.rag.loaders.markdown_loader import load_markdown_docs
from app.rag.loaders.pdf_loader import load_pdf, load_pdf_docs
from app.rag.loaders.html_loader import load_html, load_html_docs


def load_docs(corpus_dir: str | Path) -> list[Document]:
    """加载目录下所有支持的文档（md / pdf / html）。

    Args:
        corpus_dir: 语料目录路径

    Returns:
        Document 列表
    """
    corpus_dir = Path(corpus_dir)
    docs: list[Document] = []

    # Markdown
    md_files = list(corpus_dir.glob("**/*.md"))
    if md_files:
        docs.extend(load_markdown_docs(corpus_dir))

    # PDF
    pdf_files = list(corpus_dir.glob("**/*.pdf"))
    if pdf_files:
        docs.extend(load_pdf_docs(corpus_dir))

    # HTML
    html_files = list(corpus_dir.glob("**/*.html"))
    if html_files:
        docs.extend(load_html_docs(corpus_dir))

    return docs


def load_single_file(file_path: str | Path, filename: str = "") -> list[Document]:
    """根据文件后缀选择加载器加载单个文件。

    Args:
        file_path: 文件路径
        filename: 原始文件名（用于 metadata）

    Returns:
        Document 列表
    """
    ext = Path(filename or file_path).suffix.lower()
    if ext == ".pdf":
        return load_pdf(file_path)
    elif ext in (".html", ".htm"):
        return [load_html(file_path)]
    else:
        # 默认当文本处理
        from langchain_core.document_loaders import TextLoader
        loader = TextLoader(str(file_path), encoding="utf-8")
        return loader.load()
