"""
Android Permission Manager.

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
        mgr.request_permission("CAMERA")
        granted = mgr.get_granted_permissions()
    """

    def __init__(self):
        self._permissions: Dict[str, AndroidPermission] = {}
        self._initialize_permissions()

    def _initialize_permissions(self) -> None:
        for group, perm_name in ANDROID_PERMISSION_GROUPS.items():
            self._permissions[group] = AndroidPermission(
                name=perm_name,
                group=group,
                state=AndroidPermissionState.NEVER_ASKED,
            )

    def check_permission(self, permission_group: str) -> AndroidPermissionState:
        perm = self._permissions.get(permission_group.upper())
        if not perm:
            return AndroidPermissionState.NEVER_ASKED
        return perm.state

    def request_permission(self, permission_group: str) -> bool:
        perm = self._ensure_permission(permission_group)
        if not perm:
            return False

        perm.asked_count += 1
        perm.last_asked = datetime.now(timezone.utc)

        if perm.state == AndroidPermissionState.BLOCKED:
            logger.debug("Permission '%s' is blocked, cannot request", permission_group)
            return False

        perm.state = AndroidPermissionState.GRANTED
        logger.debug("Permission '%s' granted (simulated)", permission_group)
        return True

    def grant_permission(self, permission_group: str) -> bool:
        perm = self._ensure_permission(permission_group)
        if not perm:
            return False
        perm.state = AndroidPermissionState.GRANTED
        logger.debug("Permission '%s' manually granted", permission_group)
        return True

    def deny_permission(self, permission_group: str) -> bool:
        perm = self._ensure_permission(permission_group)
        if not perm:
            return False
        perm.state = AndroidPermissionState.DENIED
        logger.debug("Permission '%s' manually denied", permission_group)
        return True

    def block_permission(self, permission_group: str) -> bool:
        perm = self._ensure_permission(permission_group)
        if not perm:
            return False
        perm.state = AndroidPermissionState.BLOCKED
        logger.debug("Permission '%s' blocked", permission_group)
        return True

    def get_granted_permissions(self) -> List[AndroidPermission]:
        return [p for p in self._permissions.values() if p.state == AndroidPermissionState.GRANTED]

    def get_denied_permissions(self) -> List[AndroidPermission]:
        return [p for p in self._permissions.values() if p.state in (AndroidPermissionState.DENIED, AndroidPermissionState.BLOCKED)]

    def get_permission_state(self, permission_group: str) -> Optional[AndroidPermission]:
        return self._permissions.get(permission_group.upper())

    def list_permissions(self) -> List[AndroidPermission]:
        return list(self._permissions.values())

    def reset_permission(self, permission_group: str) -> bool:
        perm = self._permissions.get(permission_group.upper())
        if not perm:
            return False
        perm.state = AndroidPermissionState.NEVER_ASKED
        perm.asked_count = 0
        perm.last_asked = None
        return True

    def reset_all(self) -> None:
        for perm in self._permissions.values():
            perm.state = AndroidPermissionState.NEVER_ASKED
            perm.asked_count = 0
            perm.last_asked = None

    def _ensure_permission(self, permission_group: str) -> Optional[AndroidPermission]:
        group = permission_group.upper()
        if group not in self._permissions:
            if group in ANDROID_PERMISSION_GROUPS:
                self._permissions[group] = AndroidPermission(
                    name=ANDROID_PERMISSION_GROUPS[group],
                    group=group,
                )
            else:
                logger.warning("Unknown permission group: %s", permission_group)
                return None
        return self._permissions[group]
