"""BGE Embedding 模型：把文本转成向量（单例懒加载）。"""
from functools import lru_cache

from langchain_huggingface import HuggingFaceEmbeddings

from app.core.config import settings


@lru_cache
def get_embeddings() -> HuggingFaceEmbeddings:
    """单例 BGE embedding 模型（首次调用加载，后续直接返回缓存）。"""
    return HuggingFaceEmbeddings(
        model_name=settings.EMBEDDING_MODEL,
        model_kwargs={"device": settings.EMBEDDING_DEVICE},
        encode_kwargs={"normalize_embeddings": True},
    )