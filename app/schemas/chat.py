"""聊天相关 Pydantic schema（请求/响应数据校验）。"""
from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
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
    reply: str = Field(..., description="AI 回复内容")
    provider: str = Field(..., description="实际使用的 provider")
    model: str = Field(..., description="实际使用的模型名")


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000, description="用户问题")
    provider: Literal["deepseek", "qwen", "minimax"] | None = Field(
        default=None,
        description="LLM provider（不传用默认）"
    )
    top_k: int = Field(default=3, ge=1, le=10, description="检索 top-k")
    session_id: str | None = Field(default=None, max_length=128, description="会话 ID（None=不持久化）")


class Citation(BaseModel):
    index: int = Field(..., description="引用编号（对应答案里的 [1] [2]）")
    chunk_id: str = Field(..., description="chunk 唯一 ID（SHA256 前 16 位）")
    source: str = Field(..., description="文件名")
    heading: str | None = Field(default=None, description="所在标题")
    position: int = Field(..., description="原文起始字符 offset")
    end: int = Field(..., description="原文结束字符 offset")
    is_code: bool = Field(default=False, description="是否代码块")


class AskResponse(BaseModel):
    answer: str = Field(..., description="AI 答案")
    citations: list[Citation] = Field(default_factory=list, description="chunk 级引用列表")
    provider: str = Field(..., description="实际使用的 provider")


class StreamAskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000, description="用户问题")
    provider: Literal["deepseek", "qwen", "minimax"] | None = Field(
        default=None,
        description="LLM provider（不传用默认）"
    )
    top_k: int = Field(default=3, ge=1, le=10, description="检索 top-k")
    session_id: str | None = Field(default=None, max_length=128, description="会话 ID（None=不持久化）")

class AgentAskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000, description="用户问题")
    provider: Literal["deepseek", "qwen", "minimax"] | None = Field(
        default=None, description="LLM provider"
    )
    top_k: int = Field(default=3, ge=1, le=10, description="检索 top-k")
    session_id: str | None = Field(default=None, max_length=128, description="会话 ID（None=不持久化）")


class AgentAskResponse(BaseModel):
    answer: str = Field(..., description="AI 答案")
    intent: str = Field(..., description="query_analyzer 判定的意图（factual/code/chat）")
    citations: list[Citation] = Field(default_factory=list, description="chunk 级引用")
    provider: str = Field(..., description="实际使用的 provider")


class FeedbackRequest(BaseModel):
    session_id: str = Field(..., max_length=128, description="会话 ID")
    question: str = Field(..., min_length=1, description="用户问题")
    answer: str = Field(..., min_length=1, description="AI 回答")
    rating: Literal["thumbs_up", "thumbs_down"] = Field(..., description="反馈类型")
    comment: str | None = Field(default=None, description="可选文字反馈")


class FeedbackResponse(BaseModel):
    message: str = Field(..., description="反馈结果")