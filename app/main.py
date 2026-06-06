"""FastAPI 应用入口。"""
from contextlib import asynccontextmanager
from app.api.chat import router as chat_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import logger, setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info(f"🚀 启动 | LLM={settings.LLM_PROVIDER} | Port={settings.APP_PORT}")
    yield
    logger.info("👋 关闭")


app = FastAPI(
    title="AI 面试助手 API",
    description="基于 RAG 的面试问答系统",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(chat_router)

@app.get("/", tags=["system"])
async def root() -> dict:
    return {
        "message": "AI 面试助手 API",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", tags=["system"])
async def health_check() -> dict:
    return {
        "status": "ok",
        "llm_provider": settings.LLM_PROVIDER,
        "embedding_model": settings.EMBEDDING_MODEL,
        "version": "0.1.0",
    }