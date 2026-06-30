"""
Phase 27 — Knowledge Store.

In-memory storage for knowledge entries with search, tag, and
category filtering.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from .config import KnowledgeConfig
from .models import KnowledgeEntry

logger = logging.getLogger(__name__)


class KnowledgeStore:
    """In-memory store for knowledge entries.

    Usage:
        store = KnowledgeStore()
        entry = store.add(KnowledgeEntry(id="1", question="...", answer="..."))
        results = store.search("hello")
    """

    def __init__(self, config: Optional[KnowledgeConfig] = None):
        self.config = config or KnowledgeConfig()
        self._entries: Dict[str, KnowledgeEntry] = {}
        self._tag_index: Dict[str, List[str]] = {}
        self._category_index: Dict[str, List[str]] = {}

    def add(self, entry: KnowledgeEntry) -> KnowledgeEntry:
        """Add a knowledge entry to the store.

        Args:
            entry: KnowledgeEntry to add.

        Returns:
            The added entry.
        """
        if len(self._entries) >= self.config.max_entries:
            # Evict least-accessed entry
            oldest = min(self._entries.values(), key=lambda e: e.access_count)
            self.delete(oldest.id)

        self._entries[entry.id] = entry
        self._index_entry(entry)
        return entry

    def get(self, entry_id: str) -> Optional[KnowledgeEntry]:
        """Get an entry by ID and increment access count."""
        entry = self._entries.get(entry_id)
        if entry:
            entry.access_count += 1
        return entry

    def update(self, entry_id: str, **updates) -> Optional[KnowledgeEntry]:
        """Update fields on an existing entry.

        Args:
            entry_id: Entry identifier.
            **updates: Fields to update.

        Returns:
            Updated entry or None if not found.
        """
        entry = self._entries.get(entry_id)
        if not entry:
            return None

        # Remove old index entries if tags or category changed
        if "tags" in updates:
            self._deindex_entry(entry)
        if "category" in updates:
            self._deindex_entry(entry)

        for key, value in updates.items():
            if hasattr(entry, key):
                setattr(entry, key, value)

        entry.updated_at = datetime.now(timezone.utc)
        self._index_entry(entry)
        return entry

    def delete(self, entry_id: str) -> bool:
        """Delete an entry by ID."""
        entry = self._entries.get(entry_id)
        if not entry:
            return False
        self._deindex_entry(entry)
        del self._entries[entry_id]
        return True

    def search(self, query: str, min_confidence: float = 0.0, max_results: int = 10) -> List[KnowledgeEntry]:
        """Search entries by query text (simple substring/word matching).

        Args:
            query: Search text.
            min_confidence: Minimum confidence filter.
            max_results: Max results to return.

        Returns:
            List of matching KnowledgeEntry, sorted by relevance.
        """
        query_lower = query.lower()
        query_words = query_lower.split()

        scored = []
        for entry in self._entries.values():
            if entry.confidence < min_confidence:
                continue

            score = 0.0
            entry_text = (entry.question + " " + entry.answer).lower()

            # Full query match
            if query_lower in entry_text:
                score += 10.0

            # Word matches
            word_matches = sum(1 for w in query_words if w in entry_text)
            if word_matches > 0:
                score += word_matches * 2.0

            # Tag matches
            tag_matches = sum(1 for t in entry.tags if t.lower() in query_lower)
            if tag_matches > 0:
                score += tag_matches * 3.0

            if score > 0:
                scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored[:max_results]]

    def get_by_tag(self, tag: str) -> List[KnowledgeEntry]:
        """Get entries by tag."""
        entry_ids = self._tag_index.get(tag, [])
        return [self._entries[eid] for eid in entry_ids if eid in self._entries]

    def get_by_category(self, category: str) -> List[KnowledgeEntry]:
        """Get entries by category."""
        entry_ids = self._category_index.get(category, [])
        return [self._entries[eid] for eid in entry_ids if eid in self._entries]

    def list_all(self) -> List[KnowledgeEntry]:
        """List all entries."""
        return list(self._entries.values())

    def count(self) -> int:
        """Return total entry count."""
        return len(self._entries)

    def clear(self) -> None:
        """Clear all entries and indices."""
        self._entries.clear()
        self._tag_index.clear()
        self._category_index.clear()

    # ── Indexing ──────────────────────────────────────────────────

    def _index_entry(self, entry: KnowledgeEntry) -> None:
        """Index entry by tags and category."""
        for tag in entry.tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = []
            if entry.id not in self._tag_index[tag]:
                self._tag_index[tag].append(entry.id)

        cat = entry.category
        if cat not in self._category_index:
            self._category_index[cat] = []
        if entry.id not in self._category_index[cat]:
            self._category_index[cat].append(entry.id)

    def _deindex_entry(self, entry: KnowledgeEntry) -> None:
        """Remove entry from indices."""
        for tag in entry.tags:
            if tag in self._tag_index:
                self._tag_index[tag] = [eid for eid in self._tag_index[tag] if eid != entry.id]
                if not self._tag_index[tag]:
                    del self._tag_index[tag]

        cat = entry.category
        if cat in self._category_index:
            self._category_index[cat] = [eid for eid in self._category_index[cat] if eid != entry.id]
            if not self._category_index[cat]:
                del self._category_index[cat]
