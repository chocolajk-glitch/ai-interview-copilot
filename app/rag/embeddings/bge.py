"""BGE Embedding 模型：把文本转成向量（单例懒加载 + SHA-256 缓存）。"""
from functools import lru_cache

from langchain_huggingface import HuggingFaceEmbeddings

from app.core.config import settings
from app.rag.cache.embedding_cache import create_embedding_cache


@lru_cache
def get_embeddings():
    base = HuggingFaceEmbeddings(
        model_name=settings.EMBEDDING_MODEL,
        model_kwargs={"device": settings.EMBEDDING_DEVICE},
        encode_kwargs={"normalize_embeddings": True},
    )
    return create_embedding_cache(base)
