"""LLM 工厂：按 LLM_PROVIDER 环境变量返回对应 LLM client。"""
from typing import AsyncIterator, Iterator, Literal, Union

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage
from langchain_core.runnables import Runnable
from langchain_deepseek import ChatDeepSeek
from openai import AsyncOpenAI, OpenAI
from app.core.config import settings

LLMProvider = Literal["deepseek", "qwen", "minimax"]


def _extract_messages(input) -> list:
    """从多种输入格式中提取 messages：ChatPromptValue / dict / str / list。"""
    if hasattr(input, "messages"):
        return input.messages
    if isinstance(input, dict) and "messages" in input:
        return input["messages"]
    if isinstance(input, str):
        return [HumanMessage(content=input)]  # ← 新增这 3 行
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


def get_llm(
    provider: LLMProvider | None = None,
    temperature: float = 0.7,
) -> Union[BaseChatModel, OpenAICompatModel]:
    provider = provider or settings.LLM_PROVIDER
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


def chat(message: str, provider: LLMProvider | None = None, temperature: float = 0.7) -> str:
    llm = get_llm(provider, temperature)
    response = llm.invoke([HumanMessage(content=message)])
    return response.content