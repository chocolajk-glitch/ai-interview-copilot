
"""向量检索器：基于 Chroma 的相似度检索（lazy auto-build + 单例缓存）。"""
from pathlib import Path

from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

from app.core.config import settings
from app.rag.embeddings.bge import get_embeddings

COLLECTION_NAME = "ai_interview_corpus"


def _corpus_dir() -> str:
    return str(Path(settings.CHROMA_PERSIST_DIR).resolve().parent / "corpus")


_vector_store: Chroma | None = None


def get_vector_store() -> Chroma:
    global _vector_store
    if _vector_store is None:
        persist_dir = Path(settings.CHROMA_PERSIST_DIR).resolve()
        _vector_store = Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=get_embeddings(),
            persist_directory=str(persist_dir),
        )
        if _vector_store._collection.count() == 0:
            from app.rag.loaders.markdown_loader import load_markdown_docs
            from app.rag.splitters.text_splitter import split_docs
            docs = load_markdown_docs(_corpus_dir())
            chunks = split_docs(docs, chunk_size=500, chunk_overlap=50)
            _vector_store.add_documents(chunks)
    return _vector_store


def add_documents(chunks: list[Document]) -> list[str]:
    vs = get_vector_store()
    return vs.add_documents(chunks)


def similarity_search(query: str, k: int | None = None) -> list[Document]:
    vs = get_vector_store()
    k = k or settings.TOP_K
    return vs.similarity_search(query, k=k)
