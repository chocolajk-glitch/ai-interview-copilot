from unittest.mock import patch

from app.graph.nodes import query_analyzer, route_after_analyzer
from app.graph.workflow import build_workflow, get_workflow


def test_workflow_compiles():
    app = build_workflow()
    assert app is not None


def test_route_after_analyzer_chat_skips_retriever():
    assert route_after_analyzer({"intent": "chat"}) == "generator"


def test_route_after_analyzer_factual_uses_retriever():
    assert route_after_analyzer({"intent": "factual"}) == "retriever"


def test_route_after_analyzer_code_uses_retriever():
    assert route_after_analyzer({"intent": "code"}) == "retriever"


def test_query_analyzer_classifies_chat():
    state = {"question": "你好呀", "provider": "qwen"}
    result = query_analyzer(dict(state))
    assert result["intent"] == "chat"


def test_query_analyzer_classifies_factual():
    state = {"question": "哈希表的原理", "provider": "qwen"}
    result = query_analyzer(dict(state))
    assert result["intent"] == "factual"


def test_end_to_end_factual():
    app = get_workflow()
    result = app.invoke({
        "question": "哈希表怎么实现",
        "provider": "qwen",
        "k": 3,
        "docs": [],
        "citations": [],
        "answer": "",
        "intent": "factual",
    })
    assert "answer" in result
    assert "citations" in result
    assert result["intent"] in ("factual", "code")
    assert len(result["citations"]) >= 1


def test_end_to_end_chat_skips_retriever():
    app = get_workflow()
    result = app.invoke({
        "question": "你好",
        "provider": "qwen",
        "k": 3,
        "docs": [],
        "citations": [],
        "answer": "",
        "intent": "factual",
    })
    assert result["intent"] == "chat"
    assert "answer" in result
    assert result["citations"] == []


def test_end_to_end_code():
    app = get_workflow()
    result = app.invoke({
        "question": "两数之和代码怎么写",
        "provider": "qwen",
        "k": 3,
        "docs": [],
        "citations": [],
        "answer": "",
        "intent": "factual",
    })
    assert "answer" in result
    assert "citations" in result
    if result["citations"]:
        assert any(c.get("is_code") for c in result["citations"]) or len(result["citations"]) >= 1


def test_end_to_end_code_followup_returns_code_chunks():
    """复现用户报告的 bug：追问"详细讲解一下代码"必须返回代码 chunk。

    修复前：retriever 拿不到代码 chunk（BM25 排名靠后 + code 过滤回退到非代码）。
    修复后：retriever 扩大候选池，code chunk 进 Reranker，最终返回至少 1 个代码引用。
    """
    from app.memory.in_memory_store import InMemoryChatHistoryStore
    from langchain_core.messages import HumanMessage, AIMessage

    # 模拟 turn 1 历史：问"合并K个升序链表"得到 AI 回答
    store = InMemoryChatHistoryStore()
    sid = "test-code-followup"
    store.add_message(sid, HumanMessage(content="合并K个升序链表怎么做"))
    store.add_message(sid, AIMessage(content="可以用分治或优先队列，参考收集排序法..."))

    app = get_workflow()
    with patch("app.graph.nodes.get_history_store", return_value=store):
        result = app.invoke({
            "question": "详细讲解一下代码",
            "session_id": sid,
            "provider": "qwen",
            "k": 3,
            "docs": [],
            "citations": [],
            "answer": "",
            "intent": "factual",
            "rewritten_query": "",
        })
    assert "answer" in result
    assert "citations" in result
    # 关键：必须至少有 1 个代码引用
    n_code = sum(1 for c in result["citations"] if c.get("is_code"))
    assert n_code >= 1, (
        f"追问'详细讲解一下代码'必须返回代码引用，实际 0 个：{result['citations']}"
    )


def test_generator_falls_back_to_chat_when_no_docs():
    """修复 D：RAG 路径下 docs 为空时，generator 应 fallback 到 chat + history
    而不是直接返回"文档中没有找到相关信息"。

    这保护了追问被误判成 factual/code 的情况（如"六个苹果呢"接"三个苹果怎么分"）。
    """
    from unittest.mock import patch as _patch
    from app.memory.in_memory_store import InMemoryChatHistoryStore
    from app.graph.nodes import generator as generator_node
    from langchain_core.messages import HumanMessage, AIMessage

    store = InMemoryChatHistoryStore()
    sid = "test-no-docs-fallback"
    store.add_message(sid, HumanMessage(content="三个苹果三个人怎么分"))
    store.add_message(sid, AIMessage(content="每人分一个苹果。"))

    state = {
        "question": "六个苹果呢",
        "intent": "factual",       # 模拟被误判成 factual
        "docs": [],                # 模拟 RAG 没召回任何 doc
        "citations": [],
        "answer": "",
        "session_id": sid,
    }
    with _patch("app.graph.nodes.get_history_store", return_value=store):
        out = generator_node(dict(state))

    # 不应再返回"文档中没有找到相关信息"
    assert "文档中没有找到相关信息" not in out["answer"], (
        f"没 docs 时应 fallback 到 chat，但返回了：{out['answer']!r}"
    )
    # 历史里应当追加了本轮 Human + AI
    msgs = store.get_messages(sid)
    assert len(msgs) == 4, f"历史应有 4 条（turn1×2 + turn2×2），实际 {len(msgs)}"
    assert msgs[2].content == "六个苹果呢"
    assert msgs[3].content == out["answer"]


def test_intent_prompt_mentions_non_tech_followup():
    """修复 E：INTENT_PROMPT 应明确说明"追问非技术话题保持上一轮分类"。

    防止 LLM 把"六个苹果呢"误判成 factual（因为有"呢"问号词）。
    """
    from app.graph.nodes import INTENT_PROMPT
    # 必须包含对"非技术话题追问"保持分类的指引
    assert "非技术" in INTENT_PROMPT or "闲聊" in INTENT_PROMPT or "生活" in INTENT_PROMPT, (
        "INTENT_PROMPT 缺少对非技术追问的指引"
    )


def test_quick_intent_classify_greetings():
    """修复 F：_quick_intent_classify 应能直接判定招呼语，避免 LLM 模型差异。"""
    from app.graph.nodes import _quick_intent_classify
    assert _quick_intent_classify("你好") == "chat"
    assert _quick_intent_classify("你好呀") == "chat"
    assert _quick_intent_classify("hi") == "chat"
    assert _quick_intent_classify("hello") == "chat"
    assert _quick_intent_classify("在吗") == "chat"
    # 数学/生活类
    assert _quick_intent_classify("六个苹果怎么分给3个人") == "chat"
    assert _quick_intent_classify("脑筋急转弯") == "chat"
    # 明显要代码
    assert _quick_intent_classify("写一个函数实现") == "code"
    # 不确定的情况
    assert _quick_intent_classify("两数之和") is None
    assert _quick_intent_classify("") == "chat"


def test_is_no_info_answer_detection():
    """修复 G/H：检测 LLM 回答是否属于"无相关信息"模式。

    用于过滤 citations，避免 LLM 说"无相关"还挂着引用源。
    """
    from app.graph.nodes import _is_no_info_answer
    from app.api.chat import _is_no_info_answer as api_check
    from app.rag.chain import _is_no_info_answer as chain_check

    # 命中
    assert _is_no_info_answer("抱歉，文档中没有相关...")
    assert _is_no_info_answer("根据文档内容，没有找到...")
    assert _is_no_info_answer("无相关信息")
    assert _is_no_info_answer("我无法回答这个问题")

    # 不命中
    assert not _is_no_info_answer("根据文档内容，两数之和可以用哈希表...")
    assert not _is_no_info_answer("每人分2个苹果")
    assert not _is_no_info_answer("")

    # 三个位置都应该有这个函数（api/chat、graph/nodes、rag/chain）
    assert api_check("无相关") is True
    assert chain_check("抱歉") is True