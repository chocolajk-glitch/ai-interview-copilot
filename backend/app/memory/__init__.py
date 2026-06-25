from functools import lru_cache

from app.core.config import settings
from app.memory.chat_history_store import ChatHistoryStore
from app.memory.preference_store import UserPreferenceStore, get_preference_store


@lru_cache
def get_history_store() -> ChatHistoryStore:
    if settings.HISTORY_BACKEND == "redis":
        from app.memory.redis_store import RedisChatHistoryStore
        return RedisChatHistoryStore(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            ttl=settings.HISTORY_TTL,
        )
    from app.memory.in_memory_store import InMemoryChatHistoryStore
    return InMemoryChatHistoryStore()