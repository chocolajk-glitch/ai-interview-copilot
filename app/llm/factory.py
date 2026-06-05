"""LLM 工厂：按 LLM_PROVIDER 环境变量返回对应 LLM client。"""
from typing import Literal, Union

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_deepseek import ChatDeepSeek
from openai import OpenAI
from langchain_community.chat_models import ChatTongyi

from app.core.config import settings

LLMProvider = Literal["deepseek", "qwen", "minimax"]


class OpenAICompatModel:
    """OpenAI 兼容协议轻量 wrapper（Qwen / MiniMax 用）。"""

    def __init__(self, api_key: str, base_url: str, model: str, temperature: float = 0.7):
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model
        self._temperature = temperature

    @property
    def model(self) -> str:
        return self._model

    def invoke(self, messages: list) -> AIMessage:
        oa_msgs = [{"role": "user", "content": m.content} for m in messages]
        r = self._client.chat.completions.create(
            model=self._model, messages=oa_msgs, temperature=self._temperature
        )
        return AIMessage(content=r.choices[0].message.content or "")


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


def chat(message: str, provider: LLMProvider | None = None) -> str:
    llm = get_llm(provider)
    response = llm.invoke([HumanMessage(content=message)])
    return response.content