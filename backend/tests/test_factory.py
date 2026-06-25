"""测试 LLM 工厂：3 个 provider 都能正确返回带降级链的 FallbackChatModel。"""
import pytest

from app.llm.factory import FallbackChatModel, OpenAICompatModel, _create_llm, get_llm
from langchain_deepseek import ChatDeepSeek


def test_get_llm_deepseek_wraps_chat_deepseek():
    """DeepSeek 应被包装在 FallbackChatModel 内，且 primary 是 ChatDeepSeek。"""
    llm = get_llm("deepseek")
    assert isinstance(llm, FallbackChatModel)
    assert isinstance(llm._models[0], ChatDeepSeek)


def test_get_llm_qwen_wraps_openai_compat():
    """Qwen 应被包装在 FallbackChatModel 内，且 primary 是 OpenAICompatModel。"""
    llm = get_llm("qwen")
    assert isinstance(llm, FallbackChatModel)
    assert isinstance(llm._models[0], OpenAICompatModel)


def test_get_llm_invalid_provider_raises():
    """非法 provider 应抛 ValueError。"""
    with pytest.raises(ValueError, match="Unknown LLM provider"):
        _create_llm("claude")


def test_fallback_chain_has_at_least_one_model():
    """无论哪个 provider，FallbackChatModel 至少包含主 provider。"""
    for p in ("deepseek", "qwen", "minimax"):
        llm = get_llm(p)
        assert isinstance(llm, FallbackChatModel)
        assert len(llm._models) >= 1


def test_fallback_chain_contains_distinct_providers():
    """降级链上的 provider 应与主 provider 不同。"""
    llm = get_llm("deepseek")
    # primary 是 deepseek
    assert isinstance(llm._models[0], ChatDeepSeek)
    # 降级链：qwen / minimax 至少有一个能成功创建
    for fallback in llm._models[1:]:
        assert not isinstance(fallback, ChatDeepSeek), "降级链不应包含 deepseek"