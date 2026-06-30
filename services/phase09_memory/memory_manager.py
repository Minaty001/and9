"""
Phase 9 — Memory Manager.

Orchestrates memory lifecycle: storage, retrieval, consolidation,
and forgetting.
"""

from __future__ import annotations

import time
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .config import MemoryConfig
from .models import MemoryItem, MemoryType, MemoryQuery, MemoryStats
from .memory_store import MemoryStore

logger = logging.getLogger(__name__)


class MemoryManager:
    """High-level memory operations with consolidation and lifecycle.

    Usage:
        mgr = MemoryManager()
        mgr.store("user_name", "Alice", memory_type=MemoryType.LONG_TERM, importance=0.9)
        results = mgr.recall("name")
        mgr.consolidate()
    """

    def __init__(self, config: Optional[MemoryConfig] = None):
        self.config = config or MemoryConfig()
        self._store = MemoryStore(self.config)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def store(
        self,
        key: str,
        value: Any,
        memory_type: MemoryType = MemoryType.WORKING,
        importance: Optional[float] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None,
    ) -> MemoryItem:
        """Store a new memory or update an existing one.

        Args:
            key: Unique memory key.
            value: Memory value.
            memory_type: Type of memory (working, long_term, etc.).
            importance: Importance score (0-1). Default from config.
            tags: Tags for categorization.
            metadata: Additional metadata.
            embedding: Optional embedding vector.

        Returns:
            The stored MemoryItem.
        """
        importance = importance if importance is not None else self.config.default_importance

        existing = self._store.get(key)
        if existing:
            # Update existing
            existing.value = value
            existing.memory_type = memory_type
            existing.importance = importance
            existing.tags = tags or existing.tags
            existing.metadata = metadata or existing.metadata
            existing.embedding = embedding if embedding is not None else existing.embedding
            existing.touch()
            # Overwrite in store (touch updates last_accessed)
            self._store._items[key] = existing
            item = existing
            logger.debug("Updated memory: %s (type=%s)", key, memory_type.value)
        else:
            item = MemoryItem(
                key=key,
                value=value,
                memory_type=memory_type,
                importance=importance,
                tags=tags or [],
                metadata=metadata or {},
                embedding=embedding,
            )
            self._store.add(item)

        # Auto-consolidate
        if self.config.auto_consolidate_on_store:
            self.consolidate()

        return item

    def recall(self, query: str, top_k: int = 10) -> List[MemoryItem]:
        """Retrieve memories matching a text query.

        Searches both working and long-term memory.

        Args:
            query: Text query to match against keys, values, and tags.
            top_k: Maximum results.

        Returns:
            List of matching MemoryItem, sorted by relevance.
        """
        mem_query = MemoryQuery(
            text=query,
            limit=top_k,
        )
        results = self._store.search(mem_query)

        # Record access
        for item in results:
            item.touch()

        return results

    def recall_by_type(
        self,
        query: str,
        memory_type: MemoryType,
        top_k: int = 10,
    ) -> List[MemoryItem]:
        """Retrieve memories of a specific type matching a query."""
        mem_query = MemoryQuery(
            text=query,
            memory_type=memory_type,
            limit=top_k,
        )
        results = self._store.search(mem_query)
        for item in results:
            item.touch()
        return results

    def get_memory(self, key: str) -> Optional[MemoryItem]:
        """Get a specific memory by key."""
        return self._store.get(key)

    def forget(self, key: str) -> bool:
        """Delete a specific memory."""
        return self._store.delete(key)

    def consolidate(self) -> int:
        """Promote important working memories to long-term storage.

        Returns:
            Number of memories consolidated.
        """
        threshold = self.config.consolidation_importance_threshold
        working = self._store.list_by_type(MemoryType.WORKING)
        consolidated = 0

        for item in working:
            if item.importance >= threshold:
                item.memory_type = MemoryType.LONG_TERM
                # Overwrite in store
                self._store._items[item.key] = item
                consolidated += 1

        if consolidated:
            logger.info("Consolidated %d working → long-term memories", consolidated)

        return consolidated

    def get_stats(self) -> MemoryStats:
        """Get memory system statistics."""
        return self._store.get_stats()

    def clear(self) -> None:
        """Clear all memories."""
        self._store.clear()

    def list_recent(self, memory_type: Optional[MemoryType] = None, limit: int = 20) -> List[MemoryItem]:
        """List most recently accessed memories."""
        if memory_type:
            return self._store.list_by_type(memory_type, limit=limit)
        all_items = self._store.get_all()
        all_items.sort(key=lambda i: i.last_accessed, reverse=True)
        return all_items[:limit]
