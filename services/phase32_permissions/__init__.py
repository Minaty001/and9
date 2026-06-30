"""
Phase 32 — Permission Manager
===============================

Granular permissions, roles, resource scoping, permission checking,
Android runtime permissions, and fallback-aware access control.
Owner/admin/user role model with cached permission checks.

Components:
    - RoleManager: CRUD for roles and role assignments
    - PermissionChecker: Check user permissions with caching and fallback logic
    - AndroidPermissionManager: Android runtime permission state tracking
    - PermissionManagerService: ServiceBase wrapper
"""

from .config import PermissionConfig
from .models import (
    Permission,
    Role,
    UserPermissions,
    PermissionCheckResult,
    AndroidPermission,
    AndroidPermissionState,
    ANDROID_PERMISSION_GROUPS,
)
from .role_manager import RoleManager
from .permission_checker import PermissionChecker
from .android_permissions import AndroidPermissionManager
from .service import PermissionManagerService

__all__ = [
    "PermissionConfig",
    "Permission",
    "Role",
    "UserPermissions",
    "PermissionCheckResult",
    "AndroidPermission",
    "AndroidPermissionState",
    "ANDROID_PERMISSION_GROUPS",
    "RoleManager",
    "PermissionChecker",
    "AndroidPermissionManager",
    "PermissionManagerService",
]
