"""BM25 关键词检索器（基于 rank_bm25 库，进程内内存索引）。"""
from langchain_core.documents import Document
from rank_bm25 import BM25Okapi


class BM25Retriever:
    """BM25 关键词检索器（中文用字符级分词，简化实现）。"""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        """初始化 BM25 参数。

        Args:
            k1: 词频饱和参数（1.2-2.0 常用，1.5 是经典默认）
            b: 文档长度归一化参数（0-1，0.75 是经典默认）
        """
        self._bm25: BM25Okapi | None = None
        self._docs: list[Document] = []
        self._k1 = k1
        self._b = b

    def index(self, docs: list[Document]) -> None:
        """构建 BM25 索引（内存）。"""
        self._docs = docs
        # 字符级分词（每个汉字当 1 token，去掉空格和换行）
        tokenized = [
            list(doc.page_content.replace("\n", "").replace(" ", ""))
            for doc in docs
        ]
        self._bm25 = BM25Okapi(tokenized, k1=self._k1, b=self._b)

    def search(self, query: str, k: int = 5) -> list[tuple[Document, float]]:
        """搜索 top-k 文档，返回 (Document, BM25_score) 列表。"""
        if self._bm25 is None:
            raise ValueError("BM25Retriever not indexed. Call index() first.")
        tokenized_query = list(query.replace(" ", ""))
        scores = self._bm25.get_scores(tokenized_query)
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
        return [(self._docs[i], float(scores[i])) for i in top_indices]