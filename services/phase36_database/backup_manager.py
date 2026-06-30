"""
Phase 36 — Backup Manager.

Export/import all collections to/from JSON for backup and restore.
Supports scheduled periodic backups.
"""

from __future__ import annotations

import json
import os
import time
import logging
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .config import DatabaseConfig
from .document_store import DocumentStore

logger = logging.getLogger(__name__)


class BackupManager:
    """Export/import all collections to/from JSON.

    Usage:
        bm = BackupManager(store)
        data = bm.create_backup()
        count = bm.restore_backup(data)
        bm.create_backup_file("/tmp/backup.json")
        bm.restore_backup_file("/tmp/backup.json")
        bm.schedule_backup(interval_minutes=30)
    """

    def __init__(self, store: DocumentStore, config: Optional[DatabaseConfig] = None):
        self.store = store
        self.config = config or DatabaseConfig()
        self._timer: Optional[threading.Timer] = None
        self._running = False

    # ── Create Backup ────────────────────────────────────────────────

    def create_backup(self) -> Dict[str, Any]:
        """Export all collections, documents, schema defs, and migration state to a dict.

        Returns:
            A dict containing the full backup.
        """
        collections_data: Dict[str, List[Dict[str, Any]]] = {}
        schemas_data: Dict[str, Dict[str, Any]] = {}

        for name, docs in self.store._collections.items():
            collections_data[name] = list(docs.values())
            schema = self.store._schemas.get(name)
            if schema:
                schemas_data[name] = schema.model_dump()

        backup = {
            "version": "1.0",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "collections": collections_data,
            "schemas": schemas_data,
            "collection_count": len(collections_data),
            "document_count": sum(len(docs) for docs in collections_data.values()),
        }

        logger.info(
            "Created backup: %d collections, %d documents",
            backup["collection_count"],
            backup["document_count"],
        )
        return backup

    # ── Restore Backup ───────────────────────────────────────────────

    def restore_backup(self, data: Dict[str, Any]) -> int:
        """Restore all collections, documents, and schemas from a backup dict.

        Args:
            data: Backup dict from create_backup().

        Returns:
            Number of documents restored.
        """
        restored_docs = 0

        collections = data.get("collections", {})
        schemas = data.get("schemas", {})

        for name, schema_dict in schemas.items():
            # Recreate schema
            from .models import CollectionSchema
            schema = CollectionSchema(**schema_dict)
            self.store.create_collection(schema)

        for name, docs in collections.items():
            # Ensure collection exists
            if name not in self.store._collections:
                from .models import CollectionSchema
                schema_data = schemas.get(name, {"name": name, "fields": {}, "strict": False})
                schema = CollectionSchema(**schema_data)
                self.store.create_collection(schema)

            # Restore documents
            for doc in docs:
                doc_id = doc.get("_id")
                # Use internal insertion to preserve IDs
                if doc_id and name in self.store._collections:
                    self.store._collections[name][doc_id] = doc
                    if name in self.store._id_map and doc_id not in self.store._id_map[name]:
                        self.store._id_map[name].append(doc_id)
                    restored_docs += 1

        logger.info("Restored backup: %d documents in %d collections", restored_docs, len(collections))
        return restored_docs

    # ── File-based Backup / Restore ──────────────────────────────────

    def create_backup_file(self, path: str) -> None:
        """Export backup to a JSON file.

        Args:
            path: Filesystem path to write the backup JSON.
        """
        data = self.create_backup()
        os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        logger.info("Backup written to file: %s", path)

    def restore_backup_file(self, path: str) -> int:
        """Restore backup from a JSON file.

        Args:
            path: Filesystem path to read the backup JSON from.

        Returns:
            Number of documents restored.
        """
        if not os.path.isfile(path):
            logger.error("Backup file not found: %s", path)
            return 0

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return self.restore_backup(data)

    # ── Scheduled Backup ─────────────────────────────────────────────

    def schedule_backup(self, interval_minutes: int) -> None:
        """Set up periodic backups at the given interval.

        Args:
            interval_minutes: Minutes between backups. Set to 0 to disable.
        """
        self.stop()

        if interval_minutes <= 0:
            logger.info("Scheduled backup disabled")
            return

        self._running = True

        def _run():
            if not self._running:
                return
            try:
                backup = self.create_backup()
                logger.info("Scheduled backup: %d documents", backup.get("document_count", 0))
            except Exception as e:
                logger.error("Scheduled backup failed: %s", e)
            if self._running:
                self._timer = threading.Timer(interval_minutes * 60.0, _run)
                self._timer.daemon = True
                self._timer.start()

        self._timer = threading.Timer(interval_minutes * 60.0, _run)
        self._timer.daemon = True
        self._timer.start()
        logger.info("Scheduled backup every %d minutes", interval_minutes)

    def stop(self) -> None:
        """Stop scheduled backups."""
        self._running = False
        if self._timer:
            self._timer.cancel()
            self._timer = None
