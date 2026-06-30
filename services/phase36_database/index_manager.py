"""
Phase 36 — Index Manager.

Manage indexes on collections for faster query performance.
"""

from __future__ import annotations

import time
import logging
from typing import Any, Dict, List, Optional, Set
from collections import defaultdict

from .config import DatabaseConfig

logger = logging.getLogger(__name__)


class IndexManager:
    """Manage indexes on collections.

    Usage:
        mgr = IndexManager(store)
        mgr.create_index("users", "age")
        mgr.list_indexes("users")
    """

    def __init__(self, config: Optional[DatabaseConfig] = None):
        self.config = config or DatabaseConfig()
        self._indexes: Dict[str, Dict[str, Dict[Any, List[str]]]] = defaultdict(dict)
        # collection -> {field -> {value -> [doc_id, ...]}}

    def create_index(self, collection: str, field: str, documents: Optional[Dict[str, dict]] = None) -> bool:
        """Create an index on a field for a collection.

        Args:
            collection: Collection name.
            field: Field name to index.
            documents: Current documents to index (collection id->doc map).

        Returns:
            True if created.
        """
        if not self.config.enable_indexing:
            return False
        if collection in self._indexes and field in self._indexes[collection]:
            return False  # already exists

        index_map: Dict[Any, List[str]] = defaultdict(list)
        if documents:
            for doc_id, doc in documents.items():
                val = doc.get(field)
                if val is not None:
                    index_map[val].append(doc_id)

        self._indexes[collection][field] = dict(index_map)
        logger.debug("Created index on %s.%s (%d entries)", collection, field, len(index_map))
        return True

    def drop_index(self, collection: str, field: str) -> bool:
        """Drop an index on a field."""
        if collection in self._indexes and field in self._indexes[collection]:
            del self._indexes[collection][field]
            return True
        return False

    def list_indexes(self, collection: str) -> List[Dict[str, Any]]:
        """List all indexes for a collection."""
        col_indexes = self._indexes.get(collection, {})
        return [
            {
                "field": field,
                "unique_entries": len(values),
                "total_document_ids": sum(len(v) for v in values.values()),
            }
            for field, values in col_indexes.items()
        ]

    def optimize(self, collection: str) -> Dict[str, Any]:
        """Optimize indexes for a collection (rebuild, compact)."""
        t0 = time.time()
        col_indexes = self._indexes.get(collection, {})
        if not col_indexes:
            return {"collection": collection, "indexes_optimized": 0, "time_ms": 0}

        optimized = 0
        for field in list(col_indexes.keys()):
            # Compact by removing empty value lists
            old = col_indexes[field]
            compacted = {k: v for k, v in old.items() if v}
            if len(compacted) < len(old):
                col_indexes[field] = compacted
                optimized += 1

        elapsed = (time.time() - t0) * 1000
        return {
            "collection": collection,
            "indexes_optimized": optimized,
            "total_indexes": len(col_indexes),
            "time_ms": round(elapsed, 2),
        }

    def lookup(self, collection: str, field: str, value: Any) -> Optional[List[str]]:
        """Look up document IDs by indexed field value.

        Returns list of doc IDs or None if not indexed.
        """
        col_indexes = self._indexes.get(collection)
        if col_indexes is None:
            return None
        field_index = col_indexes.get(field)
        if field_index is None:
            return None
        return field_index.get(value)

    def add_document(self, collection: str, doc_id: str, doc: Dict[str, Any]) -> None:
        """Add a document to relevant indexes."""
        col_indexes = self._indexes.get(collection)
        if col_indexes is None:
            return
        for field, index_map in col_indexes.items():
            val = doc.get(field)
            if val is not None:
                if val not in index_map:
                    index_map[val] = []
                if doc_id not in index_map[val]:
                    index_map[val].append(doc_id)

    def remove_document(self, collection: str, doc_id: str, doc: Dict[str, Any]) -> None:
        """Remove a document from relevant indexes."""
        col_indexes = self._indexes.get(collection)
        if col_indexes is None:
            return
        for field, index_map in col_indexes.items():
            val = doc.get(field)
            if val is not None and val in index_map:
                if doc_id in index_map[val]:
                    index_map[val].remove(doc_id)
