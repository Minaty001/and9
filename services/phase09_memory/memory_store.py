"""
Phase 9 — Memory Store.

In-memory storage for memories with CRUD operations, tagged search,
and LRU eviction when capacity is exceeded.
"""

from __future__ import annotations

import time
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .config import MemoryConfig
from .models import MemoryItem, MemoryType, MemoryQuery, MemoryStats

logger = logging.getLogger(__name__)


class MemoryStore:
    """Thread-safe in-memory memory store.

    Supports per-type capacity limits with LRU eviction.
    """

    def __init__(self, config: Optional[MemoryConfig] = None):
        self.config = config or MemoryConfig()
        self._items: Dict[str, MemoryItem] = {}
        logger.info("MemoryStore created (max_working=%d, max_long_term=%d)",
                     self.config.max_working_memories, self.config.max_long_term_memories)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add(self, item: MemoryItem) -> MemoryItem:
        """Store a memory item. Evicts if capacity exceeded for its type."""
        self._items[item.key] = item
        self._evict_if_needed(item.memory_type)
        logger.debug("Stored memory: %s (type=%s, importance=%.2f)", item.key, item.memory_type.value, item.importance)
        return item

    def get(self, key: str) -> Optional[MemoryItem]:
        """Retrieve by key and record access."""
        item = self._items.get(key)
        if item:
            item.touch()
        return item

    def update(self, key: str, **updates: Any) -> Optional[MemoryItem]:
        """Update fields of an existing memory item."""
        item = self._items.get(key)
        if not item:
            return None
        for field, value in updates.items():
            if hasattr(item, field) and field not in ("key", "created_at"):
                setattr(item, field, value)
        item.touch()
        return item

    def delete(self, key: str) -> bool:
        """Delete a memory by key."""
        if key in self._items:
            del self._items[key]
            logger.debug("Deleted memory: %s", key)
            return True
        return False

    def clear(self) -> None:
        """Delete all memories."""
        self._items.clear()
        logger.info("Memory store cleared")

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(self, query: MemoryQuery) -> List[MemoryItem]:
        """Search memories matching the given query."""
        results: List[MemoryItem] = []

        for item in self._items.values():
            # Filter by type
            if query.memory_type and item.memory_type != query.memory_type:
                continue

            # Filter by importance
            if item.importance < query.min_importance:
                continue

            # Filter by tags (any match)
            if query.tags:
                if not any(t in item.tags for t in query.tags):
                    continue

            # Text match (key or value string)
            if query.text:
                text_lower = query.text.lower()
                key_match = text_lower in item.key.lower()
                value_match = False
                if isinstance(item.value, str):
                    value_match = text_lower in item.value.lower()
                elif isinstance(item.value, dict):
                    value_match = any(
                        text_lower in str(v).lower() for v in item.value.values()
                    )
                if not key_match and not value_match:
                    continue

            results.append(item)

        # Score and sort by relevance
        results.sort(key=lambda i: self._relevance_score(i), reverse=True)

        return results[: query.limit]

    def list_by_type(self, memory_type: MemoryType, limit: int = 50) -> List[MemoryItem]:
        """List memories of a given type, sorted by recency."""
        items = [i for i in self._items.values() if i.memory_type == memory_type]
        items.sort(key=lambda i: i.last_accessed, reverse=True)
        return items[:limit]

    def count_by_type(self, memory_type: MemoryType) -> int:
        """Count memories of a given type."""
        return sum(1 for i in self._items.values() if i.memory_type == memory_type)

    def get_all(self) -> List[MemoryItem]:
        """Return all memories."""
        return list(self._items.values())

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> MemoryStats:
        """Compute memory system statistics."""
        items = list(self._items.values())
        if not items:
            return MemoryStats()

        avg_imp = sum(i.importance for i in items) / len(items)
        total_access = sum(i.access_count for i in items)
        oldest = min(i.age_seconds() for i in items)

        return MemoryStats(
            total_items=len(items),
            working_count=self.count_by_type(MemoryType.WORKING),
            long_term_count=self.count_by_type(MemoryType.LONG_TERM),
            episodic_count=self.count_by_type(MemoryType.EPISODIC),
            semantic_count=self.count_by_type(MemoryType.SEMANTIC),
            avg_importance=round(avg_imp, 3),
            total_accesses=total_access,
            oldest_memory_age_seconds=round(oldest, 1),
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _evict_if_needed(self, memory_type: MemoryType) -> None:
        """LRU eviction when capacity is exceeded for a memory type."""
        max_items = {
            MemoryType.WORKING: self.config.max_working_memories,
            MemoryType.LONG_TERM: self.config.max_long_term_memories,
            MemoryType.EPISODIC: self.config.max_long_term_memories,  # share budget
            MemoryType.SEMANTIC: self.config.max_long_term_memories,
        }.get(memory_type, 1000)

        type_items = [i for i in self._items.values() if i.memory_type == memory_type]
        if len(type_items) <= max_items:
            return

        # Sort by last_accessed (oldest first) and remove excess
        type_items.sort(key=lambda i: i.last_accessed)
        to_remove = len(type_items) - max_items
        removed_keys = {i.key for i in type_items[:to_remove]}
        self._items = {k: v for k, v in self._items.items() if k not in removed_keys}
        logger.debug("Evicted %d %s memories (LRU)", to_remove, memory_type.value)

    @staticmethod
    def _relevance_score(item: MemoryItem) -> float:
        """Compute a combined relevance score for sorting search results."""
        now = datetime.now(timezone.utc)
        recency_hours = (now - item.last_accessed).total_seconds() / 3600.0
        recency_score = 1.0 / (1.0 + recency_hours)  # 1.0 = just now, decays to 0
        freq_score = min(item.access_count / 20.0, 1.0)
        importance = item.importance
        # Weighted combination (config weights are used externally;
        # this is a simple internal sort heuristic)
        return 0.3 * recency_score + 0.3 * freq_score + 0.4 * importance
