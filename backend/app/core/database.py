"""数据库引擎与会话管理（SQLAlchemy async）。"""
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# 确保 data 目录存在
_db_path = Path(settings.DATABASE_URL.split("///")[-1])
_db_path.parent.mkdir(parents=True, exist_ok=True)

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.APP_DEBUG,
    future=True,
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """FastAPI 依赖注入：获取异步数据库会话。"""
    async with async_session() as session:
        yield session


async def init_db() -> None:
    """创建所有表（应用启动时调用）。"""
    from app.models import Base  # noqa: F401 — 触发模型注册
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """关闭数据库引擎（应用关闭时调用）。"""
    await engine.dispose()
