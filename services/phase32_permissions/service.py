"""
Phase 32 — Permission Manager Service.

ServiceBase wrapper for the Permission Manager.
Includes Android runtime permission handling and fallback-aware checks.
"""

from __future__ import annotations

import time
import logging
from typing import Any, Dict, List, Optional

from services.base.service_base import ServiceBase
from .config import PermissionConfig
from .models import (
    Permission,
    Role,
    UserPermissions,
    PermissionCheckResult,
    AndroidPermission,
    AndroidPermissionState,
)
from .role_manager import RoleManager
from .permission_checker import PermissionChecker
from .android_permissions import AndroidPermissionManager

logger = logging.getLogger(__name__)


class PermissionManagerService(ServiceBase):
    """Permission management service.

    Usage:
        svc = PermissionManagerService()
        await svc.initialize()
        result = await svc.has_permission("user123", "document", "read")
        await svc.create_role("editor", "Can edit documents")
        await svc.check_android_permission("CAMERA")
    """

    def __init__(self, config: Optional[PermissionConfig] = None):
        super().__init__(name="jarvis_permissions", version="1.0.0")
        self.config = config or PermissionConfig()
        self.role_manager: Optional[RoleManager] = None
        self.permission_checker: Optional[PermissionChecker] = None
        self.android_permissions: Optional[AndroidPermissionManager] = None
        self._start_time = 0.0

    async def initialize(self) -> bool:
        self._start_time = time.time()
        try:
            self.role_manager = RoleManager(self.config)
            self.permission_checker = PermissionChecker(self.role_manager, self.config)
            self.android_permissions = AndroidPermissionManager()
            self._metrics.reset()
            self._initialized = True
            logger.info("PermissionManagerService initialized")
            return True
        except Exception as e:
            logger.error("PermissionManagerService init failed: %s", e)
            return False

    async def shutdown(self) -> None:
        logger.info("PermissionManagerService shutting down...")
        self._initialized = False

    async def has_permission(
        self, user_id: str, resource: str, action: str, scope: str = "global"
    ) -> PermissionCheckResult:
        """Check if a user has a permission.

        Args:
            user_id: User identifier.
            resource: Resource identifier.
            action: Action to check.
            scope: Scope context.

        Returns:
            PermissionCheckResult.
        """
        if not self.permission_checker:
            raise RuntimeError("PermissionManagerService not initialized")
        t0 = time.perf_counter()
        result = self.permission_checker.has_permission(user_id, resource, action, scope)
        elapsed = (time.perf_counter() - t0) * 1000
        self._metrics.counter("permission_checks", 1)
        self._metrics.histogram("check_time_ms", elapsed)
        if result.is_granted:
            self._metrics.counter("permissions_granted", 1)
        else:
            self._metrics.counter("permissions_denied", 1)
        return result

    async def create_role(
        self,
        name: str,
        description: str = "",
        permissions: Optional[List[Permission]] = None,
        priority: int = 0,
        is_default: bool = False,
        parent_role: str = "",
    ) -> Role:
        """Create a new role.

        Args:
            name: Role name.
            description: Role description.
            permissions: List of Permission objects.
            priority: Priority value.
            is_default: Whether default role.
            parent_role: Parent role name.

        Returns:
            The created Role.
        """
        if not self.role_manager:
            raise RuntimeError("PermissionManagerService not initialized")
        role = self.role_manager.create_role(
            name=name,
            description=description,
            permissions=permissions,
            priority=priority,
            is_default=is_default,
            parent_role=parent_role,
        )
        self._metrics.counter("roles_created", 1)
        if self.permission_checker:
            self.permission_checker.invalidate_cache()
        return role

    async def update_role(self, name: str, **updates) -> Optional[Role]:
        """Update a role.

        Args:
            name: Role name.
            **updates: Fields to update.

        Returns:
            Updated Role or None.
        """
        if not self.role_manager:
            raise RuntimeError("PermissionManagerService not initialized")
        role = self.role_manager.update_role(name, **updates)
        if role and self.permission_checker:
            self.permission_checker.invalidate_cache()
        return role

    async def delete_role(self, name: str) -> bool:
        """Delete a role.

        Args:
            name: Role name.

        Returns:
            True if deleted.
        """
        if not self.role_manager:
            raise RuntimeError("PermissionManagerService not initialized")
        result = self.role_manager.delete_role(name)
        if result and self.permission_checker:
            self.permission_checker.invalidate_cache()
        return result

    async def get_role(self, name: str) -> Optional[Role]:
        """Get a role by name.

        Args:
            name: Role name.

        Returns:
            Role or None.
        """
        if not self.role_manager:
            raise RuntimeError("PermissionManagerService not initialized")
        return self.role_manager.get_role(name)

    async def list_roles(self) -> List[str]:
        """List all role names.

        Returns:
            List of role name strings.
        """
        if not self.role_manager:
            raise RuntimeError("PermissionManagerService not initialized")
        return [r.name for r in self.role_manager.list_roles()]

    async def assign_role(self, user_id: str, role_name: str) -> bool:
        """Assign a role to a user.

        Args:
            user_id: User identifier.
            role_name: Role name.

        Returns:
            True if assigned.
        """
        if not self.role_manager:
            raise RuntimeError("PermissionManagerService not initialized")
        result = self.role_manager.assign_role(user_id, role_name)
        if result and self.permission_checker:
            self.permission_checker.invalidate_cache(user_id)
        self._metrics.counter("role_assignments", 1)
        return result

    async def remove_role(self, user_id: str, role_name: str) -> bool:
        """Remove a role from a user.

        Args:
            user_id: User identifier.
            role_name: Role name.

        Returns:
            True if removed.
        """
        if not self.role_manager:
            raise RuntimeError("PermissionManagerService not initialized")
        result = self.role_manager.remove_role(user_id, role_name)
        if result and self.permission_checker:
            self.permission_checker.invalidate_cache(user_id)
        return result

    async def get_user_permissions(self, user_id: str) -> Optional[UserPermissions]:
        """Get a user's permissions.

        Args:
            user_id: User identifier.

        Returns:
            UserPermissions or None.
        """
        if not self.role_manager:
            raise RuntimeError("PermissionManagerService not initialized")
        return self.role_manager.get_user_permissions(user_id)

    async def reset_user(self, user_id: str) -> bool:
        """Reset a user's permissions to default.

        Args:
            user_id: User identifier.

        Returns:
            True if reset.
        """
        if not self.role_manager:
            raise RuntimeError("PermissionManagerService not initialized")
        result = self.role_manager.reset_user(user_id)
        if self.permission_checker:
            self.permission_checker.invalidate_cache(user_id)
        return result

    async def add_custom_permission(self, user_id: str, permission: Permission) -> bool:
        """Add a custom permission for a user.

        Args:
            user_id: User identifier.
            permission: Permission to add.

        Returns:
            True if added.
        """
        if not self.role_manager:
            raise RuntimeError("PermissionManagerService not initialized")
        result = self.role_manager.add_custom_permission(user_id, permission)
        if result and self.permission_checker:
            self.permission_checker.invalidate_cache(user_id)
        return result

    # ── Android Runtime Permissions ─────────────────────────────────

    async def check_android_permission(self, permission_group: str) -> AndroidPermissionState:
        """Check the state of an Android runtime permission.

        Args:
            permission_group: The permission group (e.g., "CAMERA").

        Returns:
            The current AndroidPermissionState.
        """
        if not self.android_permissions:
            raise RuntimeError("PermissionManagerService not initialized")
        self._metrics.counter("android_permission_checks", 1)
        return self.android_permissions.check_permission(permission_group)

    async def request_android_permission(self, permission_group: str) -> bool:
        """Request an Android runtime permission (simulated async grant).

        Args:
            permission_group: The permission group.

        Returns:
            True if granted.
        """
        if not self.android_permissions:
            raise RuntimeError("PermissionManagerService not initialized")
        granted = self.android_permissions.request_permission(permission_group)
        self._metrics.counter("android_permission_requests", 1)
        return granted

    async def get_granted_android_permissions(self) -> List[AndroidPermission]:
        """Get all granted Android permissions.

        Returns:
            List of granted AndroidPermission objects.
        """
        if not self.android_permissions:
            raise RuntimeError("PermissionManagerService not initialized")
        return self.android_permissions.get_granted_permissions()

    async def get_denied_android_permissions(self) -> List[AndroidPermission]:
        """Get all denied or blocked Android permissions.

        Returns:
            List of denied/blocked AndroidPermission objects.
        """
        if not self.android_permissions:
            raise RuntimeError("PermissionManagerService not initialized")
        return self.android_permissions.get_denied_permissions()

    async def get_android_permission_state(self, permission_group: str) -> Optional[AndroidPermission]:
        """Get the full Android permission object with state details.

        Args:
            permission_group: The permission group.

        Returns:
            AndroidPermission or None.
        """
        if not self.android_permissions:
            raise RuntimeError("PermissionManagerService not initialized")
        return self.android_permissions.get_permission_state(permission_group)

    async def list_android_permissions(self) -> List[AndroidPermission]:
        """List all tracked Android permissions.

        Returns:
            List of all AndroidPermission objects.
        """
        if not self.android_permissions:
            raise RuntimeError("PermissionManagerService not initialized")
        return self.android_permissions.list_permissions()

    async def grant_android_permission(self, permission_group: str) -> bool:
        """Manually grant an Android permission.

        Args:
            permission_group: The permission group.

        Returns:
            True if granted.
        """
        if not self.android_permissions:
            raise RuntimeError("PermissionManagerService not initialized")
        return self.android_permissions.grant_permission(permission_group)

    async def deny_android_permission(self, permission_group: str) -> bool:
        """Manually deny an Android permission.

        Args:
            permission_group: The permission group.

        Returns:
            True if denied.
        """
        if not self.android_permissions:
            raise RuntimeError("PermissionManagerService not initialized")
        return self.android_permissions.deny_permission(permission_group)

    async def reset_android_permission(self, permission_group: str) -> bool:
        """Reset an Android permission to never_asked.

        Args:
            permission_group: The permission group.

        Returns:
            True if reset.
        """
        if not self.android_permissions:
            raise RuntimeError("PermissionManagerService not initialized")
        return self.android_permissions.reset_permission(permission_group)

    # ── Fallback-Aware Permission Check ────────────────────────────

    async def check_with_fallback(
        self, user_id: str, resource: str, action: str, scope: str = "global"
    ) -> PermissionCheckResult:
        """Check permission and include a fallback action if denied.

        Args:
            user_id: User identifier.
            resource: Resource identifier.
            action: Action to check.
            scope: Scope context.

        Returns:
            PermissionCheckResult with fallback_action set.
        """
        result = await self.has_permission(user_id, resource, action, scope)
        return result

    async def health(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        role_count = len(self.role_manager.list_roles()) if self.role_manager else 0
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "service_name": self.name,
            "version": self.version,
            "initialized": self._initialized,
            "uptime_seconds": round(uptime, 1),
            "roles_configured": role_count,
        }

    async def stats(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        role_count = len(self.role_manager.list_roles()) if self.role_manager else 0
        return {
            "service": self.name,
            "version": self.version,
            "uptime_seconds": round(uptime, 1),
            "roles_configured": role_count,
            "metrics": self._metrics.snapshot(),
        }
