"""RAG Chain：混合检索 + LLM 生成答案 + chunk 级引用 + 对话记忆。"""
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.llm.factory import get_llm
from app.rag.citations import extract_citations, format_docs_with_citations
from app.rag.loaders.markdown_loader import load_markdown_docs
from app.rag.retrievers.hybrid_retriever import HybridRetriever
from app.rag.splitters.text_splitter import split_docs


PROMPT_TEMPLATE = """你是 AI 面试助手。基于以下文档内容回答用户问题。

{chat_history}

【文档内容】
{context}

【用户问题】
{question}

【要求】
1. 严格基于文档内容回答，不要编造
2. 简洁、清晰、像面试官讲题
3. 如果文档没有相关内容，回答"文档中没有找到相关信息"
4. 回答中引用的事实点用 [1] [2] [3] 标注来源（编号对应文档前的 [n] 标签）
"""


CHAT_PROMPT_TEMPLATE = """根据对话历史，回答用户的问题。

{chat_history}

【用户】
{question}
"""


_NO_INFO_PATTERNS = (
    "无相关", "无相关信息", "没有找到", "没有找到相关", "未提供", "未找到",
    "文档中没有", "抱歉", "不能回答", "无法回答", "无法基于", "不能基于",
    "未提及", "没有提到", "不涉及", "不相关", "无关", "仅有",
)


def _is_no_info_answer(answer: str) -> bool:
    """检测 LLM 是否给出了"无相关信息"式的回答。

    命中时不应回传 citations，否则用户会看到 LLM 明明说没找到，
    却还挂着几条引用源，造成认知冲突。
    """
    if not answer:
        return False
    head = answer[:300]
    return any(p in head for p in _NO_INFO_PATTERNS)


_hybrid_retriever: HybridRetriever | None = None
_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
_CORPUS_DIR = str(_BACKEND_ROOT / "data" / "corpus")


def _get_hybrid_retriever() -> HybridRetriever:
    global _hybrid_retriever
    if _hybrid_retriever is None:
        docs = load_markdown_docs(_CORPUS_DIR)
        chunks = split_docs(docs, chunk_size=500, chunk_overlap=50)
        _hybrid_retriever = HybridRetriever()
        _hybrid_retriever.index(chunks)
    return _hybrid_retriever


def _classify_intent(question: str, history_text: str, provider: str | None) -> str:
    """复用 workflow 的意图分类：避免"分苹果"被错分到 factual/code。"""
    from app.graph.nodes import _quick_intent_classify
    quick = _quick_intent_classify(question)
    if quick:
        return quick

    from app.graph.nodes import query_analyzer
    state = {
        "question": question,
        "intent": "factual",  # 会被 query_analyzer 覆盖
        "provider": provider,
        "session_id": None,   # 分类器不写库
        "k": 0,
    }
    # 临时把 history_text 喂给 analyzer（analyzer 内部用 store，但也可以直接传）
    # 简化做法：跳过 store，直接用 LLM 分类
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.prompts import ChatPromptTemplate
    from app.graph.nodes import INTENT_PROMPT
    llm = get_llm(provider)
    chain = ChatPromptTemplate.from_template(INTENT_PROMPT) | llm | StrOutputParser()
    result = chain.invoke({"question": question, "chat_history": history_text}).strip().lower()
    if result not in ("factual", "code", "chat"):
        return "factual"
    return result


def _format_docs(docs) -> str:
    return format_docs_with_citations(docs)


def _format_history(messages, max_turns: int = 5) -> str:
    if not messages:
        return ""
    recent = messages[-(max_turns * 2):]
    parts = []
    for m in recent:
        role = "用户" if m.type == "human" else "AI"
        parts.append(f"{role}: {m.content}")
    return "【对话历史】\n" + "\n".join(parts) + "\n"


def _extract_citations(docs) -> list[dict]:
    return extract_citations(docs)


def _load_and_append_question(session_id: str | None, question: str):
    history = []
    if session_id:
        from app.memory import get_history_store
        store = get_history_store()
        history = store.get_messages(session_id)
        store.add_message(session_id, HumanMessage(content=question))
    return history


def _append_answer(session_id: str | None, answer: str) -> None:
    if session_id:
        from app.memory import get_history_store
        store = get_history_store()
        store.add_message(session_id, AIMessage(content=answer))


def _chat_answer(provider, question, history_text, session_id) -> str:
    """用 chat prompt + history 生成答案，落库。"""
    prompt = ChatPromptTemplate.from_template(CHAT_PROMPT_TEMPLATE)
    llm = get_llm(provider)
    chain = prompt | llm | StrOutputParser()
    answer = chain.invoke({"question": question, "chat_history": history_text})
    _append_answer(session_id, answer)
    return answer


def _rag_answer(provider, docs, question, history_text, session_id) -> str:
    """用 RAG prompt + docs 生成答案，落库。"""
    context = _format_docs(docs)
    prompt = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    llm = get_llm(provider)
    chain = prompt | llm | StrOutputParser()
    answer = chain.invoke({
        "context": context,
        "question": question,
        "chat_history": history_text,
    })
    _append_answer(session_id, answer)
    return answer


def ask(
    question: str,
    provider: str | None = None,
    k: int = 3,
    session_id: str | None = None,
) -> dict:
    history = _load_and_append_question(session_id, question)
    history_text = _format_history(history)
    intent = _classify_intent(question, history_text, provider)

    # chat 意图：直接用历史回答，跳过 RAG
    if intent == "chat":
        answer = _chat_answer(provider, question, history_text, session_id)
        return {"answer": answer, "citations": []}

    retriever = _get_hybrid_retriever()
    docs = retriever.search(question, top_k=k)

    if not docs:
        # RAG 没召回到任何 doc：fallback 到 chat + history
        answer = _chat_answer(provider, question, history_text, session_id)
        return {"answer": answer, "citations": []}

    answer = _rag_answer(provider, docs, question, history_text, session_id)
    citations = _extract_citations(docs) if not _is_no_info_answer(answer) else []
    return {
        "answer": answer,
        "citations": citations,
    }


async def astream(
    question: str,
    provider: str | None = None,
    k: int = 3,
    session_id: str | None = None,
):
    history = _load_and_append_question(session_id, question)
    history_text = _format_history(history)
    intent = _classify_intent(question, history_text, provider)

    # chat 意图：直接用历史回答，跳过 RAG
    if intent == "chat":
        prompt = ChatPromptTemplate.from_template(CHAT_PROMPT_TEMPLATE)
        llm = get_llm(provider)
        chain = prompt | llm | StrOutputParser()
        full_answer = ""
        async for chunk in chain.astream({
            "question": question,
            "chat_history": history_text,
        }):
            full_answer += chunk
            yield {"type": "chunk", "content": chunk}
        _append_answer(session_id, full_answer)
        yield {"type": "done"}
        return

    retriever = _get_hybrid_retriever()
    docs = retriever.search(question, top_k=k)

    if not docs:
        # RAG 没召回到任何 doc：fallback 到 chat + history
        prompt = ChatPromptTemplate.from_template(CHAT_PROMPT_TEMPLATE)
        llm = get_llm(provider)
        chain = prompt | llm | StrOutputParser()
        full_answer = ""
        async for chunk in chain.astream({
            "question": question,
            "chat_history": history_text,
        }):
            full_answer += chunk
            yield {"type": "chunk", "content": chunk}
        _append_answer(session_id, full_answer)
        yield {"type": "done"}
        return

    context = _format_docs(docs)
    prompt = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    llm = get_llm(provider)
    chain = prompt | llm | StrOutputParser()

    full_answer = ""
    async for chunk in chain.astream({
        "context": context,
        "question": question,
        "chat_history": history_text,
    }):
        full_answer += chunk
        yield {"type": "chunk", "content": chunk}

    _append_answer(session_id, full_answer)
    # 仅当 LLM 没明确说"无相关"时才发引用（避免"你好"挂着 Leetcode.md 引用）
    if not _is_no_info_answer(full_answer):
        yield {"type": "citations", "citations": _extract_citations(docs)}
    yield {"type": "done"}