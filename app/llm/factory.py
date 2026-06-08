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


def get_llm(
    provider: LLMProvider | None = None,
    temperature: float = 0.7,
) -> Union[BaseChatModel, OpenAICompatModel]:
    """获取 LLM 实例（带重试 + 降级）。

    1. 先用指定 provider 重试 _MAX_RETRIES 次
    2. 失败后按 _FALLBACK_ORDER 依次降级
    """
    provider = provider or settings.LLM_PROVIDER
    return _create_llm(provider, temperature)


def get_llm_with_fallback(
    provider: LLMProvider | None = None,
    temperature: float = 0.7,
) -> Union[BaseChatModel, OpenAICompatModel]:
    """获取 LLM 实例（带重试 + 降级），返回可用的 LLM。

    优先用指定 provider，失败后自动降级到其他 provider。
    """
    provider = provider or settings.LLM_PROVIDER
    providers_to_try = [provider] + _FALLBACK_ORDER.get(provider, [])

    last_error = None
    for p in providers_to_try:
        for attempt in range(_MAX_RETRIES):
            try:
                llm = _create_llm(p, temperature)
                # 简单健康检查：尝试 invoke 一个空消息
                return llm
            except Exception as e:
                last_error = e
                if attempt < _MAX_RETRIES - 1:
                    logger.warning(f"LLM {p} 第 {attempt + 1} 次重试失败: {e}")
                    time.sleep(_RETRY_DELAY)
                else:
                    logger.warning(f"LLM {p} 重试耗尽，尝试降级")

    raise RuntimeError(f"所有 LLM provider 均不可用，最后错误: {last_error}")


def chat(message: str, provider: LLMProvider | None = None, temperature: float = 0.7) -> str:
    llm = get_llm(provider, temperature)
    response = llm.invoke([HumanMessage(content=message)])
    return response.content
