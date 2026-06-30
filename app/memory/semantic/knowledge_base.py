"""
app/memory/semantic/knowledge_base.py — Knowledge Base.

Structured Q&A, facts, user info, domain knowledge with fast retrieval,
tagging, confidence scoring, and import/export.

Components:
    - KnowledgeEntry: A single knowledge entry (Q&A pair)
    - KnowledgeStore: In-memory storage for knowledge entries
    - KnowledgeBase: Query/retrieve logic with import/export and linking
"""

from __future__ import annotations

import uuid
import time
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# MODELS
# ═══════════════════════════════════════════════════════════════


@dataclass
class KnowledgeEntry:
    """A single knowledge entry (structured Q&A)."""

    id: str
    question: str
    answer: str
    category: str = "general"
    tags: List[str] = field(default_factory=list)
    confidence: float = 1.0
    source: str = "manual"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    access_count: int = 0
    linked_entries: List[str] = field(default_factory=list)


@dataclass
class KnowledgeQuery:
    """A query against the knowledge base."""

    query: str
    category: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    min_confidence: float = 0.3
    max_results: int = 10


@dataclass
class KnowledgeResult:
    """Result of a knowledge query."""

    entries: List[KnowledgeEntry] = field(default_factory=list)
    query: str = ""
    total_found: int = 0
    search_time_ms: float = 0.0
    confidence_scores: Dict[str, float] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════
# KNOWLEDGE STORE
# ═══════════════════════════════════════════════════════════════


class KnowledgeStore:
    """In-memory store for knowledge entries with search, tag, and
    category filtering.

    Usage:
        store = KnowledgeStore()
        entry = store.add(KnowledgeEntry(id="1", question="...", answer="..."))
        results = store.search("hello")
    """

    def __init__(self, max_entries: int = 1000):
        self._max_entries = max_entries
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
        if len(self._entries) >= self._max_entries:
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
        if "tags" in updates or "category" in updates:
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


# ═══════════════════════════════════════════════════════════════
# KNOWLEDGE BASE
# ═══════════════════════════════════════════════════════════════


class KnowledgeBase:
    """High-level knowledge base with query, import/export, and linking.

    Usage:
        kb = KnowledgeBase(store)
        entry = kb.add_knowledge("What is AI?", "Artificial Intelligence...", "tech")
        result = kb.query(KnowledgeQuery(query="What is AI?"))
    """

    def __init__(self, store: KnowledgeStore, enable_auto_linking: bool = True):
        self.store = store
        self._enable_auto_linking = enable_auto_linking

    def add_knowledge(
        self,
        question: str,
        answer: str,
        category: str = "general",
        tags: Optional[List[str]] = None,
        source: str = "manual",
        confidence: float = 1.0,
    ) -> KnowledgeEntry:
        """Add a knowledge entry.

        Args:
            question: Question or trigger phrase.
            answer: Answer or response.
            category: Knowledge category.
            tags: Tags for organization.
            source: Source of knowledge.
            confidence: Confidence score (0-1).

        Returns:
            The created KnowledgeEntry.
        """
        entry = KnowledgeEntry(
            id=uuid.uuid4().hex[:12],
            question=question,
            answer=answer,
            category=category,
            tags=tags or [],
            source=source,
            confidence=confidence,
        )

        # Auto-linking
        if self._enable_auto_linking:
            self._auto_link(entry)

        self.store.add(entry)
        return entry

    def query(self, query_obj: KnowledgeQuery) -> KnowledgeResult:
        """Execute a query against the knowledge base.

        Args:
            query_obj: KnowledgeQuery with search parameters.

        Returns:
            KnowledgeResult with matching entries.
        """
        t0 = time.perf_counter()
        results = self.store.search(
            query=query_obj.query,
            min_confidence=query_obj.min_confidence,
            max_results=query_obj.max_results,
        )

        # Apply category filter
        if query_obj.category:
            results = [e for e in results if e.category == query_obj.category]

        # Apply tag filter
        if query_obj.tags:
            results = [e for e in results if any(t in e.tags for t in query_obj.tags)]

        elapsed = (time.perf_counter() - t0) * 1000

        conf_scores = {e.id: e.confidence for e in results}

        return KnowledgeResult(
            entries=results,
            query=query_obj.query,
            total_found=len(results),
            search_time_ms=round(elapsed, 2),
            confidence_scores=conf_scores,
        )

    def find_related(self, entry_id: str) -> List[KnowledgeEntry]:
        """Find entries related to the given entry.

        Args:
            entry_id: Entry ID to find related entries for.

        Returns:
            List of related KnowledgeEntry.
        """
        entry = self.store.get(entry_id)
        if not entry:
            return []

        related_ids = set(entry.linked_entries)
        related = []
        for rid in related_ids:
            rel = self.store.get(rid)
            if rel:
                related.append(rel)

        # Also find by shared tags
        if not related:
            for tag in entry.tags:
                tagged = self.store.get_by_tag(tag)
                for e in tagged:
                    if e.id != entry_id and e not in related:
                        related.append(e)

        return related[:5]

    def import_from_dict(self, data: List[Dict[str, Any]]) -> int:
        """Import entries from a dictionary.

        Args:
            data: List of dicts with keys matching KnowledgeEntry fields.

        Returns:
            Number of entries imported.
        """
        count = 0
        for item in data:
            try:
                entry = KnowledgeEntry(
                    id=item.get("id", uuid.uuid4().hex[:12]),
                    question=item["question"],
                    answer=item["answer"],
                    category=item.get("category", "general"),
                    tags=item.get("tags", []),
                    confidence=item.get("confidence", 1.0),
                    source=item.get("source", "import"),
                )
                self.store.add(entry)
                count += 1
            except (KeyError, ValueError) as e:
                logger.warning("Skipped invalid entry: %s", e)
        return count

    def export_to_dict(self) -> List[Dict[str, Any]]:
        """Export all entries to a list of dicts.

        Returns:
            List of serializable dicts.
        """
        return [
            {
                "id": e.id,
                "question": e.question,
                "answer": e.answer,
                "category": e.category,
                "tags": e.tags,
                "confidence": e.confidence,
                "source": e.source,
                "created_at": e.created_at.isoformat(),
                "updated_at": e.updated_at.isoformat(),
                "access_count": e.access_count,
                "linked_entries": e.linked_entries,
            }
            for e in self.store.list_all()
        ]

    def bulk_add(self, entries: List[KnowledgeEntry]) -> int:
        """Add multiple entries at once.

        Args:
            entries: List of KnowledgeEntry.

        Returns:
            Number of entries added.
        """
        count = 0
        for entry in entries:
            try:
                self.store.add(entry)
                count += 1
            except Exception as e:
                logger.warning("Failed to add entry %s: %s", entry.id, e)
        return count

    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics."""
        entries = self.store.list_all()
        if not entries:
            return {"total_entries": 0, "categories": {}, "avg_confidence": 0.0, "total_accesses": 0}

        categories = {}
        for e in entries:
            categories[e.category] = categories.get(e.category, 0) + 1

        return {
            "total_entries": len(entries),
            "categories": categories,
            "avg_confidence": round(sum(e.confidence for e in entries) / len(entries), 3),
            "total_accesses": sum(e.access_count for e in entries),
        }

    def _auto_link(self, entry: KnowledgeEntry) -> None:
        """Automatically link entry to related existing entries."""
        for existing in self.store.list_all():
            if existing.id == entry.id:
                continue
            # Link if they share tags
            shared_tags = set(entry.tags) & set(existing.tags)
            if shared_tags and len(shared_tags) >= 2:
                if entry.id not in existing.linked_entries:
                    existing.linked_entries.append(entry.id)
                if existing.id not in entry.linked_entries:
                    entry.linked_entries.append(existing.id)
