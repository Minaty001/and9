"""
Tests for Phase 9 — Memory System.
"""

import pytest
from datetime import datetime, timezone, timedelta
from services.phase09_memory import (
    MemoryStore,
    MemoryItem,
    MemoryManager,
    MemoryService,
    MemoryConfig,
    MemoryType,
    MemoryQuery,
    MemoryStats,
)


class TestMemoryItem:
    """Verify MemoryItem model."""

    def test_create_item(self):
        item = MemoryItem(key="test_key", value="test_value", importance=0.8)
        assert item.key == "test_key"
        assert item.value == "test_value"
        assert item.importance == 0.8
        assert item.memory_type == MemoryType.WORKING
        assert item.access_count == 0

    def test_touch(self):
        item = MemoryItem(key="k", value="v")
        old = item.last_accessed
        item.touch()
        assert item.access_count == 1
        assert item.last_accessed >= old

    def test_age_seconds(self):
        item = MemoryItem(key="k", value="v")
        age = item.age_seconds()
        assert age >= 0


class TestMemoryStore:
    """Verify store CRUD and search."""

    def test_add_and_get(self):
        store = MemoryStore()
        item = MemoryItem(key="name", value="Alice", memory_type=MemoryType.LONG_TERM)
        store.add(item)
        retrieved = store.get("name")
        assert retrieved is not None
        assert retrieved.value == "Alice"
        assert retrieved.access_count == 1  # get calls touch()

    def test_get_missing(self):
        store = MemoryStore()
        assert store.get("nonexistent") is None

    def test_update(self):
        store = MemoryStore()
        store.add(MemoryItem(key="k", value="v1"))
        updated = store.update("k", value="v2", importance=0.9)
        assert updated is not None
        assert updated.value == "v2"
        assert updated.importance == 0.9

    def test_update_missing(self):
        store = MemoryStore()
        assert store.update("nonexistent", value="v") is None

    def test_delete(self):
        store = MemoryStore()
        store.add(MemoryItem(key="k", value="v"))
        assert store.delete("k") is True
        assert store.get("k") is None

    def test_delete_missing(self):
        store = MemoryStore()
        assert store.delete("nonexistent") is False

    def test_search_text(self):
        store = MemoryStore()
        store.add(MemoryItem(key="user_name", value="Alice", tags=["user", "contact"]))
        store.add(MemoryItem(key="weather_pref", value="Celsius", tags=["settings"]))
        results = store.search(MemoryQuery(text="alice"))
        assert len(results) == 1
        assert results[0].key == "user_name"

    def test_search_by_type(self):
        store = MemoryStore()
        lt = MemoryItem(key="lt", value="v", memory_type=MemoryType.LONG_TERM)
        w = MemoryItem(key="wk", value="v", memory_type=MemoryType.WORKING)
        store.add(lt)
        store.add(w)
        results = store.search(MemoryQuery(text="v", memory_type=MemoryType.LONG_TERM))
        assert len(results) == 1
        assert results[0].key == "lt"

    def test_search_by_tags(self):
        store = MemoryStore()
        store.add(MemoryItem(key="a", value="v", tags=["important", "user"]))
        store.add(MemoryItem(key="b", value="v", tags=["trivial"]))
        results = store.search(MemoryQuery(text="v", tags=["important"]))
        assert len(results) == 1
        assert results[0].key == "a"

    def test_search_min_importance(self):
        store = MemoryStore()
        store.add(MemoryItem(key="a", value="v", importance=0.9))
        store.add(MemoryItem(key="b", value="v", importance=0.3))
        results = store.search(MemoryQuery(text="v", min_importance=0.5))
        assert len(results) == 1
        assert results[0].key == "a"

    def test_clear(self):
        store = MemoryStore()
        store.add(MemoryItem(key="k", value="v"))
        store.clear()
        assert store.get("k") is None

    def test_list_by_type(self):
        store = MemoryStore()
        store.add(MemoryItem(key="a", value="v", memory_type=MemoryType.WORKING))
        store.add(MemoryItem(key="b", value="v", memory_type=MemoryType.LONG_TERM))
        items = store.list_by_type(MemoryType.WORKING)
        assert len(items) == 1

    def test_count_by_type(self):
        store = MemoryStore()
        store.add(MemoryItem(key="a", value="v", memory_type=MemoryType.WORKING))
        store.add(MemoryItem(key="b", value="v", memory_type=MemoryType.LONG_TERM))
        assert store.count_by_type(MemoryType.WORKING) == 1

    def test_get_stats(self):
        store = MemoryStore()
        store.add(MemoryItem(key="a", value="v", importance=0.8))
        store.add(MemoryItem(key="b", value="v", importance=0.4))
        stats = store.get_stats()
        assert stats.total_items == 2
        assert stats.avg_importance == 0.6  # (0.8 + 0.4) / 2

    def test_empty_stats(self):
        store = MemoryStore()
        stats = store.get_stats()
        assert stats.total_items == 0

    def test_eviction_lru(self):
        cfg = MemoryConfig(max_working_memories=10)
        store = MemoryStore(cfg)
        for i in range(15):
            store.add(MemoryItem(key=f"k{i}", value=f"v{i}", memory_type=MemoryType.WORKING))
        assert store.count_by_type(MemoryType.WORKING) == 10


class TestMemoryManager:
    """Verify manager-level operations."""

    def test_store_and_recall(self):
        mgr = MemoryManager()
        mgr.store("user_name", "Alice", memory_type=MemoryType.LONG_TERM, importance=0.9)
        results = mgr.recall("alice")
        assert len(results) >= 1
        assert results[0].key == "user_name"

    def test_store_update(self):
        mgr = MemoryManager()
        mgr.store("key", "v1")
        mgr.store("key", "v2")
        item = mgr.get_memory("key")
        assert item is not None
        assert item.value == "v2"

    def test_forget(self):
        mgr = MemoryManager()
        mgr.store("key", "value")
        assert mgr.forget("key") is True
        assert mgr.get_memory("key") is None

    def test_forget_missing(self):
        mgr = MemoryManager()
        assert mgr.forget("nonexistent") is False

    def test_consolidate_promotes_high_importance(self):
        cfg = MemoryConfig(consolidation_importance_threshold=0.6, auto_consolidate_on_store=False)
        mgr = MemoryManager(cfg)
        mgr.store("important", "v", importance=0.8)
        mgr.store("trivial", "v", importance=0.3)
        consolidated = mgr.consolidate()
        assert consolidated == 1
        # Important memory should now be long-term
        item = mgr.get_memory("important")
        assert item is not None
        assert item.memory_type == MemoryType.LONG_TERM
        # Trivial should remain working
        trivial = mgr.get_memory("trivial")
        assert trivial.memory_type == MemoryType.WORKING

    def test_auto_consolidate(self):
        cfg = MemoryConfig(consolidation_importance_threshold=0.5, auto_consolidate_on_store=True)
        mgr = MemoryManager(cfg)
        mgr.store("key", "v", importance=0.9)
        item = mgr.get_memory("key")
        assert item.memory_type == MemoryType.LONG_TERM

    def test_get_stats(self):
        mgr = MemoryManager()
        mgr.store("a", "v", importance=0.9)
        mgr.store("b", "v", importance=0.5)
        stats = mgr.get_stats()
        assert stats.total_items >= 2

    def test_clear(self):
        mgr = MemoryManager()
        mgr.store("k", "v")
        mgr.clear()
        assert mgr.get_memory("k") is None

    def test_recall_by_type(self):
        mgr = MemoryManager()
        mgr.store("a", "v1", memory_type=MemoryType.WORKING)
        mgr.store("b", "v2", memory_type=MemoryType.LONG_TERM)
        results = mgr.recall_by_type("v", memory_type=MemoryType.LONG_TERM)
        assert len(results) == 1
        assert results[0].key == "b"

    def test_list_recent(self):
        mgr = MemoryManager()
        mgr.store("a", "v1")
        mgr.store("b", "v2")
        recent = mgr.list_recent(limit=5)
        assert len(recent) >= 2


class TestMemoryService:
    """Verify service wrapper."""

    @pytest.mark.asyncio
    async def test_initialize(self):
        svc = MemoryService()
        result = await svc.initialize()
        assert result is True

    @pytest.mark.asyncio
    async def test_store_and_recall(self):
        svc = MemoryService()
        await svc.initialize()
        await svc.store("user_name", "Bob", memory_type="long_term", importance=0.9)
        results = await svc.recall("bob")
        assert len(results) >= 1
        assert results[0].value == "Bob"

    @pytest.mark.asyncio
    async def test_store_default_type(self):
        svc = MemoryService()
        await svc.initialize()
        item = await svc.store("k", "v")
        assert item.memory_type == MemoryType.WORKING

    @pytest.mark.asyncio
    async def test_consolidate(self):
        svc = MemoryService(MemoryConfig(
            consolidation_importance_threshold=0.7,
            auto_consolidate_on_store=False,
        ))
        await svc.initialize()
        await svc.store("important", "v", importance=0.9)
        count = await svc.consolidate()
        assert count == 1

    @pytest.mark.asyncio
    async def test_forget(self):
        svc = MemoryService()
        await svc.initialize()
        await svc.store("k", "v")
        assert await svc.forget("k") is True
        assert await svc.forget("k") is False

    @pytest.mark.asyncio
    async def test_get_memory(self):
        svc = MemoryService()
        await svc.initialize()
        await svc.store("k", "v")
        item = await svc.get_memory("k")
        assert item is not None
        assert item.key == "k"

    @pytest.mark.asyncio
    async def test_get_stats(self):
        svc = MemoryService()
        await svc.initialize()
        await svc.store("k1", "v1", importance=0.9)
        await svc.store("k2", "v2", importance=0.3)
        stats = await svc.get_stats()
        assert stats.total_items >= 2
        assert stats.long_term_count >= 1 or stats.working_count >= 1

    @pytest.mark.asyncio
    async def test_clear(self):
        svc = MemoryService()
        await svc.initialize()
        await svc.store("k", "v")
        await svc.clear()
        stats = await svc.get_stats()
        assert stats.total_items == 0

    @pytest.mark.asyncio
    async def test_health(self):
        svc = MemoryService()
        await svc.initialize()
        health = await svc.health()
        assert health["status"] == "healthy"
        assert "total_memories" in health

    @pytest.mark.asyncio
    async def test_shutdown(self):
        svc = MemoryService()
        await svc.initialize()
        await svc.shutdown()
        assert not svc.is_initialized()
