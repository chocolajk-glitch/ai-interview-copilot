"""BGE Reranker 精排：基于 flagembedding 库。"""
from functools import lru_cache

from FlagEmbedding import FlagReranker

from app.core.config import settings


@lru_cache
def get_reranker() -> FlagReranker:
    """单例 BGE Reranker（首次调用加载模型，1-3 秒）。"""
    return FlagReranker(
        model_name_or_path=settings.RERANK_MODEL,
        use_fp16=True,  # 半精度（显存减半，速度快 2x，质量损失 < 1%）
    )


def rerank(query: str, documents: list, top_k: int | None = None) -> list:
    """对 documents 重排序（按相关性降序），返回 top_k 文档。

    Args:
        query: 查询文本
        documents: Document 列表（已经过 RRF 粗筛的 top-20）
        top_k: 返回的文档数（None = 全部）

    Returns:
        重排序后的 Document 列表（按 Reranker 分数降序）
    """
    if not documents:
        return []
    reranker = get_reranker()
    # 构造 (query, doc) pairs
    pairs = [[query, doc.page_content] for doc in documents]
    scores = reranker.compute_score(pairs)
    # 按分数降序排序
    sorted_docs = sorted(zip(documents, scores), key=lambda x: x[1], reverse=True)
    if top_k is not None:
        sorted_docs = sorted_docs[:top_k]
    return [doc for doc, _ in sorted_docs]