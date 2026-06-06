"""RAG Chain：混合检索（BM25 + 向量 RRF）+ LLM 生成答案。"""
from pathlib import Path

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from app.llm.factory import get_llm
from app.rag.loaders.markdown_loader import load_markdown_docs
from app.rag.retrievers.hybrid_retriever import HybridRetriever
from app.rag.splitters.text_splitter import split_docs


PROMPT_TEMPLATE = """你是 AI 面试助手。基于以下文档内容回答用户问题。

【文档内容】
{context}

【用户问题】
{question}

【要求】
1. 严格基于文档内容回答，不要编造
2. 简洁、清晰、像面试官讲题
3. 如果文档没有相关内容，回答"文档中没有找到相关信息"
"""


# 单例混合检索器（懒加载）+ 绝对路径 corpus
_hybrid_retriever: HybridRetriever | None = None
_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
_CORPUS_DIR = str(_BACKEND_ROOT / "data" / "corpus")


def _get_hybrid_retriever() -> HybridRetriever:
    """懒加载单例混合检索器（首次调用构建索引）。"""
    global _hybrid_retriever
    if _hybrid_retriever is None:
        docs = load_markdown_docs(_CORPUS_DIR)
        chunks = split_docs(docs, chunk_size=500, chunk_overlap=50)
        _hybrid_retriever = HybridRetriever()
        _hybrid_retriever.index(chunks)
    return _hybrid_retriever


def _format_docs(docs) -> str:
    """把多个 Document 拼成 context 字符串。"""
    return "\n\n---\n\n".join(
        f"[来源: {d.metadata['source'].split(chr(92))[-1]}]\n{d.page_content}"
        for d in docs
    )


def _extract_sources(docs) -> list[str]:
    """提取来源文件名列表。"""
    return [d.metadata["source"].split("\\")[-1] for d in docs]


def ask(question: str, provider: str | None = None, k: int = 3) -> dict:
    """RAG 问答：混合检索 + LLM 生成答案。

    Args:
        question: 用户问题
        provider: LLM provider（None 用 settings 默认）
        k: 检索 top-k 文档数

    Returns:
        {"answer": str, "sources": list[str]}
    """
    # 1. 混合检索
    retriever = _get_hybrid_retriever()
    docs = retriever.search(question, top_k=k)
    if not docs:
        return {"answer": "文档中没有找到相关信息", "sources": []}

    # 2. 拼 Prompt
    context = _format_docs(docs)
    prompt = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)

    # 3. 调 LLM（LCEL 链式 + 自写类包装）
    llm = get_llm(provider)
    chain = prompt | llm | StrOutputParser()
    answer = chain.invoke({"context": context, "question": question})

    return {
        "answer": answer,
        "sources": _extract_sources(docs),
    }


async def astream(question: str, provider: str | None = None, k: int = 3):
    """流式 RAG 问答：异步生成器。

    Yields:
        {"type": "chunk", "content": "..."}  - LLM 输出片段（多次）
        {"type": "sources", "sources": [...]} - 检索到的文档（最后 1 次）
        {"type": "done"} - 结束标记
    """
    retriever = _get_hybrid_retriever()
    docs = retriever.search(question, top_k=k)

    if not docs:
        yield {"type": "chunk", "content": "文档中没有找到相关信息"}
        yield {"type": "done"}
        return

    context = _format_docs(docs)
    prompt = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)

    llm = get_llm(provider)
    chain = prompt | llm | StrOutputParser()

    async for chunk in chain.astream({"context": context, "question": question}):
        yield {"type": "chunk", "content": chunk}

    yield {"type": "sources", "sources": _extract_sources(docs)}
    yield {"type": "done"}