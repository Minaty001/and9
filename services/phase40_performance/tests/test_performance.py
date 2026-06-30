"""
Tests for Phase 40 — Performance Optimization.
"""

import pytest
from services.phase40_performance import (
    PerformanceConfig,
    CacheEntry,
    CacheStats,
    L1Cache,
    L2Cache,
    RequestCoalescer,
    ResourcePool,
    LazyLoader,
    PerformanceOptimizerService,
)


class TestL1Cache:
    """Verify small, fast LRU cache."""

    def test_set_and_get(self):
        cache = L1Cache()
        cache.set("key", "value")
        val, hit = cache.get("key")
        assert val == "value"
        assert hit is True

    def test_get_miss(self):
        cache = L1Cache()
        val, hit = cache.get("nonexistent")
        assert val is None
        assert hit is False

    def test_eviction(self):
        cache = L1Cache()
        cache._capacity = 2
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)  # should evict 'a'
        val, hit = cache.get("a")
        assert hit is False
        val, hit = cache.get("c")
        assert val == 3

    def test_invalidate(self):
        cache = L1Cache()
        cache.set("key", "val")
        assert cache.invalidate("key") is True
        assert cache.get("key")[1] is False

    def test_invalidate_nonexistent(self):
        cache = L1Cache()
        assert cache.invalidate("nonexistent") is False

    def test_clear(self):
        cache = L1Cache()
        cache.set("a", 1)
        cache.set("b", 2)
        cache.clear()
        assert cache.get("a")[1] is False
        assert cache.get("b")[1] is False

    def test_stats(self):
        cache = L1Cache()
        cache.set("k", "v")
        cache.get("k")
        cache.get("missing")
        stats = cache.stats()
        assert stats.hit_count == 1
        assert stats.miss_count == 1
        assert stats.hit_ratio == 0.5


class TestL2Cache:
    """Verify larger LRU cache."""

    def test_set_and_get(self):
        cache = L2Cache()
        cache.set("key", "l2_value")
        val, hit = cache.get("key")
        assert val == "l2_value"
        assert hit is True

    def test_get_miss(self):
        cache = L2Cache()
        val, hit = cache.get("missing")
        assert val is None
        assert hit is False

    def test_invalidate(self):
        cache = L2Cache()
        cache.set("k", "v")
        assert cache.invalidate("k") is True
        assert cache.get("k")[1] is False

    def test_clear(self):
        cache = L2Cache()
        cache.set("a", 1)
        cache.clear()
        assert cache.get("a")[1] is False

    def test_stats(self):
        cache = L2Cache()
        cache.set("k", "v")
        cache.get("k")
        stats = cache.stats()
        assert stats.cache_name == "L2"


class TestRequestCoalescer:
    """Verify request deduplication."""

    @pytest.mark.asyncio
    async def test_coalesce(self):
        coalescer = RequestCoalescer()
        call_count = 0

        async def loader():
            nonlocal call_count
            call_count += 1
            return "result"

        result1 = await coalescer.coalesce("key", loader)
        result2 = await coalescer.coalesce("key", loader)
        assert result1 == "result"
        assert result2 == "result"
        assert call_count == 1  # loader called only once

    @pytest.mark.asyncio
    async def test_coalesce_unique_keys(self):
        coalescer = RequestCoalescer()
        call_count = 0

        async def make_loader(val):
            async def loader():
                nonlocal call_count
                call_count += 1
                return val
            return loader

        r1 = await coalescer.coalesce("k1", await make_loader("a"))
        r2 = await coalescer.coalesce("k2", await make_loader("b"))
        assert r1 == "a"
        assert r2 == "b"
        assert call_count == 2

    def test_get_stats(self):
        coalescer = RequestCoalescer()
        stats = coalescer.get_stats()
        assert "pending_requests" in stats


class TestResourcePool:
    """Verify resource pooling."""

    def test_acquire_release(self):
        pool = ResourcePool(creator=lambda: object())
        resource, rid = pool.acquire()
        assert resource is not None
        assert rid is not None
        assert pool.release(rid) is True

    def test_acquire_max(self):
        pool = ResourcePool()
        pool._max_size = 1
        pool._creator = lambda: object()
        r1, _ = pool.acquire()
        assert r1 is not None
        r2, _ = pool.acquire()
        assert r2 is None  # pool exhausted

    def test_release_invalid(self):
        pool = ResourcePool()
        assert pool.release("invalid") is False

    def test_stats(self):
        pool = ResourcePool(creator=lambda: {})
        pool.acquire()
        stats = pool.stats()
        assert stats["active"] == 1


class TestLazyLoader:
    """Verify lazy loading."""

    def test_load(self):
        loader = LazyLoader()
        call_count = 0

        def load_func():
            nonlocal call_count
            call_count += 1
            return "loaded_value"

        val = loader.load("key", load_func)
        assert val == "loaded_value"
        assert call_count == 1

        # Second access uses cache
        val2 = loader.load("key", load_func)
        assert val2 == "loaded_value"
        assert call_count == 1  # Not called again

    def test_is_loaded(self):
        loader = LazyLoader()
        assert loader.is_loaded("key") is False
        loader.load("key", lambda: "val")
        assert loader.is_loaded("key") is True

    def test_invalidate(self):
        loader = LazyLoader()
        loader.load("key", lambda: "val")
        assert loader.invalidate("key") is True
        assert loader.is_loaded("key") is False

    def test_clear(self):
        loader = LazyLoader()
        loader.load("a", lambda: 1)
        loader.load("b", lambda: 2)
        loader.clear()
        assert loader.is_loaded("a") is False
        assert loader.is_loaded("b") is False

    def test_get_stats(self):
        loader = LazyLoader()
        loader.load("k", lambda: "v")
        stats = loader.get_stats()
        assert stats["cached_items"] == 1


class TestPerformanceOptimizerService:
    """Verify service wrapper."""

    @pytest.mark.asyncio
    async def test_initialize(self):
        svc = PerformanceOptimizerService()
        assert await svc.initialize() is True

    @pytest.mark.asyncio
    async def test_l1_cache_ops(self):
        svc = PerformanceOptimizerService()
        await svc.initialize()
        svc.l1_set("test_key", "test_value")
        val, hit = svc.l1_get("test_key")
        assert hit is True
        assert val == "test_value"

    @pytest.mark.asyncio
    async def test_l2_cache_ops(self):
        svc = PerformanceOptimizerService()
        await svc.initialize()
        svc.l2_set("l2_key", "l2_value")
        val, hit = svc.l2_get("l2_key")
        assert hit is True
        assert val == "l2_value"

    @pytest.mark.asyncio
    async def test_coalesce(self):
        svc = PerformanceOptimizerService()
        await svc.initialize()

        async def loader():
            return "coalesced"

        result = await svc.coalesce("ck", loader)
        assert result == "coalesced"

    @pytest.mark.asyncio
    async def test_pool_ops(self):
        svc = PerformanceOptimizerService()
        await svc.initialize()
        resource, rid = svc.pool_acquire()
        if rid:
            assert svc.pool_release(rid) is True

    @pytest.mark.asyncio
    async def test_lazy_load(self):
        svc = PerformanceOptimizerService()
        await svc.initialize()
        val = svc.lazy_load("lk", lambda: "lazy_val")
        assert val == "lazy_val"

    @pytest.mark.asyncio
    async def test_benchmark(self):
        svc = PerformanceOptimizerService()
        await svc.initialize()
        result = svc.benchmark(lambda: 1 + 1, iterations=10)
        assert result["iterations"] == 10
        assert result["avg_ms"] >= 0

    @pytest.mark.asyncio
    async def test_health(self):
        svc = PerformanceOptimizerService()
        await svc.initialize()
        health = await svc.health()
        assert health["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_stats(self):
        svc = PerformanceOptimizerService()
        await svc.initialize()
        stats = await svc.stats()
        assert stats["service"] == "jarvis_performance"

    @pytest.mark.asyncio
    async def test_shutdown(self):
        svc = PerformanceOptimizerService()
        await svc.initialize()
        await svc.shutdown()
        assert not svc.is_initialized()
