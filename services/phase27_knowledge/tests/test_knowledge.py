"""
Tests for Phase 27 — Knowledge Base.
"""

import pytest
from services.phase27_knowledge import (
    KnowledgeStore,
    KnowledgeBase,
    KnowledgeBaseService,
    KnowledgeConfig,
    KnowledgeEntry,
    KnowledgeQuery,
    KnowledgeResult,
)


class TestKnowledgeStore:
    """Verify in-memory storage operations."""

    def test_add_and_get(self):
        store = KnowledgeStore()
        entry = KnowledgeEntry(id="1", question="Q1", answer="A1")
        store.add(entry)
        retrieved = store.get("1")
        assert retrieved is not None
        assert retrieved.question == "Q1"
        assert retrieved.access_count == 1  # incremented on get

    def test_get_nonexistent(self):
        store = KnowledgeStore()
        assert store.get("nonexistent") is None

    def test_update(self):
        store = KnowledgeStore()
        store.add(KnowledgeEntry(id="1", question="Q1", answer="A1"))
        updated = store.update("1", answer="A2")
        assert updated is not None
        assert updated.answer == "A2"

    def test_update_nonexistent(self):
        store = KnowledgeStore()
        assert store.update("x") is None

    def test_delete(self):
        store = KnowledgeStore()
        store.add(KnowledgeEntry(id="1", question="Q", answer="A"))
        assert store.delete("1") is True
        assert store.get("1") is None

    def test_delete_nonexistent(self):
        store = KnowledgeStore()
        assert store.delete("x") is False

    def test_search(self):
        store = KnowledgeStore()
        store.add(KnowledgeEntry(id="1", question="What is AI?", answer="Artificial Intelligence"))
        store.add(KnowledgeEntry(id="2", question="What is ML?", answer="Machine Learning"))
        results = store.search("AI")
        assert len(results) == 1
        assert results[0].id == "1"

    def test_get_by_tag(self):
        store = KnowledgeStore()
        store.add(KnowledgeEntry(id="1", question="Q", answer="A", tags=["python", "code"]))
        tagged = store.get_by_tag("python")
        assert len(tagged) == 1

    def test_get_by_category(self):
        store = KnowledgeStore()
        store.add(KnowledgeEntry(id="1", question="Q", answer="A", category="tech"))
        cats = store.get_by_category("tech")
        assert len(cats) == 1

    def test_count(self):
        store = KnowledgeStore()
        assert store.count() == 0
        store.add(KnowledgeEntry(id="1", question="Q", answer="A"))
        assert store.count() == 1

    def test_clear(self):
        store = KnowledgeStore()
        store.add(KnowledgeEntry(id="1", question="Q", answer="A"))
        store.clear()
        assert store.count() == 0


class TestKnowledgeBase:
    """Verify high-level KB operations."""

    def test_add_knowledge(self):
        store = KnowledgeStore()
        kb = KnowledgeBase(store)
        entry = kb.add_knowledge("Q1", "A1", "general")
        assert entry.question == "Q1"
        assert store.count() == 1

    def test_query(self):
        store = KnowledgeStore()
        kb = KnowledgeBase(store)
        kb.add_knowledge("What is AI?", "Artificial Intelligence", "tech", ["ai"])
        result = kb.query(KnowledgeQuery(query="AI"))
        assert result.total_found >= 1
        assert result.entries[0].category == "tech"

    def test_query_no_results(self):
        store = KnowledgeStore()
        kb = KnowledgeBase(store)
        result = kb.query(KnowledgeQuery(query="nonexistent"))
        assert result.total_found == 0

    def test_find_related_empty(self):
        store = KnowledgeStore()
        kb = KnowledgeBase(store)
        entry = kb.add_knowledge("Q", "A")
        related = kb.find_related(entry.id)
        assert isinstance(related, list)

    def test_import_from_dict(self):
        store = KnowledgeStore()
        kb = KnowledgeBase(store)
        data = [
            {"question": "Q1", "answer": "A1"},
            {"question": "Q2", "answer": "A2", "category": "tech"},
        ]
        count = kb.import_from_dict(data)
        assert count == 2
        assert store.count() == 2

    def test_export_to_dict(self):
        store = KnowledgeStore()
        kb = KnowledgeBase(store)
        kb.add_knowledge("Q1", "A1")
        exported = kb.export_to_dict()
        assert len(exported) == 1
        assert exported[0]["question"] == "Q1"

    def test_bulk_add(self):
        store = KnowledgeStore()
        kb = KnowledgeBase(store)
        entries = [
            KnowledgeEntry(id="1", question="Q1", answer="A1"),
            KnowledgeEntry(id="2", question="Q2", answer="A2"),
        ]
        count = kb.bulk_add(entries)
        assert count == 2

    def test_get_stats_empty(self):
        store = KnowledgeStore()
        kb = KnowledgeBase(store)
        stats = kb.get_stats()
        assert stats["total_entries"] == 0


class TestKnowledgeBaseService:
    """Verify service wrapper."""

    @pytest.mark.asyncio
    async def test_initialize(self):
        svc = KnowledgeBaseService()
        assert await svc.initialize() is True

    @pytest.mark.asyncio
    async def test_add_and_query(self):
        svc = KnowledgeBaseService()
        await svc.initialize()
        await svc.add("Q1", "A1", "general", ["tag1"])
        result = await svc.query(KnowledgeQuery(query="Q1"))
        assert result.total_found >= 1

    @pytest.mark.asyncio
    async def test_get_entry(self):
        svc = KnowledgeBaseService()
        await svc.initialize()
        entry = await svc.add("Q", "A")
        retrieved = await svc.get_entry(entry.id)
        assert retrieved is not None

    @pytest.mark.asyncio
    async def test_update(self):
        svc = KnowledgeBaseService()
        await svc.initialize()
        entry = await svc.add("Q", "A")
        updated = await svc.update(entry.id, answer="A2")
        assert updated.answer == "A2"

    @pytest.mark.asyncio
    async def test_delete(self):
        svc = KnowledgeBaseService()
        await svc.initialize()
        entry = await svc.add("Q", "A")
        assert await svc.delete(entry.id) is True

    @pytest.mark.asyncio
    async def test_import_export(self):
        svc = KnowledgeBaseService()
        await svc.initialize()
        data = [{"question": "Q", "answer": "A"}]
        count = await svc.import_data(data)
        assert count == 1
        exported = await svc.export_data()
        assert len(exported) == 1

    @pytest.mark.asyncio
    async def test_get_by_tag(self):
        svc = KnowledgeBaseService()
        await svc.initialize()
        await svc.add("Q", "A", tags=["test-tag"])
        tagged = await svc.get_by_tag("test-tag")
        assert len(tagged) >= 1

    @pytest.mark.asyncio
    async def test_get_by_category(self):
        svc = KnowledgeBaseService()
        await svc.initialize()
        await svc.add("Q", "A", category="test-cat")
        cats = await svc.get_by_category("test-cat")
        assert len(cats) >= 1

    @pytest.mark.asyncio
    async def test_health(self):
        svc = KnowledgeBaseService()
        await svc.initialize()
        health = await svc.health()
        assert health["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_stats(self):
        svc = KnowledgeBaseService()
        await svc.initialize()
        stats = await svc.stats()
        assert stats["service"] == "jarvis_knowledge"

    @pytest.mark.asyncio
    async def test_shutdown(self):
        svc = KnowledgeBaseService()
        await svc.initialize()
        await svc.shutdown()
        assert not svc.is_initialized()
