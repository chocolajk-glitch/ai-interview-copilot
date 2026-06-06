"""测试 RAG Chain：混合检索 + LLM 端到端。"""
from app.rag.chain import ask


def test_ask_returns_answer_and_sources():
    """ask() 返回非空 answer + 非空 sources。"""
    result = ask("两数之和怎么解", provider="deepseek")
    assert "answer" in result
    assert "sources" in result
    assert len(result["answer"]) > 10
    assert "01_two_sum" in str(result["sources"])


def test_ask_with_minimax_provider_works():
    """用 MiniMax provider 也能跑（验证 OpenAICompatModel + as_runnable 在 chain 里 work）。"""
    result = ask("反转链表", provider="minimax")
    assert "02_reverse_linked_list" in str(result["sources"])


def test_ask_hybrid_top3_returns_3_sources():
    """top_k=3 应返回 3 个 sources。"""
    result = ask("栈", provider="deepseek", k=3)
    assert len(result["sources"]) == 3