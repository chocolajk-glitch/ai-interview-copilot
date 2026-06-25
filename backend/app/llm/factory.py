"""LLM 工厂：按 LLM_PROVIDER 环境变量返回对应 LLM client，支持重试与降级。"""
import time
from typing import AsyncIterator, Iterator, Literal, Union

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage
from langchain_core.runnables import Runnable
from langchain_deepseek import ChatDeepSeek
from openai import AsyncOpenAI, OpenAI
from app.core.config import settings
from app.core.logging import logger

LLMProvider = Literal["deepseek", "qwen", "minimax"]

# 降级顺序：当前 provider 失败后依次尝试
_FALLBACK_ORDER: dict[str, list[str]] = {
    "deepseek": ["qwen", "minimax"],
    "qwen": ["deepseek", "minimax"],
    "minimax": ["deepseek", "qwen"],
}

_MAX_RETRIES = 2
_RETRY_DELAY = 1.0  # 秒


def _extract_messages(input) -> list:
    """从多种输入格式中提取 messages：ChatPromptValue / dict / str / list。"""
    if hasattr(input, "messages"):
        return input.messages
    if isinstance(input, dict) and "messages" in input:
        return input["messages"]
    if isinstance(input, str):
        return [HumanMessage(content=input)]
    return input


def _to_oa_messages(messages: list) -> list[dict]:
    """把 LangChain messages 转 OpenAI 协议（type + content）。"""
    return [
        {"role": "user" if isinstance(m, HumanMessage) else m.type, "content": m.content}
        for m in messages
    ]


class OpenAICompatModel(Runnable):
    """OpenAI 兼容协议轻量 wrapper（Qwen / MiniMax 用）。

    继承 Runnable：直接接入 LCEL（prompt | model | parser），
    支持 invoke / ainvoke（一次性）+ stream / astream（流式）。
    """

    def __init__(self, api_key: str, base_url: str, model: str, temperature: float = 0.7):
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._async_client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._model = model
        self._temperature = temperature

    @property
    def model(self) -> str:
        return self._model

    def invoke(self, input, config=None, **kwargs) -> AIMessage:
        messages = _extract_messages(input)
        r = self._client.chat.completions.create(
            model=self._model, messages=_to_oa_messages(messages),
            temperature=self._temperature
        )
        return AIMessage(content=r.choices[0].message.content or "")

    async def ainvoke(self, input, config=None, **kwargs) -> AIMessage:
        messages = _extract_messages(input)
        r = await self._async_client.chat.completions.create(
            model=self._model, messages=_to_oa_messages(messages),
            temperature=self._temperature
        )
        return AIMessage(content=r.choices[0].message.content or "")

    def stream(self, input, config=None, **kwargs) -> Iterator[AIMessageChunk]:
        messages = _extract_messages(input)
        response = self._client.chat.completions.create(
            model=self._model, messages=_to_oa_messages(messages),
            temperature=self._temperature, stream=True
        )
        for chunk in response:
            if chunk.choices[0].delta.content:
                yield AIMessageChunk(content=chunk.choices[0].delta.content)

    async def astream(self, input, config=None, **kwargs) -> AsyncIterator[AIMessageChunk]:
        messages = _extract_messages(input)
        response = await self._async_client.chat.completions.create(
            model=self._model, messages=_to_oa_messages(messages),
            temperature=self._temperature, stream=True
        )
        async for chunk in response:
            if chunk.choices[0].delta.content:
                yield AIMessageChunk(content=chunk.choices[0].delta.content)


def _create_llm(provider: str, temperature: float = 0.7) -> Union[BaseChatModel, OpenAICompatModel]:
    """创建指定 provider 的 LLM 实例（无重试）。"""
    if provider == "deepseek":
        return ChatDeepSeek(
            model=settings.DEEPSEEK_MODEL,
            api_key=settings.DEEPSEEK_API_KEY,
            temperature=temperature,
        )
    if provider == "qwen":
        return OpenAICompatModel(
            api_key=settings.QWEN_API_KEY,
            base_url=settings.QWEN_BASE_URL,
            model=settings.QWEN_MODEL,
            temperature=temperature,
        )
    if provider == "minimax":
        return OpenAICompatModel(
            api_key=settings.MINIMAX_API_KEY,
            base_url=settings.MINIMAX_BASE_URL,
            model=settings.MINIMAX_MODEL,
            temperature=temperature,
        )
    raise ValueError(f"Unknown LLM provider: {provider}")


class FallbackChatModel(Runnable):
    """带「invoke 失败降级」的 LLM 包装器。

    - 内部按 _FALLBACK_ORDER 维护一个 LLM 列表
    - 首次 invoke/ainvoke/stream/astream 失败时（任意 provider），降级到下一个
    - 同一 provider 内部不重试（避免延迟翻倍），降级是兜底

    这样既不增加常规请求的延迟，又能在主 provider 异常时自动切换。
    """

    def __init__(self, primary: Union[BaseChatModel, OpenAICompatModel], fallbacks: list[Union[BaseChatModel, OpenAICompatModel]]):
        self._models: list[Union[BaseChatModel, OpenAICompatModel]] = [primary] + fallbacks
        self._provider_index: list[str] = []  # 仅用于日志

    @property
    def model(self) -> str:
        return getattr(self._models[0], "model", "?")

    def _try_invoke(self, idx: int, input, config=None, **kwargs) -> AIMessage:
        return self._models[idx].invoke(input, config, **kwargs)

    async def _try_ainvoke(self, idx: int, input, config=None, **kwargs) -> AIMessage:
        return await self._models[idx].ainvoke(input, config, **kwargs)

    def invoke(self, input, config=None, **kwargs) -> AIMessage:
        last_error: Exception | None = None
        for idx, model in enumerate(self._models):
            try:
                return self._try_invoke(idx, input, config, **kwargs)
            except Exception as e:
                last_error = e
                logger.warning(
                    f"LLM[{idx}] invoke 失败，尝试降级: {type(e).__name__}: {str(e)[:200]}"
                )
        raise RuntimeError(f"所有 LLM provider 均不可用，最后错误: {last_error}")

    async def ainvoke(self, input, config=None, **kwargs) -> AIMessage:
        last_error: Exception | None = None
        for idx, model in enumerate(self._models):
            try:
                return await self._try_ainvoke(idx, input, config, **kwargs)
            except Exception as e:
                last_error = e
                logger.warning(
                    f"LLM[{idx}] ainvoke 失败，尝试降级: {type(e).__name__}: {str(e)[:200]}"
                )
        raise RuntimeError(f"所有 LLM provider 均不可用，最后错误: {last_error}")

    def stream(self, input, config=None, **kwargs) -> Iterator[AIMessageChunk]:
        last_error: Exception | None = None
        for idx, model in enumerate(self._models):
            try:
                yield from model.stream(input, config, **kwargs)
                return
            except Exception as e:
                last_error = e
                logger.warning(
                    f"LLM[{idx}] stream 失败，尝试降级: {type(e).__name__}: {str(e)[:200]}"
                )
        raise RuntimeError(f"所有 LLM provider 均不可用，最后错误: {last_error}")

    async def astream(self, input, config=None, **kwargs) -> AsyncIterator[AIMessageChunk]:
        last_error: Exception | None = None
        for idx, model in enumerate(self._models):
            try:
                async for chunk in model.astream(input, config, **kwargs):
                    yield chunk
                return
            except Exception as e:
                last_error = e
                logger.warning(
                    f"LLM[{idx}] astream 失败，尝试降级: {type(e).__name__}: {str(e)[:200]}"
                )
        raise RuntimeError(f"所有 LLM provider 均不可用，最后错误: {last_error}")


def get_llm(
    provider: LLMProvider | None = None,
    temperature: float = 0.7,
) -> FallbackChatModel:
    """获取 LLM 实例（带 invoke 失败降级）。

    策略：构造时同时创建主 provider + 降级链上的所有 provider，
    包装在 FallbackChatModel 里；运行时只在 invoke 失败时降级，
    不在 provider 内部重试，避免延迟翻倍。
    """
    provider = provider or settings.LLM_PROVIDER
    fallbacks: list[Union[BaseChatModel, OpenAICompatModel]] = []
    for p in _FALLBACK_ORDER.get(provider, []):
        try:
            fallbacks.append(_create_llm(p, temperature))
        except Exception as e:
            logger.warning(f"降级 provider {p} 创建失败，跳过: {e}")
    primary = _create_llm(provider, temperature)
    return FallbackChatModel(primary, fallbacks)


def chat(message: str, provider: LLMProvider | None = None, temperature: float = 0.7) -> str:
    llm = get_llm(provider, temperature)
    response = llm.invoke([HumanMessage(content=message)])
    return response.content
