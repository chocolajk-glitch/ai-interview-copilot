"""向量检索器：基于 Chroma 的相似度检索。"""
from pathlib import Path

from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

from app.core.config import settings
from app.rag.embeddings.bge import get_embeddings

COLLECTION_NAME = "ai_interview_corpus"


def get_vector_store() -> Chroma:
    """获取/创建 Chroma 向量库。"""
    persist_dir = Path(settings.CHROMA_PERSIST_DIR).resolve()
    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=get_embeddings(),
        persist_directory=str(persist_dir),
    )


def add_documents(chunks: list[Document]) -> list[str]:
    """把 chunk 加到 Chroma，返回 id 列表。"""
    vs = get_vector_store()
    return vs.add_documents(chunks)


def similarity_search(query: str, k: int | None = None) -> list[Document]:
    """按相似度查 top-k chunk。"""
    vs = get_vector_store()
    k = k or settings.TOP_K
    return vs.similarity_search(query, k=k)