"""
Phase 27 — Knowledge Base Service.

ServiceBase wrapper for the Knowledge Base.
"""

from __future__ import annotations

import time
import logging
from typing import Any, Dict, List, Optional

from services.base.service_base import ServiceBase
from .config import KnowledgeConfig
from .models import KnowledgeEntry, KnowledgeQuery, KnowledgeResult
from .knowledge_store import KnowledgeStore
from .knowledge_base import KnowledgeBase

logger = logging.getLogger(__name__)


class KnowledgeBaseService(ServiceBase):
    """Knowledge base service for structured Q&A and facts.

    Usage:
        svc = KnowledgeBaseService()
        await svc.initialize()
        entry = await svc.add("What is AI?", "Artificial Intelligence...")
        result = await svc.query(KnowledgeQuery(query="What is AI?"))
    """

    def __init__(self, config: Optional[KnowledgeConfig] = None):
        super().__init__(name="jarvis_knowledge", version="1.0.0")
        self.config = config or KnowledgeConfig()
        self.store: Optional[KnowledgeStore] = None
        self.knowledge_base: Optional[KnowledgeBase] = None
        self._start_time = 0.0

    async def initialize(self) -> bool:
        self._start_time = time.time()
        try:
            self.store = KnowledgeStore(self.config)
            self.knowledge_base = KnowledgeBase(self.store, self.config)
            self._metrics.reset()
            self._initialized = True
            logger.info("KnowledgeBaseService initialized")
            return True
        except Exception as e:
            logger.error("KnowledgeBaseService init failed: %s", e)
            return False

    async def shutdown(self) -> None:
        logger.info("KnowledgeBaseService shutting down...")
        self._initialized = False

    async def add(
        self,
        question: str,
        answer: str,
        category: str = "general",
        tags: Optional[List[str]] = None,
        source: str = "manual",
        confidence: float = 1.0,
    ) -> KnowledgeEntry:
        """Add a knowledge entry."""
        if not self.knowledge_base:
            raise RuntimeError("KnowledgeBaseService not initialized")
        t0 = time.perf_counter()
        result = self.knowledge_base.add_knowledge(question, answer, category, tags, source, confidence)
        elapsed = (time.perf_counter() - t0) * 1000
        self._metrics.counter("entries_added", 1)
        self._metrics.histogram("add_time_ms", elapsed)
        return result

    async def add_knowledge(
        self,
        question: str,
        answer: str,
        category: str = "general",
        tags: Optional[List[str]] = None,
        source: str = "manual",
        confidence: float = 1.0,
    ) -> KnowledgeEntry:
        """Add a knowledge entry (alias for add)."""
        return await self.add(question, answer, category, tags, source, confidence)

    async def query(self, query_obj: KnowledgeQuery | str) -> KnowledgeResult:
        """Query the knowledge base.

        Accepts either a KnowledgeQuery object or a plain string query.
        """
        if not self.knowledge_base:
            raise RuntimeError("KnowledgeBaseService not initialized")
        if isinstance(query_obj, str):
            from .models import KnowledgeQuery
            query_obj = KnowledgeQuery(query=query_obj)
        t0 = time.perf_counter()
        result = self.knowledge_base.query(query_obj)
        elapsed = (time.perf_counter() - t0) * 1000
        self._metrics.counter("queries", 1)
        self._metrics.histogram("query_time_ms", elapsed)
        return result

    async def update(self, entry_id: str, **updates) -> Optional[KnowledgeEntry]:
        """Update a knowledge entry."""
        if not self.store:
            raise RuntimeError("KnowledgeBaseService not initialized")
        return self.store.update(entry_id, **updates)

    async def delete(self, entry_id: str) -> bool:
        """Delete a knowledge entry."""
        if not self.store:
            raise RuntimeError("KnowledgeBaseService not initialized")
        return self.store.delete(entry_id)

    async def get_entry(self, entry_id: str) -> Optional[KnowledgeEntry]:
        """Get a single entry by ID."""
        if not self.store:
            raise RuntimeError("KnowledgeBaseService not initialized")
        return self.store.get(entry_id)

    async def find_related(self, entry_id: str) -> List[KnowledgeEntry]:
        """Find related entries."""
        if not self.knowledge_base:
            raise RuntimeError("KnowledgeBaseService not initialized")
        return self.knowledge_base.find_related(entry_id)

    async def import_data(self, data: List[Dict[str, Any]]) -> int:
        """Import entries from dict."""
        if not self.knowledge_base:
            raise RuntimeError("KnowledgeBaseService not initialized")
        count = self.knowledge_base.import_from_dict(data)
        self._metrics.counter("entries_imported", count)
        return count

    async def export_data(self) -> List[Dict[str, Any]]:
        """Export all entries to dict."""
        if not self.knowledge_base:
            raise RuntimeError("KnowledgeBaseService not initialized")
        return self.knowledge_base.export_to_dict()

    async def get_by_tag(self, tag: str) -> List[KnowledgeEntry]:
        """Get entries by tag."""
        if not self.store:
            raise RuntimeError("KnowledgeBaseService not initialized")
        return self.store.get_by_tag(tag)

    async def get_by_category(self, category: str) -> List[KnowledgeEntry]:
        """Get entries by category."""
        if not self.store:
            raise RuntimeError("KnowledgeBaseService not initialized")
        return self.store.get_by_category(category)

    async def health(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        entry_count = self.store.count() if self.store else 0
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "service_name": self.name,
            "version": self.version,
            "initialized": self._initialized,
            "uptime_seconds": round(uptime, 1),
            "total_entries": entry_count,
        }

    async def stats(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        kb_stats = self.knowledge_base.get_stats() if self.knowledge_base else {}
        return {
            "service": self.name,
            "version": self.version,
            "uptime_seconds": round(uptime, 1),
            **kb_stats,
            "metrics": self._metrics.snapshot(),
        }
