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
