"""应用配置：从 .env 文件加载所有配置。"""
import os

# 模型离线加载：BGE embedding / reranker 已下载到本地缓存，避免 sentence-transformers
# 反复 HEAD 远端 huggingface.co 检查不存在的 adapter_config.json / processor_config.json
# （每次重试 1+2+4+8+8=23s，会让 turn 2/3 整体卡 1 分钟以上）。
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

from functools import lru_cache
from typing import Literal
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    _BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent

    model_config = SettingsConfigDict(
        env_file=str(_BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    LLM_PROVIDER: Literal["deepseek", "qwen", "minimax"] = "deepseek"

    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_MODEL: str = "deepseek-chat"
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"

    QWEN_API_KEY: str = ""
    QWEN_MODEL: str = "qwen-plus"
    QWEN_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    MINIMAX_API_KEY: str = ""
    MINIMAX_MODEL: str = "MiniMax-M2.7"
    MINIMAX_BASE_URL: str = "https://api.minimaxi.com/v1"

    EMBEDDING_MODEL: str = "BAAI/bge-small-zh-v1.5"
    EMBEDDING_DEVICE: str = "cpu"
    RERANK_MODEL: str = "BAAI/bge-reranker-base"

    DATABASE_URL: str = "sqlite+aiosqlite:///./data/app.db"

    CHROMA_PERSIST_DIR: str = "./data/chroma"
    TOP_K: int = 5

    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    APP_DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    HISTORY_BACKEND: str = "redis"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    HISTORY_TTL: int = 86400

@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()