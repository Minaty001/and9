"""
Phase 43 — Deprecation Manager.

Tracks deprecated APIs, features, configs, and endpoints.
Provides registration, querying, expiration checks, and cleanup.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from .models import DeprecationNotice
from .config import MaintenanceConfig

logger = logging.getLogger(__name__)


class DeprecationManager:
    """Manages deprecation notices for system components.

    Usage:
        dm = DeprecationManager()
        dm.deprecate("old_api", "api", "new_api", "3.0.0")
        assert dm.check_deprecated("old_api", "api") is True
    """

    def __init__(self, config: Optional[MaintenanceConfig] = None):
        self.config = config or MaintenanceConfig()
        self._notices: dict = {}
        self._version = "1.0.0"

    def set_current_version(self, version: str) -> None:
        """Set the current application version for expiration checks."""
        self._version = version

    def deprecate(
        self,
        item_name: str,
        item_type: str = "api",
        alternative: Optional[str] = None,
        removal_version: Optional[str] = None,
        notice: str = "",
    ) -> DeprecationNotice:
        """Register a deprecation notice.

        Args:
            item_name: Name of the item being deprecated.
            item_type: Type (api, feature, config, endpoint).
            alternative: Recommended replacement.
            removal_version: Version in which it will be removed.
            notice: Detailed deprecation message.

        Returns:
            The created DeprecationNotice.
        """
        notice_id = uuid.uuid4().hex[:12]
        d = DeprecationNotice(
            item_name=item_name,
            item_type=item_type,
            deprecated_in_version=self._version,
            removal_in_version=removal_version or f"{self._parse_major(self._version) + 1}.0.0",
            alternative=alternative,
            notice=notice or f"{item_name} ({item_type}) is deprecated.",
        )
        self._notices[notice_id] = d
        logger.info("Deprecated %s (%s) -> %s", item_name, item_type, alternative)
        return d

    def get_deprecations(self) -> List[DeprecationNotice]:
        """List all active deprecation notices."""
        return list(self._notices.values())

    def check_deprecated(self, name: str, item_type: str = "api") -> bool:
        """Check if a specific item is deprecated.

        Args:
            name: Item name.
            item_type: Item type.

        Returns:
            True if the item has a deprecation notice.
        """
        for d in self._notices.values():
            if d.item_name == name and d.item_type == item_type:
                return True
        return False

    def get_expired(self) -> List[DeprecationNotice]:
        """Get deprecation notices that are past their removal version."""
        current_parts = [int(p) for p in self._version.split(".")]
        expired = []

        for d in self._notices.values():
            removal_parts = [int(p) for p in d.removal_in_version.split(".")]
            # Compare version tuples
            if tuple(current_parts) >= tuple(removal_parts):
                expired.append(d)

        return expired

    def cleanup_expired(self) -> int:
        """Remove expired deprecation notices.

        Returns:
            Number of notices removed.
        """
        expired = self.get_expired()
        expired_ids = [
            nid for nid, d in self._notices.items()
            if d in expired
        ]
        for nid in expired_ids:
            del self._notices[nid]
        count = len(expired_ids)
        if count:
            logger.info("Cleaned up %d expired deprecation notice(s)", count)
        return count

    # ── Internal ──────────────────────────────────────────────────

    @staticmethod
    def _parse_major(version: str) -> int:
        try:
            return int(version.split(".")[0])
        except (ValueError, IndexError):
            return 1
