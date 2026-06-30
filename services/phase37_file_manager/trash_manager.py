"""
Phase 37 — Trash Manager.

Move to trash, restore, empty trash, cleanup expired items.
"""

from __future__ import annotations

import uuid
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from .config import FileManagerConfig
from .models import FileItem

logger = logging.getLogger(__name__)


class TrashManager:
    """Manage trashed files with retention and recovery.

    Usage:
        mgr = TrashManager()
        mgr.move_to_trash("/path/to/file")
        mgr.restore("/path/to/file")
        mgr.empty_trash()
    """

    def __init__(self, config: Optional[FileManagerConfig] = None):
        self.config = config or FileManagerConfig()
        self._trash: Dict[str, Dict[str, Any]] = {}  # trash_id -> {file_item, original_path, trashed_at}

    def move_to_trash(self, path: str, item: FileItem) -> bool:
        """Move a file item to trash.

        Args:
            path: Original file path.
            item: FileItem to trash.

        Returns:
            True if trashed.
        """
        if not self.config.enable_trash:
            return False

        trash_id = uuid.uuid4().hex[:12]
        self._trash[trash_id] = {
            "trash_id": trash_id,
            "original_path": path,
            "file_item": item,
            "trashed_at": datetime.now(timezone.utc),
        }
        logger.debug("Moved to trash: %s (id=%s)", path, trash_id)
        return True

    def restore(self, path: str) -> bool:
        """Restore the most recent trash entry for a path.

        Returns True if restored.
        """
        candidates = [
            (tid, entry) for tid, entry in self._trash.items()
            if entry["original_path"] == path
        ]
        if not candidates:
            return False

        # Restore the most recent
        candidates.sort(key=lambda x: x[1]["trashed_at"], reverse=True)
        tid = candidates[0][0]
        del self._trash[tid]
        logger.debug("Restored from trash: %s", path)
        return True

    def empty_trash(self) -> int:
        """Permanently delete all trashed items.

        Returns the number of items emptied.
        """
        count = len(self._trash)
        self._trash.clear()
        logger.debug("Emptied trash (%d items)", count)
        return count

    def list_trash(self) -> List[Dict[str, Any]]:
        """List all items in trash."""
        return [
            {
                "trash_id": entry["trash_id"],
                "original_path": entry["original_path"],
                "name": entry["file_item"].name,
                "file_type": entry["file_item"].file_type,
                "size_bytes": entry["file_item"].size_bytes,
                "trashed_at": entry["trashed_at"].isoformat(),
                "expires_at": (entry["trashed_at"] + timedelta(days=self.config.trash_retention_days)).isoformat(),
            }
            for entry in self._trash.values()
        ]

    def recover_file(self, trash_id: str) -> Optional[FileItem]:
        """Recover a specific trash item by ID.

        Returns the FileItem if found, None otherwise.
        """
        entry = self._trash.get(trash_id)
        if not entry:
            return None
        item = entry["file_item"]
        del self._trash[trash_id]
        return item

    def cleanup_expired(self) -> int:
        """Remove expired trash items based on retention days.

        Returns the number of items cleaned up.
        """
        now = datetime.now(timezone.utc)
        expired_ids = []
        for tid, entry in self._trash.items():
            age = now - entry["trashed_at"]
            if age.days >= self.config.trash_retention_days:
                expired_ids.append(tid)

        for tid in expired_ids:
            del self._trash[tid]

        logger.debug("Cleaned up %d expired trash items", len(expired_ids))
        return len(expired_ids)
