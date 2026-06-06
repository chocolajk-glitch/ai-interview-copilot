"""测试 LLM 工厂：3 个 provider 都能正确返回对应 client。"""
import pytest

from app.llm.factory import OpenAICompatModel, get_llm
from langchain_deepseek import ChatDeepSeek


def test_get_llm_deepseek_returns_chat_deepseek():
    """DeepSeek 走 ChatDeepSeek（LangChain 官方类）。"""
    llm = get_llm("deepseek")
    assert isinstance(llm, ChatDeepSeek)


def test_get_llm_qwen_returns_openai_compat():
    """Qwen 走 OpenAICompatModel（自写 wrapper）。"""
    llm = get_llm("qwen")
    assert isinstance(llm, OpenAICompatModel)


def test_get_llm_invalid_provider_raises():
    """非法 provider 应抛 ValueError。"""
    with pytest.raises(ValueError, match="Unknown LLM provider"):
        get_llm("claude")