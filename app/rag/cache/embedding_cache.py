"""Embedding 缓存：SHA-256 去重 + Redis TTL / 内存 dict 自动切换。"""
import hashlib
import json

from langchain_huggingface import HuggingFaceEmbeddings

from app.core.config import settings


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class EmbeddingCache:
    """内存 Embedding 缓存（默认）。"""

    def __init__(self, base: HuggingFaceEmbeddings):
        self._base = base
        self._cache: dict[str, list[float]] = {}
        self.hits = 0
        self.misses = 0

    def _get(self, key: str) -> list[float] | None:
        return self._cache.get(key)

    def _set(self, key: str, value: list[float]) -> None:
        self._cache[key] = value

    def embed_query(self, text: str) -> list[float]:
        key = _hash(text)
        cached = self._get(key)
        if cached is not None:
            self.hits += 1
            return cached
        self.misses += 1
        vec = self._base.embed_query(text)
        self._set(key, vec)
        return vec

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        results: list[list[float] | None] = [None] * len(texts)
        missing: list[tuple[int, str]] = []
        for i, t in enumerate(texts):
            key = _hash(t)
            cached = self._get(key)
            if cached is not None:
                self.hits += 1
                results[i] = cached
            else:
                missing.append((i, t))
        if missing:
            self.misses += len(missing)
            new_vecs = self._base.embed_documents([t for _, t in missing])
            for (i, t), vec in zip(missing, new_vecs):
                self._set(_hash(t), vec)
                results[i] = vec
        return results  # type: ignore

    def stats(self) -> dict:
        total = self.hits + self.misses
        return {
            "hits": self.hits,
            "misses": self.misses,
            "size": len(self._cache),
            "hit_rate": round(self.hits / total, 4) if total > 0 else 0.0,
            "backend": "memory",
        }


class RedisEmbeddingCache(EmbeddingCache):
    """Redis Embedding 缓存：SHA-256 去重 + Redis TTL。"""

    def __init__(self, base: HuggingFaceEmbeddings, ttl: int = 86400):
        super().__init__(base)
        import redis
        self._redis = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True,
        )
        self._ttl = ttl
        self._prefix = "emb_cache:"

    def _get(self, key: str) -> list[float] | None:
        data = self._redis.get(self._prefix + key)
        if data is not None:
            return json.loads(data)
        # 也查内存缓存（双缓存）
        return self._cache.get(key)

    def _set(self, key: str, value: list[float]) -> None:
        self._cache[key] = value
        self._redis.setex(self._prefix + key, self._ttl, json.dumps(value))

    def stats(self) -> dict:
        total = self.hits + self.misses
        return {
            "hits": self.hits,
            "misses": self.misses,
            "size": len(self._cache),
            "hit_rate": round(self.hits / total, 4) if total > 0 else 0.0,
            "backend": "redis",
        }


def create_embedding_cache(base: HuggingFaceEmbeddings) -> EmbeddingCache:
    """根据配置自动选择缓存后端。"""
    if settings.HISTORY_BACKEND == "redis":
        try:
            return RedisEmbeddingCache(base)
        except Exception:
            pass  # Redis 不可用时降级到内存
    return EmbeddingCache(base)
