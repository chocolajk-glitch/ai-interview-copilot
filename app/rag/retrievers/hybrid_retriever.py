"""混合检索器：BM25 + 向量 + Rerank 精排。"""
from langchain_core.documents import Document

from app.rag.retrievers.bm25_retriever import BM25Retriever
from app.rag.retrievers.vector_retriever import similarity_search


class HybridRetriever:
    """BM25 + 向量混合检索，RRF 融合 + Rerank 精排。"""

    def __init__(self, k: int = 60):
        self._bm25 = BM25Retriever()
        self._k = k

    def index(self, docs: list[Document]) -> None:
        self._bm25.index(docs)

    def search(
        self,
        query: str,
        top_k: int = 5,
        bm25_k: int = 20,
        vector_k: int = 20,
        use_rerank: bool = True,
    ) -> list[Document]:
        """混合检索：BM25 + 向量 → RRF → Rerank → top_k。

        Args:
            query: 查询文本
            top_k: 最终返回文档数
            bm25_k: BM25 召回数
            vector_k: 向量召回数
            use_rerank: 是否启用 Rerank 精排（默认 True）
        """
        # 1. BM25 召回
        bm25_results = self._bm25.search(query, k=bm25_k)
        bm25_rank = {id(doc): rank for rank, (doc, _) in enumerate(bm25_results)}

        # 2. 向量召回
        vector_results = similarity_search(query, k=vector_k)
        vector_rank = {id(doc): rank for rank, doc in enumerate(vector_results)}

        # 3. 合并 + RRF 融合
        all_docs: dict[int, Document] = {}
        for doc, _ in bm25_results:
            all_docs[id(doc)] = doc
        for doc in vector_results:
            if id(doc) not in all_docs:
                all_docs[id(doc)] = doc

        rrf_scores: dict[int, float] = {}
        for doc_id in all_docs:
            bm25_r = bm25_rank.get(doc_id, bm25_k)
            vector_r = vector_rank.get(doc_id, vector_k)
            rrf_scores[doc_id] = 1 / (self._k + bm25_r) + 1 / (self._k + vector_r)

        # 4. RRF top-20 给 Rerank 精排
        rrf_top_ids = sorted(rrf_scores.keys(), key=lambda i: rrf_scores[i], reverse=True)[:20]
        rrf_top_docs = [all_docs[doc_id] for doc_id in rrf_top_ids]

        # 5. Rerank 精排（可选）
        if use_rerank and len(rrf_top_docs) > top_k:
            from app.rag.rerankers.bge_reranker import rerank
            return rerank(query, rrf_top_docs, top_k=top_k)
        return rrf_top_docs[:top_k]