"""
Phase 36 — Migration Manager.

Manage schema migrations for collections.
"""

from __future__ import annotations

import uuid
import time
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .config import DatabaseConfig

logger = logging.getLogger(__name__)


class MigrationManager:
    """Manage migrations for database collections.

    Usage:
        mgr = MigrationManager()
        mid = mgr.create_migration("add_email_field")
        mgr.apply_migration(mid)
        mgr.rollback_migration(mid)
    """

    def __init__(self, config: Optional[DatabaseConfig] = None):
        self.config = config or DatabaseConfig()
        self._migrations: Dict[str, Dict[str, Any]] = {}

    def create_migration(self, name: str, actions: Optional[List[Dict[str, Any]]] = None) -> str:
        """Create a new migration.

        Args:
            name: Human-readable migration name.
            actions: Optional list of migration action dicts.

        Returns:
            Migration ID string.
        """
        mid = uuid.uuid4().hex[:12]
        self._migrations[mid] = {
            "id": mid,
            "name": name,
            "status": "pending",
            "actions": actions or [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "applied_at": None,
            "rolled_back_at": None,
        }
        logger.info("Created migration '%s' (%s)", name, mid)
        return mid

    def apply_migration(self, id: str) -> bool:
        """Apply a pending migration.

        Returns True if applied successfully.
        """
        migration = self._migrations.get(id)
        if not migration:
            logger.error("Migration '%s' not found", id)
            return False
        if migration["status"] != "pending":
            logger.error("Migration '%s' is not pending (status=%s)", id, migration["status"])
            return False
        if not self.config.enable_migration:
            return False

        migration["status"] = "applied"
        migration["applied_at"] = datetime.now(timezone.utc).isoformat()
        logger.info("Applied migration '%s' (%s)", migration["name"], id)
        return True

    def rollback_migration(self, id: str) -> bool:
        """Rollback an applied migration.

        Returns True if rolled back successfully.
        """
        migration = self._migrations.get(id)
        if not migration:
            logger.error("Migration '%s' not found", id)
            return False
        if migration["status"] != "applied":
            logger.error("Migration '%s' is not applied (status=%s)", id, migration["status"])
            return False
        if not self.config.enable_migration:
            return False

        migration["status"] = "rolled_back"
        migration["rolled_back_at"] = datetime.now(timezone.utc).isoformat()
        logger.info("Rolled back migration '%s' (%s)", migration["name"], id)
        return True

    def list_migrations(self) -> List[Dict[str, Any]]:
        """List all migrations."""
        return [
            {
                "id": m["id"],
                "name": m["name"],
                "status": m["status"],
                "created_at": m["created_at"],
                "applied_at": m.get("applied_at"),
                "rolled_back_at": m.get("rolled_back_at"),
            }
            for m in self._migrations.values()
        ]

    def get_migration_status(self, id: str) -> str:
        """Get the status of a migration.

        Returns status string or 'not_found'.
        """
        migration = self._migrations.get(id)
        if not migration:
            return "not_found"
        return migration["status"]
