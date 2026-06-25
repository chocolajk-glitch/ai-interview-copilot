from typing import Literal

from langchain_core.documents import Document
from typing_extensions import TypedDict


class GraphState(TypedDict):
    question: str
    rewritten_query: str  # 改写后的查询（用于检索）
    intent: Literal["factual", "code", "chat"]
    provider: str | None
    k: int
    session_id: str | None
    docs: list[Document]
    citations: list[dict]
    answer: str
    reflection_count: int  # reflection 已执行次数
    need_retry: bool  # 显式重试信号，替代隐式清空 answer
    retry_strategy: Literal["expand_k", "rewrite_query", "hyde", "fallback"]
    reflection_log: list[dict]  # 结构化反思日志，最后落盘到 data/logs
