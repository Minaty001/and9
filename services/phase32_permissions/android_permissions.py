"""
Phase 32 — Android Permission Manager.

Models Android runtime permissions with state tracking
(granted, denied, never_asked, blocked) and support for
common Android permission groups.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from .models import (
    ANDROID_PERMISSION_GROUPS,
    AndroidPermission,
    AndroidPermissionState,
)

logger = logging.getLogger(__name__)


class AndroidPermissionManager:
    """Manages Android runtime permissions with state tracking.

    Simulates the Android runtime permission model where each
    permission can be in one of four states: granted, denied,
    never_asked, or blocked (don't ask again).

    Usage:
        mgr = AndroidPermissionManager()
        state = mgr.check_permission("CAMERA")
        mgr.request_permission("CAMERA")  # simulated async grant
        granted = mgr.get_granted_permissions()
    """

    def __init__(self):
        """Initialize the manager with all standard permissions."""
        self._permissions: Dict[str, AndroidPermission] = {}
        self._initialize_permissions()

    def _initialize_permissions(self) -> None:
        """Create initial permission entries for all standard groups."""
        for group, perm_name in ANDROID_PERMISSION_GROUPS.items():
            self._permissions[group] = AndroidPermission(
                name=perm_name,
                group=group,
                state=AndroidPermissionState.NEVER_ASKED,
            )

    def check_permission(self, permission_group: str) -> AndroidPermissionState:
        """Check the current state of a permission.

        Args:
            permission_group: The permission group name (e.g., "CAMERA").

        Returns:
            The current AndroidPermissionState, or NEVER_ASKED if unknown.
        """
        perm = self._permissions.get(permission_group.upper())
        if not perm:
            return AndroidPermissionState.NEVER_ASKED
        return perm.state

    def request_permission(self, permission_group: str) -> bool:
        """Simulate requesting a permission from the user (async grant flow).

        In development mode, this automatically grants the permission.
        In production, this would trigger an Android system dialog.

        Args:
            permission_group: The permission group name (e.g., "CAMERA").

        Returns:
            True if the permission was granted, False otherwise.
        """
        perm = self._ensure_permission(permission_group)
        if not perm:
            return False

        perm.asked_count += 1
        perm.last_asked = datetime.now(timezone.utc)

        # Simulate: if blocked, deny; otherwise grant
        if perm.state == AndroidPermissionState.BLOCKED:
            logger.debug("Permission '%s' is blocked, cannot request", permission_group)
            return False

        # Auto-grant simulation (in production this would show a system dialog)
        perm.state = AndroidPermissionState.GRANTED
        logger.debug("Permission '%s' granted (simulated)", permission_group)
        return True

    def grant_permission(self, permission_group: str) -> bool:
        """Manually grant a permission.

        Args:
            permission_group: The permission group name.

        Returns:
            True if granted.
        """
        perm = self._ensure_permission(permission_group)
        if not perm:
            return False
        perm.state = AndroidPermissionState.GRANTED
        logger.debug("Permission '%s' manually granted", permission_group)
        return True

    def deny_permission(self, permission_group: str) -> bool:
        """Manually deny a permission.

        Args:
            permission_group: The permission group name.

        Returns:
            True if denied.
        """
        perm = self._ensure_permission(permission_group)
        if not perm:
            return False
        perm.state = AndroidPermissionState.DENIED
        logger.debug("Permission '%s' manually denied", permission_group)
        return True

    def block_permission(self, permission_group: str) -> bool:
        """Block a permission (don't ask again).

        Args:
            permission_group: The permission group name.

        Returns:
            True if blocked.
        """
        perm = self._ensure_permission(permission_group)
        if not perm:
            return False
        perm.state = AndroidPermissionState.BLOCKED
        logger.debug("Permission '%s' blocked", permission_group)
        return True

    def get_granted_permissions(self) -> List[AndroidPermission]:
        """Get all currently granted permissions.

        Returns:
            List of AndroidPermission with state GRANTED.
        """
        return [
            p for p in self._permissions.values()
            if p.state == AndroidPermissionState.GRANTED
        ]

    def get_denied_permissions(self) -> List[AndroidPermission]:
        """Get all denied or blocked permissions.

        Returns:
            List of AndroidPermission with state DENIED or BLOCKED.
        """
        return [
            p for p in self._permissions.values()
            if p.state in (AndroidPermissionState.DENIED, AndroidPermissionState.BLOCKED)
        ]

    def get_permission_state(self, permission_group: str) -> Optional[AndroidPermission]:
        """Get the full permission object with state details.

        Args:
            permission_group: The permission group name.

        Returns:
            AndroidPermission or None if unknown.
        """
        return self._permissions.get(permission_group.upper())

    def list_permissions(self) -> List[AndroidPermission]:
        """List all tracked permissions with their states.

        Returns:
            List of all AndroidPermission objects.
        """
        return list(self._permissions.values())

    def reset_permission(self, permission_group: str) -> bool:
        """Reset a permission to never_asked state.

        Args:
            permission_group: The permission group name.

        Returns:
            True if reset.
        """
        perm = self._permissions.get(permission_group.upper())
        if not perm:
            return False
        perm.state = AndroidPermissionState.NEVER_ASKED
        perm.asked_count = 0
        perm.last_asked = None
        return True

    def reset_all(self) -> None:
        """Reset all permissions to never_asked state."""
        for perm in self._permissions.values():
            perm.state = AndroidPermissionState.NEVER_ASKED
            perm.asked_count = 0
            perm.last_asked = None

    def _ensure_permission(self, permission_group: str) -> Optional[AndroidPermission]:
        """Get or create a permission entry.

        Args:
            permission_group: The permission group name.

        Returns:
            AndroidPermission or None if group is unknown.
        """
        group = permission_group.upper()
        if group not in self._permissions:
            # Check if it's a known group
            if group in ANDROID_PERMISSION_GROUPS:
                self._permissions[group] = AndroidPermission(
                    name=ANDROID_PERMISSION_GROUPS[group],
                    group=group,
                )
            else:
                logger.warning("Unknown permission group: %s", permission_group)
                return None
        return self._permissions[group]
