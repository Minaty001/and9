"""
Phase 27 — Knowledge Base.

Query/retrieve logic with import/export, confidence scoring,
and entry linking.
"""

from __future__ import annotations

import time
import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .config import KnowledgeConfig
from .models import KnowledgeEntry, KnowledgeQuery, KnowledgeResult
from .knowledge_store import KnowledgeStore

logger = logging.getLogger(__name__)


class KnowledgeBase:
    """High-level knowledge base with query, import/export, and linking.

    Usage:
        kb = KnowledgeBase(store)
        entry = kb.add_knowledge("What is AI?", "Artificial Intelligence...", "tech")
        result = kb.query(KnowledgeQuery(query="What is AI?"))
    """

    def __init__(self, store: KnowledgeStore, config: Optional[KnowledgeConfig] = None):
        self.store = store
        self.config = config or KnowledgeConfig()

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
        if self.config.enable_auto_linking:
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
