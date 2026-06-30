"""
Phase 36 — Document Store.

In-memory document storage with CRUD, indexing, query filtering.
"""

from __future__ import annotations

import uuid
import time
import re
import logging
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Callable

from .config import DatabaseConfig
from .models import SchemaField, CollectionSchema, QueryFilter, QueryResult

logger = logging.getLogger(__name__)


class DocumentStore:
    """In-memory document store with schema validation and query filtering.

    Usage:
        store = DocumentStore()
        store.create_collection(CollectionSchema(name="users", fields={...}))
        doc_id = store.insert("users", {"name": "Alice", "age": 30})
        results = store.find("users", [QueryFilter(field="age", operator="gt", value=25)])
    """

    def __init__(self, config: Optional[DatabaseConfig] = None):
        self.config = config or DatabaseConfig()
        self._collections: Dict[str, Dict[str, Any]] = {}  # name -> list of docs by id
        self._schemas: Dict[str, CollectionSchema] = {}
        self._id_map: Dict[str, List[str]] = {}  # collection -> ordered list of doc ids

    # ── Collection Management ─────────────────────────────────────

    def create_collection(self, schema: CollectionSchema) -> bool:
        """Create a new collection from a schema.

        Returns True if created, False if it already exists or limit reached.
        """
        if schema.name in self._collections:
            return False
        if len(self._collections) >= self.config.max_collections:
            logger.warning("Max collections (%d) reached", self.config.max_collections)
            return False
        self._collections[schema.name] = {}
        self._schemas[schema.name] = schema
        self._id_map[schema.name] = []
        return True

    def list_collections(self) -> List[Dict[str, Any]]:
        """List all collections with basic info."""
        result = []
        for name, schema in self._schemas.items():
            result.append({
                "name": name,
                "document_count": len(self._collections.get(name, {})),
                "field_count": len(schema.fields),
                "strict": schema.strict,
            })
        return result

    # ── CRUD Operations ────────────────────────────────────────────

    def insert(self, collection: str, doc: Dict[str, Any]) -> Optional[str]:
        """Insert a document into a collection.

        Args:
            collection: Collection name.
            doc: Document data.

        Returns:
            Document ID string, or None if failed.
        """
        if collection not in self._collections:
            logger.error("Collection '%s' not found", collection)
            return None

        schema = self._schemas[collection]

        if self.config.enable_schema_validation:
            validated = self._validate_and_default(schema, doc)
            if validated is None:
                return None
            doc = validated

        # Check max documents
        if len(self._collections[collection]) >= self.config.max_documents_per_collection:
            logger.warning("Collection '%s' at max capacity", collection)
            return None

        doc_id = uuid.uuid4().hex[:12]
        now = datetime.now(timezone.utc)
        stored = dict(doc)
        stored["_id"] = doc_id
        if schema.timestamps:
            stored["created_at"] = now.isoformat()
            stored["updated_at"] = now.isoformat()

        self._collections[collection][doc_id] = stored
        self._id_map[collection].append(doc_id)
        return doc_id

    def find(self, collection: str, filters: Optional[List[QueryFilter]] = None,
             page: int = 1, page_size: int = 20) -> QueryResult:
        """Find documents matching filters."""
        t0 = time.perf_counter()
        if collection not in self._collections:
            return QueryResult(total_found=0, query_time_ms=0, page=page, page_size=page_size)

        docs = list(self._collections[collection].values())
        if filters:
            docs = [d for d in docs if self._matches_filters(d, filters)]

        total = len(docs)
        start = (page - 1) * page_size
        end = start + page_size
        page_docs = docs[start:end] if start < total else []
        elapsed = (time.perf_counter() - t0) * 1000

        return QueryResult(
            documents=[deepcopy(d) for d in page_docs],
            total_found=total,
            query_time_ms=round(elapsed, 3),
            page=page,
            page_size=page_size,
            has_more=end < total,
        )

    def find_one(self, collection: str, filters: Optional[List[QueryFilter]] = None) -> Optional[Dict[str, Any]]:
        """Find the first document matching filters."""
        result = self.find(collection, filters, page=1, page_size=1)
        return result.documents[0] if result.documents else None

    def update(self, collection: str, id: str, updates: Dict[str, Any]) -> bool:
        """Update a document by ID.

        Returns True if updated.
        """
        if collection not in self._collections:
            return False
        doc = self._collections[collection].get(id)
        if doc is None:
            return False

        schema = self._schemas[collection]
        # Don't allow updating _id
        updates = {k: v for k, v in updates.items() if k != "_id"}

        if self.config.enable_schema_validation:
            # Validate updated fields against schema
            for key, value in updates.items():
                if key in schema.fields:
                    sf = schema.fields[key]
                    if sf.field_type == "int" and not isinstance(value, int):
                        try:
                            updates[key] = int(value)
                        except (ValueError, TypeError):
                            logger.error("Field '%s' expects int, got %s", key, type(value).__name__)
                            return False
                    elif sf.field_type == "float" and not isinstance(value, (int, float)):
                        try:
                            updates[key] = float(value)
                        except (ValueError, TypeError):
                            return False
                    elif sf.field_type == "bool" and not isinstance(value, bool):
                        return False

        doc.update(updates)
        if schema.timestamps:
            doc["updated_at"] = datetime.now(timezone.utc).isoformat()
        return True

    def delete(self, collection: str, id: str) -> bool:
        """Delete a document by ID.

        Returns True if deleted.
        """
        if collection not in self._collections:
            return False
        if id in self._collections[collection]:
            del self._collections[collection][id]
            if id in self._id_map[collection]:
                self._id_map[collection].remove(id)
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        total_docs = 0
        total_size = 0
        collection_stats = {}
        for name, docs in self._collections.items():
            count = len(docs)
            total_docs += count
            size = sum(len(str(d)) for d in docs.values())
            total_size += size
            collection_stats[name] = {
                "document_count": count,
                "estimated_size_bytes": size,
            }
        return {
            "collections": len(self._collections),
            "total_documents": total_docs,
            "total_estimated_size_bytes": total_size,
            "collection_details": collection_stats,
        }

    # ── Internal ───────────────────────────────────────────────────

    def _validate_and_default(self, schema: CollectionSchema, doc: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate a document against schema, filling defaults.

        Returns the validated doc or None if validation fails.
        """
        result = {}
        for fname, sfield in schema.fields.items():
            if fname in doc:
                val = doc[fname]
                if not self._validate_type(val, sfield.field_type):
                    logger.error("Field '%s': expected %s, got %s", fname, sfield.field_type, type(val).__name__)
                    if schema.strict:
                        return None
                result[fname] = val
            elif sfield.required:
                logger.error("Required field '%s' missing", fname)
                if schema.strict:
                    return None
            elif sfield.default_value is not None:
                result[fname] = sfield.default_value

        if schema.strict:
            # Reject unknown fields
            for key in doc:
                if key not in schema.fields and not key.startswith("_"):
                    logger.warning("Unknown field '%s' in strict schema", key)
                    return None

        # Add extra fields not in schema (if not strict)
        for key, val in doc.items():
            if key not in result and not key.startswith("_"):
                result[key] = val

        return result

    def _validate_type(self, value: Any, expected_type: str) -> bool:
        """Check if a value matches an expected type string."""
        type_map = {
            "str": str,
            "int": int,
            "float": (int, float),
            "bool": bool,
            "dict": dict,
            "list": list,
            "datetime": (str, datetime),
        }
        py_type = type_map.get(expected_type)
        if py_type is None:
            return True  # unknown type, skip
        return isinstance(value, py_type)

    def _matches_filters(self, doc: Dict[str, Any], filters: List[QueryFilter]) -> bool:
        """Check if a document matches all filters (AND logic)."""
        for f in filters:
            doc_val = doc.get(f.field)
            if not self._match_operator(doc_val, f.operator, f.value):
                return False
        return True

    def _match_operator(self, doc_val: Any, operator: str, filter_val: Any) -> bool:
        """Apply a single filter operator."""
        if operator == "eq":
            return doc_val == filter_val
        elif operator == "ne":
            return doc_val != filter_val
        elif operator == "gt":
            return doc_val is not None and doc_val > filter_val
        elif operator == "gte":
            return doc_val is not None and doc_val >= filter_val
        elif operator == "lt":
            return doc_val is not None and doc_val < filter_val
        elif operator == "lte":
            return doc_val is not None and doc_val <= filter_val
        elif operator == "in":
            return doc_val in (filter_val if isinstance(filter_val, list) else [filter_val])
        elif operator == "contains":
            if isinstance(doc_val, str) and isinstance(filter_val, str):
                return filter_val in doc_val
            if isinstance(doc_val, list):
                return filter_val in doc_val
            return False
        elif operator == "regex":
            if isinstance(doc_val, str) and isinstance(filter_val, str):
                try:
                    return bool(re.search(filter_val, doc_val))
                except re.error:
                    return False
            return False
        return False
