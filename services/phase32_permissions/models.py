"""
Phase 32 — Permission Models.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Permission(BaseModel):
    """A single permission definition."""

    resource: str = Field(..., description="Resource identifier")
    action: str = Field(..., description="Action: read/write/execute/admin/delete")
    scope: str = Field(default="global", description="Scope: global/user/session/resource")
    conditions: dict = Field(default_factory=dict, description="Conditional constraints")
    grant: bool = Field(default=True, description="Whether permission is granted")


class Role(BaseModel):
    """A role with associated permissions."""

    id: str = Field(..., description="Unique role identifier")
    name: str = Field(..., description="Role name")
    description: str = Field(default="", description="Role description")
    permissions: List[Permission] = Field(default_factory=list, description="Role permissions")
    priority: int = Field(default=0, description="Priority (higher = more precedence)")
    is_default: bool = Field(default=False, description="Default role for new users")
    parent_role: str = Field(default="", description="Parent role name to inherit from")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")


class UserPermissions(BaseModel):
    """A user's assigned permissions and roles."""

    user_id: str = Field(..., description="User identifier")
    roles: List[str] = Field(default_factory=list, description="Role names assigned")
    custom_permissions: List[Permission] = Field(default_factory=list, description="Direct permissions")
    resource_restrictions: dict = Field(default_factory=dict, description="Resource access restrictions")
    session_scope: dict = Field(default_factory=dict, description="Session-level scope")
    expires_at: Optional[datetime] = Field(default=None, description="Permission expiration")


class PermissionCheckResult(BaseModel):
    """Result of a permission check."""

    is_granted: bool = Field(default=False, description="Whether permission is granted")
    matched_permission: Optional[Permission] = Field(default=None, description="Matched permission")
    matched_role: str = Field(default="", description="Role that granted the permission")
    reason: str = Field(default="", description="Explanation of the result")
    check_time_ms: float = Field(default=0.0, description="Time taken for the check")
    fallback_action: str = Field(
        default="none",
        description="Fallback action when denied: none/degrade/skip/ask/mock",
    )


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


class AndroidPermission(BaseModel):
    """An Android runtime permission with state tracking."""

    name: str = Field(..., description="Permission name (e.g., android.permission.CAMERA)")
    group: str = Field(..., description="Permission group (e.g., CAMERA)")
    state: AndroidPermissionState = Field(default=AndroidPermissionState.NEVER_ASKED, description="Current state")
    asked_count: int = Field(default=0, description="Number of times user has been asked")
    last_asked: Optional[datetime] = Field(default=None, description="When the user was last asked")
