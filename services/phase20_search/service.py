"""
Phase 20 — Search Engine Service.

ServiceBase wrapper for unified web, memory, and document search.
"""

from __future__ import annotations

import time
import logging
from typing import Any, Dict, List, Optional

from services.base.service_base import ServiceBase
from .config import SearchConfig
from .models import SearchResult, SearchQuery
from .web_searcher import WebSearcher
from .memory_searcher import MemorySearcher
from .document_searcher import DocumentSearcher
from .merger import SearchMerger
from .cache import SearchCache

logger = logging.getLogger(__name__)


class SearchEngineService(ServiceBase):
    """Unified search engine service combining web, memory, and document search.

    Usage:
        svc = SearchEngineService()
        await svc.initialize()
        results = await svc.search("python programming")
    """

    def __init__(self, config: Optional[SearchConfig] = None):
        super().__init__(name="jarvis_search", version="1.0.0")
        self.config = config or SearchConfig()
        self.web_searcher: Optional[WebSearcher] = None
        self.memory_searcher: Optional[MemorySearcher] = None
        self.document_searcher: Optional[DocumentSearcher] = None
        self.merger: Optional[SearchMerger] = None
        self.cache: Optional[SearchCache] = None
        self._start_time = 0.0

    async def initialize(self) -> bool:
        self._start_time = time.time()
        try:
            self.web_searcher = WebSearcher()
            self.memory_searcher = MemorySearcher()
            self.document_searcher = DocumentSearcher()
            self.merger = SearchMerger()
            self.cache = SearchCache(default_ttl=self.config.cache_ttl_seconds)
            self._metrics.reset()
            self._initialized = True
            logger.info("SearchEngineService initialized")
            return True
        except Exception as e:
            logger.error("SearchEngineService init failed: %s", e)
            return False

    async def shutdown(self) -> None:
        logger.info("SearchEngineService shutting down...")
        self._initialized = False

    async def search(self, query: Any) -> List[SearchResult]:
        """Perform a combined search across all enabled sources.

        Args:
            query: Either a string or a SearchQuery object.

        Returns:
            Merged and ranked list of SearchResult objects.
        """
        if not self._initialized or not self.merger:
            raise RuntimeError("SearchEngineService not initialized")

        search_query = self._resolve_query(query)
        cache_key = search_query.text.lower().strip()

        # Check cache
        if self.config.enable_cache and self.cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                self._metrics.counter("cache_hits", 1)
                return cached

        t0 = time.perf_counter()

        # Gather results from enabled sources
        sources = search_query.sources
        web_results: List[SearchResult] = []
        memory_results: List[SearchResult] = []
        doc_results: List[SearchResult] = []

        if self.config.enable_web_search and (not sources or "web" in sources):
            web_results = self.web_searcher.search(search_query.text)
            self._metrics.counter("web_searches", 1)

        if self.config.enable_memory_search and (not sources or "memory" in sources):
            memory_results = self.memory_searcher.search(search_query.text)
            self._metrics.counter("memory_searches", 1)

        if self.config.enable_document_search and (not sources or "document" in sources):
            doc_results = self.document_searcher.search(search_query.text)
            self._metrics.counter("document_searches", 1)

        # Merge results
        min_score = max(search_query.min_score, self.config.rerank_min_score)
        merged = self.merger.merge(
            web_results,
            memory_results,
            doc_results,
            max_results=search_query.max_results,
            min_score=min_score,
        )

        elapsed = (time.perf_counter() - t0) * 1000
        self._metrics.histogram("search_time_ms", elapsed)
        self._metrics.counter("searches", 1)

        # Cache results
        if self.config.enable_cache and self.cache:
            self.cache.set(cache_key, merged)

        return merged

    async def search_web(self, query: str, max_results: Optional[int] = None) -> List[SearchResult]:
        """Search only the web source."""
        if not self.web_searcher:
            raise RuntimeError("SearchEngineService not initialized")
        results = self.web_searcher.search(query, max_results)
        self._metrics.counter("web_searches", 1)
        return results

    async def search_memory(self, query: str, max_results: Optional[int] = None) -> List[SearchResult]:
        """Search only the memory source."""
        if not self.memory_searcher:
            raise RuntimeError("SearchEngineService not initialized")
        results = self.memory_searcher.search(query, max_results)
        self._metrics.counter("memory_searches", 1)
        return results

    async def search_documents(self, query: str, max_results: Optional[int] = None) -> List[SearchResult]:
        """Search only the document source."""
        if not self.document_searcher:
            raise RuntimeError("SearchEngineService not initialized")
        results = self.document_searcher.search(query, max_results)
        self._metrics.counter("document_searches", 1)
        return results

    async def invalidate_cache(self, key: str) -> bool:
        """Invalidate a cached search result."""
        if not self.cache:
            raise RuntimeError("SearchEngineService not initialized")
        return self.cache.invalidate(key)

    async def clear_cache(self) -> int:
        """Clear all cached search results."""
        if not self.cache:
            raise RuntimeError("SearchEngineService not initialized")
        return self.cache.clear()

    async def health(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "service_name": self.name,
            "version": self.version,
            "initialized": self._initialized,
            "uptime_seconds": round(uptime, 1),
        }

    async def stats(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        return {
            "service": self.name,
            "version": self.version,
            "uptime_seconds": round(uptime, 1),
            "cache_size": self.cache.size if self.cache else 0,
            "metrics": self._metrics.snapshot(),
        }

    def _resolve_query(self, query: Any) -> SearchQuery:
        """Resolve a string or SearchQuery to a SearchQuery."""
        if isinstance(query, SearchQuery):
            return query
        if isinstance(query, str):
            return SearchQuery(text=query)
        raise TypeError(f"Expected str or SearchQuery, got {type(query).__name__}")
