"""
app/core/permissions/ — Permission Manager

Granular permissions, roles, resource scoping, permission checking,
Android runtime permissions, and fallback-aware access control.
"""

from .models import Permission, Role, UserPermissions, PermissionCheckResult
from .role_manager import RoleManager
from .permission_checker import PermissionChecker
from .android_permissions import AndroidPermissionManager

__all__ = [
    "Permission",
    "Role",
    "UserPermissions",
    "PermissionCheckResult",
    "RoleManager",
    "PermissionChecker",
    "AndroidPermissionManager",
]
