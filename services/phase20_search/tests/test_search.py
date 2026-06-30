"""
Tests for Phase 20 — Search Engine.
"""

import time
import pytest
from services.phase20_search import (
    SearchConfig,
    SearchResult,
    SearchQuery,
    WebSearcher,
    MemorySearcher,
    DocumentSearcher,
    SearchMerger,
    SearchCache,
    SearchEngineService,
)


class TestSearchResult:
    """Verify SearchResult creation."""

    def test_create_result(self):
        r = SearchResult(
            id="test_001",
            title="Test Result",
            snippet="A test snippet.",
            source="web",
            score=0.95,
        )
        assert r.id == "test_001"
        assert r.title == "Test Result"
        assert r.source == "web"
        assert r.score == 0.95

    def test_result_defaults(self):
        r = SearchResult(id="r1", title="Default Test")
        assert r.snippet == ""
        assert r.score == 1.0
        assert r.source == "web"
        assert r.url is None


class TestSearchQuery:
    """Verify SearchQuery creation."""

    def test_create_query(self):
        q = SearchQuery(text="hello world", intent="greeting")
        assert q.text == "hello world"
        assert q.intent == "greeting"
        assert q.max_results == 20

    def test_query_with_filters(self):
        q = SearchQuery(
            text="test",
            filters={"language": "en"},
            sources=["web", "document"],
            min_score=0.5,
        )
        assert "language" in q.filters
        assert q.min_score == 0.5
        assert len(q.sources) == 2


class TestWebSearcher:
    """Verify web search behavior."""

    def test_search_with_results(self):
        searcher = WebSearcher()
        results = searcher.search("python")
        assert len(results) >= 1
        assert results[0].source == "web"

    def test_search_empty_results(self):
        searcher = WebSearcher()
        results = searcher.search("xyznonexistentquery999")
        assert len(results) == 0

    def test_custom_results(self):
        searcher = WebSearcher()
        custom = [
            SearchResult(id="w1", title="Custom Web", snippet="Custom", source="web"),
            SearchResult(id="w2", title="Custom Web 2", snippet="Custom 2", source="web"),
        ]
        searcher.set_custom_results(custom)
        results = searcher.search("anything")
        assert len(results) == 2
        assert results[0].id == "w1"

    def test_search_max_results(self):
        searcher = WebSearcher()
        results = searcher.search("a", max_results=2)
        assert len(results) <= 2


class TestMemorySearcher:
    """Verify memory search behavior."""

    def test_search_with_results(self):
        searcher = MemorySearcher()
        results = searcher.search("name")
        assert len(results) >= 1
        assert results[0].source == "memory"

    def test_search_empty_results(self):
        searcher = MemorySearcher()
        results = searcher.search("xyznonexistent999")
        assert len(results) == 0

    def test_add_memory(self):
        searcher = MemorySearcher()
        r = SearchResult(id="m1", title="New Memory", snippet="New", source="memory")
        searcher.add_memory(r)
        results = searcher.search("New Memory")
        assert len(results) >= 1

    def test_clear_memory(self):
        searcher = MemorySearcher()
        searcher.clear_memory()
        results = searcher.search("name")
        assert len(results) == 0


class TestDocumentSearcher:
    """Verify document search behavior."""

    def test_search_with_results(self):
        searcher = DocumentSearcher()
        results = searcher.search("installation")
        assert len(results) >= 1
        assert results[0].source == "document"

    def test_search_empty_results(self):
        searcher = DocumentSearcher()
        results = searcher.search("xyznonexistent999")
        assert len(results) == 0

    def test_add_document(self):
        searcher = DocumentSearcher()
        r = SearchResult(id="d1", title="New Doc", snippet="New", source="document")
        searcher.add_document(r)
        results = searcher.search("New Doc")
        assert len(results) >= 1

    def test_clear_documents(self):
        searcher = DocumentSearcher()
        searcher.clear_documents()
        results = searcher.search("installation")
        assert len(results) == 0


class TestSearchMerger:
    """Verify merging and ranking."""

    def test_merge_single_source(self):
        merger = SearchMerger()
        web = [
            SearchResult(id="w1", title="Result A", snippet="A", source="web", score=0.9),
            SearchResult(id="w2", title="Result B", snippet="B", source="web", score=0.8),
        ]
        merged = merger.merge(web_results=web, memory_results=[], doc_results=[])
        assert len(merged) == 2
        assert merged[0].score >= merged[1].score

    def test_merge_multiple_sources(self):
        merger = SearchMerger()
        web = [SearchResult(id="w1", title="Web Result", snippet="Web", source="web", score=0.9)]
        mem = [SearchResult(id="m1", title="Memory Result", snippet="Mem", source="memory", score=0.85)]
        doc = [SearchResult(id="d1", title="Doc Result", snippet="Doc", source="document", score=0.8)]
        merged = merger.merge(web_results=web, memory_results=mem, doc_results=doc)
        assert len(merged) == 3

    def test_deduplication_by_title(self):
        merger = SearchMerger()
        web = [SearchResult(id="w1", title="Same Title", snippet="Web version", source="web", score=0.9)]
        mem = [SearchResult(id="m1", title="Same Title", snippet="Memory version", source="memory", score=0.8)]
        merged = merger.merge(web_results=web, memory_results=mem, doc_results=[])
        # Should keep the higher score version
        assert len(merged) == 1
        assert merged[0].id == "w1"

    def test_deduplication_by_url(self):
        merger = SearchMerger()
        web = [
            SearchResult(
                id="w1", title="Web Result", snippet="First", source="web", score=0.9,
                url="https://example.com/page",
            ),
        ]
        mem = [
            SearchResult(
                id="m1", title="Memory Result", snippet="Second", source="memory", score=0.8,
                url="https://example.com/page",
            ),
        ]
        merged = merger.merge(web_results=web, memory_results=mem, doc_results=[])
        assert len(merged) == 1

    def test_score_filtering(self):
        merger = SearchMerger()
        results = [
            SearchResult(id="r1", title="High", snippet="High", source="web", score=0.9),
            SearchResult(id="r2", title="Low", snippet="Low", source="web", score=0.2),
        ]
        merged = merger.merge(web_results=results, memory_results=[], doc_results=[], min_score=0.5)
        assert len(merged) == 1
        assert merged[0].id == "r1"

    def test_max_results(self):
        merger = SearchMerger()
        web = [SearchResult(id=f"r{i}", title=f"Result {i}", snippet="", source="web", score=1.0 - i * 0.1) for i in range(10)]
        merged = merger.merge(web_results=web, memory_results=[], doc_results=[], max_results=3)
        assert len(merged) == 3


class TestSearchCache:
    """Verify cache behavior."""

    def test_set_and_get(self):
        cache = SearchCache(default_ttl=300)
        results = [SearchResult(id="c1", title="Cached", snippet="Cached result", source="web")]
        assert cache.set("test_key", results) is True
        cached = cache.get("test_key")
        assert cached is not None
        assert len(cached) == 1
        assert cached[0].id == "c1"

    def test_get_missing(self):
        cache = SearchCache()
        assert cache.get("nonexistent") is None

    def test_get_expired(self):
        cache = SearchCache(default_ttl=0)  # Zero TTL = immediately expired
        results = [SearchResult(id="c1", title="Cached", snippet="Cached", source="web")]
        cache.set("key", results)
        time.sleep(0.01)
        cached = cache.get("key")
        assert cached is None

    def test_invalidate(self):
        cache = SearchCache()
        cache.set("key", [SearchResult(id="c1", title="Test", snippet="", source="web")])
        assert cache.invalidate("key") is True
        assert cache.get("key") is None

    def test_invalidate_missing(self):
        cache = SearchCache()
        assert cache.invalidate("nonexistent") is False

    def test_clear(self):
        cache = SearchCache()
        cache.set("k1", [SearchResult(id="c1", title="T1", snippet="", source="web")])
        cache.set("k2", [SearchResult(id="c2", title="T2", snippet="", source="web")])
        count = cache.clear()
        assert count == 2
        assert cache.size == 0

    def test_lru_eviction(self):
        cache = SearchCache(default_ttl=300, max_size=2)
        cache.set("k1", [SearchResult(id="c1", title="T1", snippet="", source="web")])
        cache.set("k2", [SearchResult(id="c2", title="T2", snippet="", source="web")])
        cache.set("k3", [SearchResult(id="c3", title="T3", snippet="", source="web")])
        # k1 should be evicted
        assert cache.get("k1") is None
        assert cache.get("k2") is not None
        assert cache.get("k3") is not None


class TestSearchEngineService:
    """Verify service wrapper."""

    @pytest.mark.asyncio
    async def test_initialize(self):
        svc = SearchEngineService()
        assert await svc.initialize() is True

    @pytest.mark.asyncio
    async def test_shutdown(self):
        svc = SearchEngineService()
        await svc.initialize()
        await svc.shutdown()
        assert not svc.is_initialized()

    @pytest.mark.asyncio
    async def test_health(self):
        svc = SearchEngineService()
        await svc.initialize()
        health = await svc.health()
        assert health["status"] == "healthy"
        assert health["service_name"] == "jarvis_search"

    @pytest.mark.asyncio
    async def test_stats(self):
        svc = SearchEngineService()
        await svc.initialize()
        stats = await svc.stats()
        assert stats["service"] == "jarvis_search"
        assert "metrics" in stats

    @pytest.mark.asyncio
    async def test_search_string(self):
        svc = SearchEngineService()
        await svc.initialize()
        results = await svc.search("python")
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_search_query_object(self):
        svc = SearchEngineService()
        await svc.initialize()
        q = SearchQuery(text="python", max_results=5)
        results = await svc.search(q)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_search_web(self):
        svc = SearchEngineService()
        await svc.initialize()
        results = await svc.search_web("python")
        assert len(results) >= 1
        assert all(r.source == "web" for r in results)

    @pytest.mark.asyncio
    async def test_search_memory(self):
        svc = SearchEngineService()
        await svc.initialize()
        results = await svc.search_memory("name")
        assert len(results) >= 1
        assert all(r.source == "memory" for r in results)

    @pytest.mark.asyncio
    async def test_search_documents(self):
        svc = SearchEngineService()
        await svc.initialize()
        results = await svc.search_documents("installation")
        assert len(results) >= 1
        assert all(r.source == "document" for r in results)

    @pytest.mark.asyncio
    async def test_cache_management(self):
        svc = SearchEngineService()
        await svc.initialize()
        # First search populates cache
        await svc.search("python")
        # Invalidate
        assert await svc.invalidate_cache("python") is True
        # Clear
        assert await svc.clear_cache() >= 0

    @pytest.mark.asyncio
    async def test_search_empty(self):
        svc = SearchEngineService()
        await svc.initialize()
        results = await svc.search("xyznonexistent999")
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_search_caching(self):
        svc = SearchEngineService()
        await svc.initialize()

        # First call - should search and cache
        results1 = await svc.search("python")
        assert len(results1) >= 1

        # Second call - should hit cache
        results2 = await svc.search("python")
        assert len(results2) >= 1
        # Results should be identical (cached)
        assert results1[0].id == results2[0].id
