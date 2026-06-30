"""
Phase 36 — Database Service.

ServiceBase wrapper for the Database Design service.
"""

from __future__ import annotations

import time
import logging
from typing import Any, Dict, List, Optional, Union, Union

from services.base.service_base import ServiceBase
from .config import DatabaseConfig
from .models import CollectionSchema, QueryFilter, QueryResult
from .document_store import DocumentStore
from .index_manager import IndexManager
from .migration_manager import MigrationManager
from .schemas import ALL_DOMAIN_SCHEMAS, seed_schemas
from .backup_manager import BackupManager

logger = logging.getLogger(__name__)


class DatabaseService(ServiceBase):
    """Database service for in-memory document storage.

    Usage:
        svc = DatabaseService()
        await svc.initialize()
        svc.create_collection(CollectionSchema(name="users", fields={...}))
        doc_id = svc.insert("users", {"name": "Alice"})
    """

    def __init__(self, config: Optional[DatabaseConfig] = None):
        super().__init__(name="jarvis_database", version="1.0.0")
        self.config = config or DatabaseConfig()
        self.store: Optional[DocumentStore] = None
        self.index_manager: Optional[IndexManager] = None
        self.migration_manager: Optional[MigrationManager] = None
        self.backup_manager: Optional[BackupManager] = None
        self._schemas_created: Dict[str, CollectionSchema] = {}
        self._start_time = 0.0

    async def initialize(self) -> bool:
        self._start_time = time.time()
        try:
            self.store = DocumentStore(self.config)
            self.index_manager = IndexManager(self.config)
            self.migration_manager = MigrationManager(self.config)
            self.backup_manager = BackupManager(self.store, self.config)
            self._metrics.reset()
            # Auto-create domain schemas
            created = seed_schemas(self.store)
            self._schemas_created = dict(ALL_DOMAIN_SCHEMAS)
            if created:
                logger.info("Seeded %d domain schemas on initialize", created)
            # Auto-backup if configured
            if self.config.auto_backup_interval_minutes > 0:
                self.backup_manager.schedule_backup(self.config.auto_backup_interval_minutes)
            self._initialized = True
            logger.info("DatabaseService initialized")
            return True
        except Exception as e:
            logger.error("DatabaseService init failed: %s", e)
            return False

    async def shutdown(self) -> None:
        logger.info("DatabaseService shutting down...")
        if self.backup_manager:
            self.backup_manager.stop()
        self._initialized = False

    # ── Collection Operations ─────────────────────────────────────

    async def create_collection(self, schema: CollectionSchema) -> bool:
        if not self.store:
            raise RuntimeError("DatabaseService not initialized")
        t0 = time.perf_counter()
        result = self.store.create_collection(schema)
        elapsed = (time.perf_counter() - t0) * 1000
        self._metrics.counter("collections_created", 1)
        self._metrics.histogram("operation_time_ms", elapsed)
        return result

    async def list_collections(self) -> List[Dict[str, Any]]:
        if not self.store:
            raise RuntimeError("DatabaseService not initialized")
        return self.store.list_collections()

    # ── Document Operations ────────────────────────────────────────

    async def insert(self, collection: str, doc: Dict[str, Any]) -> Optional[str]:
        if not self.store:
            raise RuntimeError("DatabaseService not initialized")
        # Auto-create collection if it doesn't exist
        if collection not in self.store._collections:
            self.store.create_collection(CollectionSchema(name=collection, fields={}, strict=False))
        t0 = time.perf_counter()
        result = self.store.insert(collection, doc)
        elapsed = (time.perf_counter() - t0) * 1000
        self._metrics.counter("documents_inserted", 1)
        self._metrics.histogram("operation_time_ms", elapsed)
        if result and self.index_manager:
            self.index_manager.add_document(collection, result,
                                            self.store._collections[collection][result])
        return result

    async def find(self, collection: str, filters: Optional[Union[List[QueryFilter], Dict[str, Any]]] = None,
             page: int = 1, page_size: int = 20) -> List[Dict[str, Any]]:
        if not self.store:
            raise RuntimeError("DatabaseService not initialized")
        # Convert dict filters to QueryFilter list
        if isinstance(filters, dict):
            filters = [QueryFilter(field=k, operator="eq", value=v) for k, v in filters.items()]
        t0 = time.perf_counter()
        result = self.store.find(collection, filters, page, page_size)
        elapsed = (time.perf_counter() - t0) * 1000
        self._metrics.counter("queries", 1)
        self._metrics.histogram("query_time_ms", elapsed)
        return result.documents

    async def find_one(self, collection: str, filters: Optional[Union[List[QueryFilter], Dict[str, Any]]] = None) -> Optional[Dict[str, Any]]:
        if not self.store:
            raise RuntimeError("DatabaseService not initialized")
        if isinstance(filters, dict):
            filters = [QueryFilter(field=k, operator="eq", value=v) for k, v in filters.items()]
        return self.store.find_one(collection, filters)

    async def update(self, collection: str, id: str, updates: Dict[str, Any]) -> bool:
        if not self.store:
            raise RuntimeError("DatabaseService not initialized")
        t0 = time.perf_counter()
        result = self.store.update(collection, id, updates)
        elapsed = (time.perf_counter() - t0) * 1000
        self._metrics.counter("documents_updated", 1)
        self._metrics.histogram("operation_time_ms", elapsed)
        return result

    async def delete(self, collection: str, id: str) -> bool:
        if not self.store:
            raise RuntimeError("DatabaseService not initialized")
        t0 = time.perf_counter()
        if self.index_manager and collection in self.store._collections:
            doc = self.store._collections[collection].get(id)
            if doc:
                self.index_manager.remove_document(collection, id, doc)
        result = self.store.delete(collection, id)
        elapsed = (time.perf_counter() - t0) * 1000
        self._metrics.counter("documents_deleted", 1)
        self._metrics.histogram("operation_time_ms", elapsed)
        return result

    # ── Index Operations ───────────────────────────────────────────

    async def create_index(self, collection: str, field: str) -> bool:
        if not self.index_manager:
            raise RuntimeError("DatabaseService not initialized")
        documents = self.store._collections.get(collection) if self.store else None
        return self.index_manager.create_index(collection, field, documents)

    async def drop_index(self, collection: str, field: str) -> bool:
        if not self.index_manager:
            raise RuntimeError("DatabaseService not initialized")
        return self.index_manager.drop_index(collection, field)

    async def list_indexes(self, collection: str) -> List[Dict[str, Any]]:
        if not self.index_manager:
            raise RuntimeError("DatabaseService not initialized")
        return self.index_manager.list_indexes(collection)

    async def optimize_indexes(self, collection: str) -> Dict[str, Any]:
        if not self.index_manager:
            raise RuntimeError("DatabaseService not initialized")
        return self.index_manager.optimize(collection)

    # ── Migration Operations ───────────────────────────────────────

    async def create_migration(self, name: str) -> str:
        if not self.migration_manager:
            raise RuntimeError("DatabaseService not initialized")
        return self.migration_manager.create_migration(name)

    async def apply_migration(self, id: str) -> bool:
        if not self.migration_manager:
            raise RuntimeError("DatabaseService not initialized")
        return self.migration_manager.apply_migration(id)

    async def rollback_migration(self, id: str) -> bool:
        if not self.migration_manager:
            raise RuntimeError("DatabaseService not initialized")
        return self.migration_manager.rollback_migration(id)

    async def list_migrations(self) -> List[Dict[str, Any]]:
        if not self.migration_manager:
            raise RuntimeError("DatabaseService not initialized")
        return self.migration_manager.list_migrations()

    async def get_migration_status(self, id: str) -> str:
        if not self.migration_manager:
            raise RuntimeError("DatabaseService not initialized")
        return self.migration_manager.get_migration_status(id)

    async def get_collection_stats(self) -> Dict[str, Any]:
        if not self.store:
            raise RuntimeError("DatabaseService not initialized")
        return self.store.get_stats()

    # ── Backup / Restore Operations ─────────────────────────────────────

    async def create_backup(self) -> Dict[str, Any]:
        """Create a full backup of all collections."""
        if not self.backup_manager:
            raise RuntimeError("DatabaseService not initialized")
        return self.backup_manager.create_backup()

    async def restore_backup(self, data: Dict[str, Any]) -> int:
        """Restore all collections from a backup dict.

        Returns the number of documents restored.
        """
        if not self.backup_manager:
            raise RuntimeError("DatabaseService not initialized")
        return self.backup_manager.restore_backup(data)

    async def create_backup_file(self, path: str) -> None:
        """Export backup to a JSON file."""
        if not self.backup_manager:
            raise RuntimeError("DatabaseService not initialized")
        self.backup_manager.create_backup_file(path)

    async def restore_backup_file(self, path: str) -> int:
        """Restore backup from a JSON file.

        Returns the number of documents restored.
        """
        if not self.backup_manager:
            raise RuntimeError("DatabaseService not initialized")
        return self.backup_manager.restore_backup_file(path)

    # ── Schema Operations ────────────────────────────────────────────────

    async def get_created_schemas(self) -> Dict[str, CollectionSchema]:
        """Return the dict of domain schemas that were created on startup."""
        return dict(self._schemas_created)

    async def get_domain_schema(self, name: str) -> Optional[CollectionSchema]:
        """Get a domain schema by collection name."""
        return ALL_DOMAIN_SCHEMAS.get(name)

    async def list_domain_schemas(self) -> List[str]:
        """List available domain schema names."""
        return list(ALL_DOMAIN_SCHEMAS.keys())

    # ── Health / Stats ─────────────────────────────────────────────

    async def health(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        stats = self.store.get_stats() if self.store else {}
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "service_name": self.name,
            "version": self.version,
            "initialized": self._initialized,
            "uptime_seconds": round(uptime, 1),
            "collections": stats.get("collections", 0),
            "total_documents": stats.get("total_documents", 0),
        }

    async def stats(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        store_stats = self.store.get_stats() if self.store else {}
        return {
            "service": self.name,
            "version": self.version,
            "uptime_seconds": round(uptime, 1),
            "collections": store_stats,
            "metrics": self._metrics.snapshot(),
        }
