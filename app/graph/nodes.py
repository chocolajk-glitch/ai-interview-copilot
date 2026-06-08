from pathlib import Path

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage, HumanMessage

from app.memory import get_history_store
from app.llm.factory import get_llm
from app.rag.citations import extract_citations, format_docs_with_citations
from app.rag.retrievers.hybrid_retriever import HybridRetriever
from app.rag.rerankers.bge_reranker import rerank

INTENT_PROMPT = """你是问题分类器。判断问题属于以下哪类：

- factual：概念解释、原理、面试八股文（如"哈希表原理"、"TCP 三次握手"）
- code：需要看代码实现、算法题（如"两数之和怎么解"、"反转链表代码"）
- chat：闲聊、问候、生活、数学、脑筋急转弯、自我介绍（如"你好"、"三个苹果怎么分"）

注意：
1. 如果用户在追问之前讨论过的技术话题（如"代码呢"、"具体怎么实现"、"继续"），应归类为 factual 或 code，而不是 chat。
2. 如果用户在追问之前讨论过的非技术话题（闲聊、生活、数学等），应**保持与上一轮相同**的分类，不要因为有"呢"、"?"等问号词就改判为 factual。

只返回一个词：factual / code / chat

{chat_history}
【当前问题】
{question}
"""

REWRITE_PROMPT = """你是一个查询改写专家。将用户的口语化问题改写成更适合文档检索的关键词查询。

规则：
1. 如果用户在追问之前讨论过的话题，需要结合对话历史将追问补全为完整的问题
2. 提取核心概念和关键词
3. 补充可能相关的专业术语
4. 去除口语化表达
5. 保持原意不变
6. 只输出改写后的查询，不要解释

示例：
- "哈希表怎么解决冲突的" → "哈希表 冲突解决方法 链地址法 开放寻址法"
- "两数之和" → "两数之和 哈希表 数组遍历 目标值"
- 对话历史讨论了"合并K个升序链表"，用户追问"具体的代码呢" → "合并K个升序链表 代码实现 收集排序法"

{chat_history}
【当前问题】
{question}
"""

GENERATOR_PROMPT = """你是 AI 面试助手。基于以下文档内容回答用户问题。
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

CHAT_PROMPT = """根据对话历史，回答用户的问题。

{chat_history}

【用户】
{question}
"""


_hybrid_retriever: HybridRetriever | None = None


def _get_hybrid_retriever() -> HybridRetriever:
    global _hybrid_retriever
    if _hybrid_retriever is None:
        from app.rag.loaders.markdown_loader import load_markdown_docs
        from app.rag.splitters.text_splitter import split_docs
        backend_root = Path(__file__).resolve().parent.parent.parent
        corpus_dir = str(backend_root / "data" / "corpus")
        docs = load_markdown_docs(corpus_dir)
        chunks = split_docs(docs, chunk_size=500, chunk_overlap=50)
        _hybrid_retriever = HybridRetriever()
        _hybrid_retriever.index(chunks)
    return _hybrid_retriever


def _load_history(session_id: str | None) -> list:
    """加载对话历史（不写入新消息）。"""
    if session_id:
        store = get_history_store()
        return store.get_messages(session_id)
    return []


def _quick_intent_classify(question: str) -> str | None:
    """规则预分类：明显属于某一类时直接返回，避免依赖 LLM 的不稳定表现。

    不同 LLM（DeepSeek / Qwen / MiniMax）对同一问题的分类不一致，
    尤其"你好"这种招呼语 MiniMax 经常分错。加规则兜底。
    """
    q = (question or "").strip()
    if not q:
        return "chat"
    # 1) 招呼 / 寒暄
    greetings = {"你好", "你好呀", "您好", "hi", "hello", "hey", "嗨", "哈喽",
                 "早", "早上好", "下午好", "晚上好", "在吗", "在么"}
    q_lower = q.lower()
    if q_lower in greetings or q_lower.rstrip("!！?？.。,，") in greetings:
        return "chat"
    # 2) 短问句 + 出现数学/生活/脑筋急转弯关键词 → chat
    life_kw = ["苹果", "分给", "怎么分", "几个人", "几个人分", "几个苹果", "平均",
               "脑筋急转弯", "思考题", "智力题", "几岁", "多大", "生日", "爱好",
               "喜欢什么", "做什么", "天气", "心情", "感觉"]
    if any(kw in q for kw in life_kw):
        return "chat"
    # 3) 明显要代码 → code
    code_kw = ["写代码", "代码实现", "代码怎么写", "怎么实现", "实现一下",
               "def ", "class ", "function ", "写一个函数", "写一段代码",
               "python 实现", "伪代码", "demo"]
    if any(kw in q for kw in code_kw):
        return "code"
    return None  # 让 LLM 决定


def query_analyzer(state: dict) -> dict:
    # 规则预分类优先：避免不同 LLM 表现差异
    quick = _quick_intent_classify(state["question"])
    if quick:
        state["intent"] = quick
        return state

    llm = get_llm(state.get("provider"))
    history = _load_history(state.get("session_id"))
    history_text = _format_history(history)
    prompt = ChatPromptTemplate.from_template(INTENT_PROMPT)
    chain = prompt | llm | StrOutputParser()
    result = chain.invoke({"question": state["question"], "chat_history": history_text}).strip().lower()
    if result not in ("factual", "code", "chat"):
        result = "factual"
    state["intent"] = result
    return state


def query_rewriter(state: dict) -> dict:
    """Query 改写节点：把口语化问题改写成关键词友好的检索查询。"""
    if state.get("intent") == "chat":
        state["rewritten_query"] = state["question"]
        return state

    llm = get_llm(state.get("provider"))
    history = _load_history(state.get("session_id"))
    history_text = _format_history(history)
    prompt = ChatPromptTemplate.from_template(REWRITE_PROMPT)
    chain = prompt | llm | StrOutputParser()
    rewritten = chain.invoke({"question": state["question"], "chat_history": history_text}).strip()
    state["rewritten_query"] = rewritten if rewritten else state["question"]
    return state


def retriever(state: dict) -> dict:
    # 优先使用改写后的查询，回退到原始问题
    query = state.get("rewritten_query") or state["question"]
    k = state.get("k", 3)
    intent = state.get("intent", "factual")
    hr = _get_hybrid_retriever()

    if intent == "code":
        # code 意图：扩大候选池到 20，确保代码 chunk 能进 Reranker
        candidates = hr.search(query, top_k=20)
        code_docs = [d for d in candidates if d.metadata.get("is_code")]
        n_pass = max(k * 2, k)
        if len(code_docs) >= n_pass:
            # 优先 code chunk，多给 Reranker 一些候选
            docs = code_docs[:n_pass]
        else:
            # code 不足时，用相关非代码 chunk 补足
            other = [d for d in candidates if not d.metadata.get("is_code")]
            docs = (code_docs + other)[:n_pass]
    else:
        # 非 code 意图：直接取 top-k
        docs = hr.search(query, top_k=k)[:k]

    state["docs"] = docs
    return state


def reranker_node(state: dict) -> dict:
    docs = state.get("docs", [])
    if not docs:
        return state
    # 必须用改写后的 query 做 rerank：追问/指代（如"详细讲解一下代码"）
    # 在原始 question 中没有可对齐的语义信号，会把对的 doc 排掉
    query = state.get("rewritten_query") or state["question"]
    reranked = rerank(query, docs, top_k=len(docs))
    state["docs"] = reranked[: state.get("k", 3)]
    return state


def _load_and_append_question(session_id: str | None, question: str):
    history = []
    if session_id:
        store = get_history_store()
        history = store.get_messages(session_id)
        store.add_message(session_id, HumanMessage(content=question))
    return history


def _format_history(messages, max_turns: int = 5) -> str:
    if not messages:
        return ""
    recent = messages[-(max_turns * 2):]
    parts = []
    for m in recent:
        role = "用户" if m.type == "human" else "AI"
        parts.append(f"{role}: {m.content}")
    return "【对话历史】\n" + "\n".join(parts) + "\n"


_NO_INFO_PATTERNS = (
    "无相关", "无相关信息", "没有找到", "没有找到相关", "未提供", "未找到",
    "文档中没有", "抱歉", "不能回答", "无法回答", "无法基于", "不能基于",
    "未提及", "没有提到", "不涉及", "不相关", "无关", "仅有",
)


def _is_no_info_answer(answer: str) -> bool:
    """检测 LLM 是否给出了"无相关信息"式的回答。"""
    if not answer:
        return False
    head = answer[:300]
    return any(p in head for p in _NO_INFO_PATTERNS)


def _append_answer(session_id: str | None, answer: str) -> None:
    if session_id:
        store = get_history_store()
        store.add_message(session_id, AIMessage(content=answer))


def generator(state: dict) -> dict:
    session_id = state.get("session_id")
    question = state["question"]
    history = _load_and_append_question(session_id, question)
    history_text = _format_history(history)

    if state.get("intent") == "chat":
        llm = get_llm(state.get("provider"))
        prompt = ChatPromptTemplate.from_template(CHAT_PROMPT)
        chain = prompt | llm | StrOutputParser()
        answer = chain.invoke({"question": question, "chat_history": history_text})
        _append_answer(session_id, answer)
        state["answer"] = answer
        state["citations"] = []
        return state

    docs = state.get("docs", [])
    if not docs:
        # 没召回任何文档：fallback 到 chat + history，而不是直接说"无相关信息"
        # —— 用户的追问（如"六个苹果呢"接"三个苹果怎么分"）经常是闲聊，
        # 即便被误判成 factual/code，也应该用历史回答。
        llm = get_llm(state.get("provider"))
        prompt = ChatPromptTemplate.from_template(CHAT_PROMPT)
        chain = prompt | llm | StrOutputParser()
        answer = chain.invoke({"question": question, "chat_history": history_text})
        _append_answer(session_id, answer)
        state["answer"] = answer
        state["citations"] = []
        return state

    context = format_docs_with_citations(docs)
    prompt = ChatPromptTemplate.from_template(GENERATOR_PROMPT)
    llm = get_llm(state.get("provider"))
    chain = prompt | llm | StrOutputParser()
    answer = chain.invoke({"context": context, "question": question, "chat_history": history_text})
    _append_answer(session_id, answer)
    state["answer"] = answer
    # LLM 明确说"无相关"时过滤掉 citations，避免认知冲突
    state["citations"] = extract_citations(docs) if not _is_no_info_answer(answer) else []
    return state

def route_after_analyzer(state: dict) -> str:
    if state.get("intent") == "chat":
        return "generator"
    return "retriever"


REFLECTION_PROMPT = """你是一个答案质量评审员。评估以下回答的质量。

【问题】
{question}

【回答】
{answer}

【参考文档】
{context}

请判断回答是否存在以下问题：
1. 编造了文档中没有的信息
2. 回答不完整，缺少关键要点
3. 回答与问题不相关

只返回一个词：pass（通过）或 fail（不通过）
"""


def reflection(state: dict) -> dict:
    """Reflection 节点：LLM 自我评估答案质量，不通过则重跑检索。"""
    if state.get("intent") == "chat":
        return state

    docs = state.get("docs", [])
    answer = state.get("answer", "")
    question = state["question"]

    if not answer or answer == "文档中没有找到相关信息":
        return state

    # 用 LLM 评估答案质量
    context = format_docs_with_citations(docs) if docs else "无"
    llm = get_llm(state.get("provider"))
    prompt = ChatPromptTemplate.from_template(REFLECTION_PROMPT)
    chain = prompt | llm | StrOutputParser()
    result = chain.invoke({
        "question": question,
        "answer": answer,
        "context": context,
    }).strip().lower()

    count = state.get("reflection_count", 0) + 1
    state["reflection_count"] = count

    # 最多 reflection 1 次，避免死循环
    if result == "fail" and count <= 1:
        # 重新检索，增加 top_k
        state["k"] = state.get("k", 3) + 2
        state["docs"] = []
        state["answer"] = ""

    return state


def route_after_reflection(state: dict) -> str:
    """Reflection 后的路由：不通过且未超限则重跑检索，否则结束。"""
    count = state.get("reflection_count", 0)
    answer = state.get("answer", "")

    # 如果 answer 被清空，说明需要重跑检索
    if not answer and count <= 1:
        return "retriever"
    return "end"