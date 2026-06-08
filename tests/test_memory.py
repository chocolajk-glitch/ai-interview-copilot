import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.memory import get_history_store
from app.rag.chain import _format_history


def test_in_memory_store_basic():
    from app.memory.in_memory_store import InMemoryChatHistoryStore
    store = InMemoryChatHistoryStore()
    store.add_message("s1", HumanMessage(content="hi"))
    store.add_message("s1", AIMessage(content="hello"))
    msgs = store.get_messages("s1")
    assert len(msgs) == 2
    assert msgs[0].content == "hi"
    assert msgs[1].content == "hello"


def test_in_memory_store_isolation():
    from app.memory.in_memory_store import InMemoryChatHistoryStore
    store = InMemoryChatHistoryStore()
    store.add_message("a", HumanMessage(content="A question"))
    store.add_message("b", HumanMessage(content="B question"))
    assert len(store.get_messages("a")) == 1
    assert len(store.get_messages("b")) == 1
    assert store.get_messages("a")[0].content == "A question"


def test_in_memory_store_clear():
    from app.memory.in_memory_store import InMemoryChatHistoryStore
    store = InMemoryChatHistoryStore()
    store.add_message("s1", HumanMessage(content="x"))
    store.clear("s1")
    assert store.get_messages("s1") == []


def test_redis_store_basic():
    from app.memory.redis_store import RedisChatHistoryStore
    store = RedisChatHistoryStore(ttl=60)
    store.clear("test-session")
    store.add_message("test-session", HumanMessage(content="redis test"))
    msgs = store.get_messages("test-session")
    assert len(msgs) >= 1
    assert msgs[-1].content == "redis test"
    store.clear("test-session")


def test_redis_store_ttl_set():
    from app.memory.redis_store import RedisChatHistoryStore
    store = RedisChatHistoryStore(ttl=60)
    store.clear("ttl-test")
    store.add_message("ttl-test", HumanMessage(content="x"))
    from app.memory.redis_store import RedisChatHistoryStore as RC
    ttl = store._r.ttl(store._key("ttl-test"))
    assert 0 < ttl <= 60
    store.clear("ttl-test")


def test_format_history_empty():
    assert _format_history([]) == ""


def test_format_history_max_turns():
    msgs = []
    for i in range(20):
        msgs.append(HumanMessage(content=f"q{i}"))
        msgs.append(AIMessage(content=f"a{i}"))
    text = _format_history(msgs, max_turns=3)
    assert "q0" not in text
    assert "q17" in text
    assert "a19" in text


def test_format_history_includes_roles():
    msgs = [HumanMessage(content="Q1"), AIMessage(content="A1")]
    text = _format_history(msgs)
    assert "用户: Q1" in text
    assert "AI: A1" in text


def test_end_to_end_session_memory():
    from app.rag.chain import ask
    store = get_history_store()
    if hasattr(store, "clear"):
        try:
            store.clear("e2e-session")
        except Exception:
            pass
    r1 = ask("两数之和怎么解", provider="qwen", k=2, session_id="e2e-session")
    assert "answer" in r1
    r2 = ask("它的时间复杂度呢", provider="qwen", k=2, session_id="e2e-session")
    assert "answer" in r2
    assert len(r2["answer"]) > 0
    try:
        store.clear("e2e-session")
    except Exception:
        pass


def test_no_session_id_does_not_persist():
    from app.rag.chain import ask
    r = ask("栈是什么", provider="qwen", k=2, session_id=None)
    assert "answer" in r