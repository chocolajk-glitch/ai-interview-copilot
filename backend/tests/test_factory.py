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


# ---------------------------------------------------------------------------
# 异常分类：瞬态错误降级 / 非瞬态错误直接抛
# ---------------------------------------------------------------------------

from unittest.mock import MagicMock

from openai import APIConnectionError, APITimeoutError, RateLimitError


class _StubOK:
    """模拟一个 invoke 成功的 provider。"""
    def invoke(self, input, config=None, **kwargs):
        from langchain_core.messages import AIMessage
        return AIMessage(content="ok")


class _StubFail:
    """模拟一个 invoke 抛指定异常的 provider。"""
    def __init__(self, exc: BaseException):
        self._exc = exc
    def invoke(self, input, config=None, **kwargs):
        raise self._exc


def _make_chain(*providers) -> FallbackChatModel:
    """用给定的 stub 列表构造一个 FallbackChatModel（绕过 _create_llm）。"""
    chain = FallbackChatModel.__new__(FallbackChatModel)
    chain._models = list(providers)
    return chain


def test_transient_api_connection_error_triggers_fallback():
    """APIConnectionError 应触发降级——切到下一个 provider。"""
    from langchain_core.messages import AIMessage

    primary = _StubFail(APIConnectionError(request=MagicMock(), message="connection refused"))
    fallback = _StubOK()
    chain = _make_chain(primary, fallback)

    result = chain.invoke("hello")
    assert result.content == "ok", "降级到 fallback 后应返回成功结果"


def test_transient_rate_limit_error_triggers_fallback():
    """RateLimitError 应触发降级。"""
    import httpx

    # 新版 OpenAI SDK: RateLimitError.__init__ 签名是 (message, *, response, body)
    fake_response = httpx.Response(
        status_code=429,
        request=httpx.Request("POST", "https://example.com"),
    )
    primary = _StubFail(RateLimitError("rate limit", response=fake_response, body=None))
    fallback = _StubOK()
    chain = _make_chain(primary, fallback)

    result = chain.invoke("hello")
    assert result.content == "ok"


def test_transient_timeout_error_triggers_fallback():
    """APITimeoutError 应触发降级。"""
    primary = _StubFail(APITimeoutError(request=MagicMock()))
    fallback = _StubOK()
    chain = _make_chain(primary, fallback)

    result = chain.invoke("hello")
    assert result.content == "ok"


def test_non_transient_error_does_not_trigger_fallback():
    """非瞬态错误（ValueError / KeyError 等代码 bug）不应降级，应直接抛出。"""
    primary = _StubFail(ValueError("代码 bug：参数顺序错了"))
    fallback = _StubOK()
    chain = _make_chain(primary, fallback)

    with pytest.raises(ValueError, match="代码 bug"):
        chain.invoke("hello")
    # fallback 不应被调用——bug 必须暴露出来


def test_all_providers_fail_raises_runtime_error():
    """所有 provider 都瞬态失败 → 抛 RuntimeError（带最后错误信息）。"""
    primary = _StubFail(APIConnectionError(request=MagicMock(), message="net down"))
    fallback = _StubFail(APITimeoutError(request=MagicMock()))
    chain = _make_chain(primary, fallback)

    with pytest.raises(RuntimeError, match="所有 LLM provider 均不可用"):
        chain.invoke("hello")