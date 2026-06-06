"""文本切分器：把长 Document 切分成 chunk。"""
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


def split_docs(
    docs: list[Document],
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> list[Document]:
    """递归按分隔符优先级切分文档。

    Args:
        docs: 原始 Document 列表
        chunk_size: 每块最大字符数
        chunk_overlap: 块间重叠字符数（防止边界信息丢失）

    Returns:
        切分后的 Document 列表（保留 metadata.source）
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "。", "，", " ", ""],
    )
    return splitter.split_documents(docs)