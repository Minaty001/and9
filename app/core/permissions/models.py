"""
Permission Models.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class Permission:
    """A single permission definition."""

    def __init__(self, resource: str, action: str, scope: str = "global",
                 conditions: Optional[Dict] = None, grant: bool = True):
        self.resource = resource
        self.action = action
        self.scope = scope
        self.conditions = conditions or {}
        self.grant = grant

    def __repr__(self) -> str:
        return f"Permission(resource={self.resource}, action={self.action}, scope={self.scope}, grant={self.grant})"


class Role:
    """A role with associated permissions."""

    def __init__(self, id: str, name: str, description: str = "",
                 permissions: Optional[List[Permission]] = None, priority: int = 0,
                 is_default: bool = False, parent_role: str = "",
                 metadata: Optional[Dict] = None):
        self.id = id
        self.name = name
        self.description = description
        self.permissions = permissions or []
        self.priority = priority
        self.is_default = is_default
        self.parent_role = parent_role
        self.metadata = metadata or {}

    def __repr__(self) -> str:
        return f"Role(name={self.name}, priority={self.priority})"


class UserPermissions:
    """A user's assigned permissions and roles."""

    def __init__(self, user_id: str, roles: Optional[List[str]] = None,
                 custom_permissions: Optional[List[Permission]] = None,
                 resource_restrictions: Optional[Dict] = None,
                 session_scope: Optional[Dict] = None,
                 expires_at: Optional[datetime] = None):
        self.user_id = user_id
        self.roles = roles or []
        self.custom_permissions = custom_permissions or []
        self.resource_restrictions = resource_restrictions or {}
        self.session_scope = session_scope or {}
        self.expires_at = expires_at


class PermissionCheckResult:
    """Result of a permission check."""

    def __init__(self, is_granted: bool = False, matched_permission: Optional[Permission] = None,
                 matched_role: str = "", reason: str = "", check_time_ms: float = 0.0,
                 fallback_action: str = "none"):
        self.is_granted = is_granted
        self.matched_permission = matched_permission
        self.matched_role = matched_role
        self.reason = reason
        self.check_time_ms = check_time_ms
        self.fallback_action = fallback_action


class AndroidPermissionState(str, Enum):
    """State of an Android runtime permission."""

    GRANTED = "granted"
    DENIED = "denied"
    NEVER_ASKED = "never_asked"
    BLOCKED = "blocked"


# Common Android permission groups
ANDROID_PERMISSION_GROUPS = {
    "CAMERA": "android.permission.CAMERA",
    "RECORD_AUDIO": "android.permission.RECORD_AUDIO",
    "ACCESS_FINE_LOCATION": "android.permission.ACCESS_FINE_LOCATION",
    "ACCESS_COARSE_LOCATION": "android.permission.ACCESS_COARSE_LOCATION",
    "READ_CONTACTS": "android.permission.READ_CONTACTS",
    "WRITE_CONTACTS": "android.permission.WRITE_CONTACTS",
    "READ_EXTERNAL_STORAGE": "android.permission.READ_EXTERNAL_STORAGE",
    "WRITE_EXTERNAL_STORAGE": "android.permission.WRITE_EXTERNAL_STORAGE",
    "SEND_SMS": "android.permission.SEND_SMS",
    "CALL_PHONE": "android.permission.CALL_PHONE",
    "READ_CALENDAR": "android.permission.READ_CALENDAR",
    "WRITE_CALENDAR": "android.permission.WRITE_CALENDAR",
    "BODY_SENSORS": "android.permission.BODY_SENSORS",
}


class AndroidPermission:
    """An Android runtime permission with state tracking."""

    def __init__(self, name: str, group: str,
                 state: AndroidPermissionState = AndroidPermissionState.NEVER_ASKED,
                 asked_count: int = 0, last_asked: Optional[datetime] = None):
        self.name = name
        self.group = group
        self.state = state
        self.asked_count = asked_count
        self.last_asked = last_asked
