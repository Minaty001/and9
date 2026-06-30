"""
Phase 9 — Memory Service.

ServiceBase wrapper around MemoryManager.
"""

from __future__ import annotations

import time
import logging
from typing import Any, Dict, List, Optional

from services.base.service_base import ServiceBase
from .config import MemoryConfig
from .models import MemoryItem, MemoryType, MemoryStats
from .memory_manager import MemoryManager

logger = logging.getLogger(__name__)


class MemoryService(ServiceBase):
    """Memory service for long-term and working memory.

    Usage:
        svc = MemoryService()
        await svc.initialize()
        await svc.store("user_name", "Alice", memory_type="long_term", importance=0.9)
        results = await svc.recall("Alice")
        stats = await svc.get_stats()
    """

    def __init__(self, config: Optional[MemoryConfig] = None):
        super().__init__(name="jarvis_memory", version="1.0.0")
        self.config = config or MemoryConfig()
        self.manager: Optional[MemoryManager] = None
        self._start_time = 0.0

    async def initialize(self) -> bool:
        """Initialize the memory service."""
        self._start_time = time.time()
        try:
            self.manager = MemoryManager(self.config)
            self._metrics.reset()
            self._initialized = True
            elapsed = (time.time() - self._start_time) * 1000
            logger.info("MemoryService initialized in %.0fms", elapsed)
            return True
        except Exception as e:
            logger.error("MemoryService init failed: %s", e)
            return False

    async def shutdown(self) -> None:
        """Shut down the service."""
        logger.info("MemoryService shutting down...")
        if self.manager:
            self.manager.clear()
        self._initialized = False

    async def store(
        self,
        key: str,
        value: Any,
        memory_type: str = "working",
        importance: Optional[float] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MemoryItem:
        """Store a memory.

        Args:
            key: Unique identifier for the memory.
            value: The value to store.
            memory_type: "working", "long_term", "episodic", or "semantic".
            importance: Importance 0-1 (defaults to config default).
            tags: Optional tags.
            metadata: Optional metadata dict.

        Returns:
            The stored MemoryItem.
        """
        if not self.manager:
            raise RuntimeError("MemoryService not initialized")

        t0 = time.perf_counter()
        mtype = MemoryType(memory_type)
        item = self.manager.store(
            key=key,
            value=value,
            memory_type=mtype,
            importance=importance,
            tags=tags,
            metadata=metadata,
        )
        elapsed = (time.perf_counter() - t0) * 1000
        self._metrics.counter("memories_stored", 1)
        self._metrics.histogram("store_time_ms", elapsed)
        return item

    async def recall(self, query: str, top_k: int = 10) -> List[MemoryItem]:
        """Recall memories matching a text query.

        Args:
            query: Text to match against memory keys/values/tags.
            top_k: Maximum results.

        Returns:
            List of matching MemoryItem.
        """
        if not self.manager:
            raise RuntimeError("MemoryService not initialized")

        t0 = time.perf_counter()
        results = self.manager.recall(query, top_k=top_k)
        elapsed = (time.perf_counter() - t0) * 1000
        self._metrics.histogram("recall_time_ms", elapsed)
        self._metrics.counter("memory_recalls", 1)
        return results

    async def get_memory(self, key: str) -> Optional[MemoryItem]:
        """Get a specific memory by key."""
        if not self.manager:
            raise RuntimeError("MemoryService not initialized")
        return self.manager.get_memory(key)

    async def forget(self, key: str) -> bool:
        """Delete a specific memory."""
        if not self.manager:
            raise RuntimeError("MemoryService not initialized")
        result = self.manager.forget(key)
        if result:
            self._metrics.counter("memories_deleted", 1)
        return result

    async def consolidate(self) -> int:
        """Promote important working memories to long-term.

        Returns:
            Number of consolidated memories.
        """
        if not self.manager:
            raise RuntimeError("MemoryService not initialized")
        count = self.manager.consolidate()
        if count:
            self._metrics.counter("consolidations", count)
        return count

    async def get_stats(self) -> MemoryStats:
        """Get memory usage statistics."""
        if not self.manager:
            raise RuntimeError("MemoryService not initialized")
        return self.manager.get_stats()

    async def clear(self) -> None:
        """Clear all memories."""
        if self.manager:
            self.manager.clear()
        logger.info("All memories cleared by user request")

    async def health(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        stats = self.manager.get_stats() if self.manager else MemoryStats()
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "service_name": self.name,
            "version": self.version,
            "initialized": self._initialized,
            "uptime_seconds": round(uptime, 1),
            "total_memories": stats.total_items,
            "working_memories": stats.working_count,
            "long_term_memories": stats.long_term_count,
        }

    async def stats(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        mem_stats = self.manager.get_stats() if self.manager else MemoryStats()
        return {
            "service": self.name,
            "version": self.version,
            "uptime_seconds": round(uptime, 1),
            "memory": mem_stats.model_dump(),
            "metrics": self._metrics.snapshot(),
        }
