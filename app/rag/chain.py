"""基础 RAG Chain：检索 + 拼 Prompt + 调 LLM + 提取答案。"""
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough

from app.core.config import settings
from app.llm.factory import get_llm
from app.rag.retrievers.vector_retriever import similarity_search


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
    """RAG 问答：检索 + LLM 生成答案。"""
    # 1. 检索
    docs = similarity_search(question, k=k)
    if not docs:
        return {
            "answer": "文档中没有找到相关信息",
            "sources": [],
        }

    # 2. 拼 Prompt
    context = _format_docs(docs)
    prompt = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)

    # 3. 调 LLM（LCEL 链式）
    llm = get_llm(provider)
    if not hasattr(llm, "stream") and not hasattr(llm, "astream"):
        # 自写类（OpenAICompatModel）不是 Runnable，包一下
        from langchain_core.runnables import Runnable
        if not isinstance(llm, Runnable):
            llm = llm.as_runnable()
    chain = prompt | llm | StrOutputParser()
    answer = chain.invoke({"context": context, "question": question})

    # 4. 返回结果
    return {
        "answer": answer,
        "sources": _extract_sources(docs),
    }