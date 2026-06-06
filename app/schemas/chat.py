"""聊天相关 Pydantic schema（请求/响应数据校验）。"""
from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """聊天请求体。"""
    message: str = Field(..., min_length=1, max_length=4000, description="用户问题")
    provider: Literal["deepseek", "qwen", "minimax"] | None = Field(
        default=None,
        description="LLM provider（不传则用 settings.LLM_PROVIDER 默认）"
    )
    temperature: float = Field(
        default=0.7, ge=0.0, le=2.0,
        description="生成温度（0=确定性, 2=最大随机）"
    )


class ChatResponse(BaseModel):
    """聊天响应。"""
    reply: str = Field(..., description="AI 回复内容")
    provider: str = Field(..., description="实际使用的 provider")
    model: str = Field(..., description="实际使用的模型名")

class AskRequest(BaseModel):
    """RAG 问答请求。"""
    question: str = Field(..., min_length=1, max_length=4000, description="用户问题")
    provider: Literal["deepseek", "qwen", "minimax"] | None = Field(
        default=None,
        description="LLM provider（不传用默认）"
    )
    top_k: int = Field(default=3, ge=1, le=10, description="检索 top-k")


class AskResponse(BaseModel):
    """RAG 问答响应。"""
    answer: str = Field(..., description="AI 答案")
    sources: list[str] = Field(default_factory=list, description="引用来源文件名列表")
    provider: str = Field(..., description="实际使用的 provider")