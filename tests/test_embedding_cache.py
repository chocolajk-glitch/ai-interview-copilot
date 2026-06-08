from app.rag.cache.embedding_cache import EmbeddingCache, _hash


class _FakeEmbeddings:
    def __init__(self):
        self.query_calls = 0
        self.doc_calls = 0

    def embed_query(self, text: str) -> list[float]:
        self.query_calls += 1
        return [float(len(text)), 0.0, 0.0]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.doc_calls += 1
        return [[float(len(t)), 0.0, 0.0] for t in texts]


def test_hash_is_deterministic_and_unique():
    assert _hash("两数之和") == _hash("两数之和")
    assert _hash("a") != _hash("b")
    assert len(_hash("x")) == 64


def test_embed_query_caches_result():
    fake = _FakeEmbeddings()
    cache = EmbeddingCache(fake)
    v1 = cache.embed_query("hello")
    v2 = cache.embed_query("hello")
    assert v1 == v2
    assert fake.query_calls == 1
    assert cache.hits == 1
    assert cache.misses == 1


def test_embed_documents_partial_hit():
    fake = _FakeEmbeddings()
    cache = EmbeddingCache(fake)
    cache.embed_documents(["a"])
    result = cache.embed_documents(["a", "b", "a"])
    assert len(result) == 3
    assert result[0] == result[2]
    assert fake.doc_calls == 2
    assert cache.hits == 2
    assert cache.misses == 2


def test_stats_hit_rate():
    fake = _FakeEmbeddings()
    cache = EmbeddingCache(fake)
    cache.embed_query("x")
    cache.embed_query("x")
    cache.embed_query("y")
    s = cache.stats()
    assert s["hits"] == 1
    assert s["misses"] == 2
    assert s["size"] == 2
    assert 0 < s["hit_rate"] < 1


def test_real_bge_cache_hit():
    from app.rag.embeddings.bge import get_embeddings
    emb = get_embeddings()
    emb._cache.clear()
    emb.hits = 0
    emb.misses = 0
    # 如果是 Redis 缓存，也需要清理 Redis
    if hasattr(emb, "_redis"):
        for key in emb._redis.scan_iter(emb._prefix + "*"):
            emb._redis.delete(key)
    emb.embed_query("哈希表")
    emb.embed_query("哈希表")
    emb.embed_query("哈希表")
    s = emb.stats()
    assert s["misses"] == 1
    assert s["hits"] >= 2  # 内存缓存或 Redis 双缓存都至少 2 次命中
    assert s["size"] == 1


def test_real_chroma_search_uses_cache():
    from app.rag.embeddings.bge import get_embeddings
    from app.rag.retrievers.vector_retriever import similarity_search
    emb = get_embeddings()
    emb._cache.clear()
    emb.hits = 0
    emb.misses = 0
    similarity_search("哈希表", k=3)
    s1 = emb.stats()
    similarity_search("哈希表", k=3)
    s2 = emb.stats()
    assert s2["hits"] > s1["hits"]