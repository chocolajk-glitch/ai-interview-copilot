"""PDF 文档加载器：把 .pdf 文件读成 LangChain Document 对象。"""
from pathlib import Path

from langchain_core.documents import Document
from pypdf import PdfReader


def load_pdf(file_path: str | Path) -> list[Document]:
    """加载单个 PDF 文件。

    Args:
        file_path: PDF 文件路径

    Returns:
        Document 列表，每个 Document 对应 PDF 的一页
    """
    reader = PdfReader(str(file_path))
    docs = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text and text.strip():
            docs.append(Document(
                page_content=text,
                metadata={"source": str(file_path), "page": i + 1},
            ))
    return docs


def load_pdf_docs(directory: str | Path) -> list[Document]:
    """加载目录下所有 .pdf 文件。"""
    directory = Path(directory)
    docs = []
    for pdf_path in directory.glob("**/*.pdf"):
        docs.extend(load_pdf(pdf_path))
    return docs
