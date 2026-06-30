"""
Tests for Phase 5 — Embedding Engine.
"""

import pytest
from services.phase05_embedding import (
    HybridEmbedding,
    Embedder,
    EmbeddingCache,
    EmbeddingService,
    cosine_similarity,
    top_k_similar,
    EmbeddingVector,
    SearchResult,
)
from services.phase05_embedding.errors import DimensionMismatchError


class TestHybridEmbedding:
    """Verify the hybrid embedding engine."""

    def test_embedding_dimension(self):
        engine = HybridEmbedding()
        vector = engine.embed("hello world")
        assert len(vector) == 128

    def test_embedding_values(self):
        engine = HybridEmbedding()
        v1 = engine.embed("hello world")
        v2 = engine.embed("hello world")
        assert v1 == v2  # deterministic

    def test_different_texts_different_vectors(self):
        engine = HybridEmbedding()
        v1 = engine.embed("open whatsapp")
        v2 = engine.embed("close whatsapp")
        assert v1 != v2

    def test_empty_text(self):
        engine = HybridEmbedding()
        vector = engine.embed("")
        assert all(v == 0.0 for v in vector)

    def test_char_frequency(self):
        engine = HybridEmbedding()
        vector = engine.embed("aaa")  # all 'a's
        # First 26 dims: char frequency
        assert vector[0] > 0  # 'a' should be dominant
        assert all(v == 0.0 for v in vector[1:26])  # other letters absent

    def test_keyword_groups(self):
        engine = HybridEmbedding()
        vector = engine.embed("open whatsapp")
        # Last 20 dims: intent keyword groups
        keyword_dims = vector[108:]  # last 20 dims
        assert any(v > 0 for v in keyword_dims)  # some keyword group should fire

    def test_direction_features(self):
        engine = HybridEmbedding()
        vector = engine.embed("turn on flashlight")
        direction_dims = vector[92:102]  # 10 dims
        assert any(v != 0 for v in direction_dims)

    def test_structural_features(self):
        engine = HybridEmbedding()
        v_q = engine.embed("is it working?")
        v_ex = engine.embed("wow!")
        struct_dims_q = v_q[102:108]  # 6 structural dims
        struct_dims_ex = v_ex[102:108]
        assert struct_dims_q[2] > 0  # question flag
        assert struct_dims_ex[3] > 0  # exclamation flag

    def test_case_insensitive(self):
        engine = HybridEmbedding()
        v1 = engine.embed("OPEN WHATSAPP")
        v2 = engine.embed("open whatsapp")
        assert v1 == v2  # case shouldn't matter


class TestSimilarity:
    """Verify similarity functions."""

    def test_cosine_similarity_identical(self):
        v = [1.0, 0.0, 0.0]
        score = cosine_similarity(v, v)
        assert pytest.approx(score, 0.001) == 1.0

    def test_cosine_similarity_orthogonal(self):
        v1 = [1.0, 0.0]
        v2 = [0.0, 1.0]
        score = cosine_similarity(v1, v2)
        assert pytest.approx(score, 0.001) == 0.0

    def test_cosine_similarity_opposite(self):
        v1 = [1.0, 0.0]
        v2 = [-1.0, 0.0]
        score = cosine_similarity(v1, v2)
        assert pytest.approx(score, 0.001) == -1.0

    def test_cosine_dimension_mismatch(self):
        with pytest.raises(DimensionMismatchError):
            cosine_similarity([1.0, 0.0], [1.0])

    def test_cosine_empty_vectors(self):
        assert cosine_similarity([], []) == 0.0

    def test_top_k_similar(self):
        query = [1.0, 0.0]
        candidates = [
            ("a", [1.0, 0.0]),   # score = 1.0
            ("b", [0.0, 1.0]),   # score = 0.0
            ("c", [0.5, 0.5]),   # score = 0.707
        ]
        results = top_k_similar(query, candidates, k=2)
        assert len(results) == 2
        assert results[0][0] == "a"  # most similar
        assert results[1][0] == "c"  # second most similar

    def test_top_k_with_threshold(self):
        query = [1.0, 0.0]
        candidates = [
            ("a", [1.0, 0.0]),
            ("b", [0.0, 1.0]),
        ]
        results = top_k_similar(query, candidates, k=5, threshold=0.5)
        assert len(results) == 1
        assert results[0][0] == "a"


class TestEmbeddingCache:
    """Verify cache behavior."""

    def test_get_miss(self):
        cache = EmbeddingCache(max_size=10, ttl_seconds=300)
        result = cache.get("hello")
        assert result is None

    def test_put_and_get(self):
        cache = EmbeddingCache(max_size=10, ttl_seconds=300)
        cache.put("hello", [0.1, 0.2, 0.3])
        result = cache.get("hello")
        assert result == [0.1, 0.2, 0.3]

    def test_cache_stats(self):
        cache = EmbeddingCache(max_size=10, ttl_seconds=300)
        cache.put("a", [1.0])
        cache.get("a")  # hit
        cache.get("b")  # miss
        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5

    def test_cache_eviction(self):
        cache = EmbeddingCache(max_size=2, ttl_seconds=300)
        cache.put("a", [1.0])
        cache.put("b", [2.0])
        cache.put("c", [3.0])  # should evict oldest (a)
        assert cache.get("a") is None  # evicted
        assert cache.get("b") is not None
        assert cache.get("c") is not None

    def test_clear(self):
        cache = EmbeddingCache(max_size=10, ttl_seconds=300)
        cache.put("a", [1.0])
        cache.clear()
        assert cache.get("a") is None
        assert cache.get_stats()["size"] == 0

    def test_invalidate(self):
        cache = EmbeddingCache(max_size=10, ttl_seconds=300)
        cache.put("a", [1.0])
        cache.invalidate("a")
        assert cache.get("a") is None


class TestEmbedder:
    """Verify high-level embedder with cache."""

    def test_embed(self):
        embedder = Embedder()
        result = embedder.embed("hello world")
        assert isinstance(result, EmbeddingVector)
        assert result.dimension == 128
        assert len(result.vector) == 128

    def test_embed_caching(self):
        embedder = Embedder()
        r1 = embedder.embed("test", use_cache=True)
        r2 = embedder.embed("test", use_cache=True)
        assert r1.metadata.get("cached") is False  # first
        assert r2.metadata.get("cached") is True  # cached

    def test_embed_batch(self):
        embedder = Embedder()
        results = embedder.embed_batch(["a", "b", "c"])
        assert len(results) == 3
        assert all(r.dimension == 128 for r in results)

    def test_normalization(self):
        embedder = Embedder()
        result = embedder.embed("hello", use_cache=False)
        magnitude = sum(v * v for v in result.vector) ** 0.5
        assert pytest.approx(magnitude, 0.01) == 1.0  # unit vector


class TestEmbeddingService:
    """Verify service wrapper."""

    @pytest.mark.asyncio
    async def test_initialize(self):
        svc = EmbeddingService()
        result = await svc.initialize()
        assert result is True

    @pytest.mark.asyncio
    async def test_embed(self):
        svc = EmbeddingService()
        await svc.initialize()
        result = await svc.embed("hello")
        assert result.dimension == 128

    @pytest.mark.asyncio
    async def test_similarity(self):
        svc = EmbeddingService()
        await svc.initialize()
        score = await svc.similarity([1.0, 0.0], [1.0, 0.0])
        assert pytest.approx(score, 0.001) == 1.0

    @pytest.mark.asyncio
    async def test_search(self):
        svc = EmbeddingService()
        await svc.initialize()
        results = await svc.search("hello", ["hello world", "goodbye", "hi there"], k=2)
        assert len(results) > 0
        assert isinstance(results[0], SearchResult)

    @pytest.mark.asyncio
    async def test_store_and_store_vector(self):
        svc = EmbeddingService()
        await svc.initialize()
        vec = await svc.embed("test")
        await svc.store_vector(vec)
        health = await svc.health()
        assert health["vector_store_size"] >= 1

    @pytest.mark.asyncio
    async def test_stats(self):
        svc = EmbeddingService()
        await svc.initialize()
        await svc.embed("test")
        stats = await svc.stats()
        assert "cache" in stats
        assert "metrics" in stats

    @pytest.mark.asyncio
    async def test_health(self):
        svc = EmbeddingService()
        await svc.initialize()
        health = await svc.health()
        assert health["status"] == "healthy"
