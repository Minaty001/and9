"""
Phase 43 — Backup Manager.

Creates, restores, lists, deletes, and prunes backups with
checksum verification and retention policy enforcement.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from .models import Backup
from .config import MaintenanceConfig

logger = logging.getLogger(__name__)


class BackupManager:
    """Manages backup creation, restoration, and lifecycle.

    Usage:
        bm = BackupManager(config)
        backup = bm.create_backup("pre-upgrade", data={"key": "value"})
        data = bm.restore_backup(backup.id)
        backups = bm.list_backups()
    """

    def __init__(self, config: Optional[MaintenanceConfig] = None):
        self.config = config or MaintenanceConfig()
        self._backups: Dict[str, Backup] = {}
        self._data_store: Dict[str, Any] = {}

    def create_backup(
        self,
        name: str,
        data: Any,
        backup_type: str = "full",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Backup:
        """Create a backup with checksum verification.

        Args:
            name: Human-readable backup name.
            data: The data to back up (must be JSON-serializable).
            backup_type: "full" or "incremental".
            metadata: Additional metadata.

        Returns:
            The created Backup record.
        """
        if not self.config.enable_backup:
            raise RuntimeError("Backup management is disabled")

        backup_id = uuid.uuid4().hex[:12]
        serialized = json.dumps(data, default=str, ensure_ascii=False).encode("utf-8")
        checksum = hashlib.sha256(serialized).hexdigest()
        path = os.path.join(self.config.data_dir, f"backup_{backup_id}.json")

        backup = Backup(
            id=backup_id,
            name=name,
            size_bytes=len(serialized),
            entries_count=len(data) if isinstance(data, dict) else 1,
            type=backup_type,
            checksum=checksum,
            path=path,
            metadata=metadata or {},
        )

        self._backups[backup_id] = backup
        self._data_store[backup_id] = data

        if not os.path.exists(self.config.data_dir):
            os.makedirs(self.config.data_dir, exist_ok=True)

        with open(path, "w") as f:
            f.write(json.dumps({"checksum": checksum, "data": data}, default=str))

        logger.info("Created backup %s (type=%s, size=%d bytes)", backup_id, backup_type, backup.size_bytes)
        return backup

    def restore_backup(self, backup_id: str) -> Any:
        """Restore data from a backup.

        Args:
            backup_id: ID of the backup to restore.

        Returns:
            The restored data.

        Raises:
            ValueError: If backup_id not found.
        """
        backup = self._backups.get(backup_id)
        if not backup:
            raise ValueError(f"Backup not found: {backup_id}")

        # Verify integrity
        if not self.verify_backup(backup_id):
            raise ValueError(f"Backup integrity check failed: {backup_id}")

        return self._data_store.get(backup_id)

    def list_backups(self) -> List[Backup]:
        """List all backups in reverse chronological order."""
        return sorted(
            self._backups.values(),
            key=lambda b: b.timestamp,
            reverse=True,
        )

    def delete_backup(self, backup_id: str) -> bool:
        """Delete a backup by ID.

        Args:
            backup_id: ID of the backup to delete.

        Returns:
            True if deleted, False if not found.
        """
        if backup_id not in self._backups:
            return False

        backup = self._backups[backup_id]
        if os.path.exists(backup.path):
            try:
                os.remove(backup.path)
            except OSError as e:
                logger.warning("Could not remove backup file %s: %s", backup.path, e)

        del self._backups[backup_id]
        self._data_store.pop(backup_id, None)
        logger.info("Deleted backup %s", backup_id)
        return True

    def prune_old_backups(self) -> int:
        """Remove backups exceeding retention policy.

        Removes backups older than backup_retention_days and ensures
        total backups do not exceed max_backups.

        Returns:
            Number of pruned backups.
        """
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=self.config.backup_retention_days)
        pruned = 0

        # Remove expired by age
        expired_ids = [
            bid for bid, b in self._backups.items()
            if b.timestamp < cutoff
        ]
        for bid in expired_ids:
            self.delete_backup(bid)
            pruned += 1

        # Enforce max count
        sorted_backups = sorted(
            self._backups.items(),
            key=lambda item: item[1].timestamp,
            reverse=True,
        )
        while len(sorted_backups) > self.config.max_backups:
            bid, _ = sorted_backups.pop()
            self.delete_backup(bid)
            pruned += 1

        if pruned:
            logger.info("Pruned %d old backup(s)", pruned)
        return pruned

    def verify_backup(self, backup_id: str) -> bool:
        """Verify backup integrity by re-computing the checksum.

        Args:
            backup_id: ID of the backup to verify.

        Returns:
            True if the backup is intact, False otherwise.
        """
        backup = self._backups.get(backup_id)
        if not backup:
            return False

        data = self._data_store.get(backup_id)
        if data is None:
            return False

        serialized = json.dumps(data, default=str, ensure_ascii=False).encode("utf-8")
        actual_checksum = hashlib.sha256(serialized).hexdigest()
        return actual_checksum == backup.checksum
