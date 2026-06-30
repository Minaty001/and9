"""
Permission Checker.

Checks user permissions against roles and custom permissions
with caching for performance.
"""

from __future__ import annotations

import time
import logging
from typing import Dict, List, Optional, Tuple

from .models import Permission, Role, PermissionCheckResult
from .role_manager import RoleManager

logger = logging.getLogger(__name__)


class PermissionChecker:
    """Checks whether a user has a specific permission.

    Uses role-based checks first, then custom permissions, then
    scoped conditions. Caches results for performance.

    Usage:
        checker = PermissionChecker(role_manager)
        result = checker.has_permission("user123", "document", "read")
        if result.is_granted:
            print("Access granted")
    """

    def __init__(self, role_manager: RoleManager,
                 cache_ttl_seconds: int = 60,
                 enable_scoped_permissions: bool = True,
                 enable_owner_override: bool = True):
        self.role_manager = role_manager
        self._cache_ttl_seconds = cache_ttl_seconds
        self._enable_scoped_permissions = enable_scoped_permissions
        self._enable_owner_override = enable_owner_override
        self._cache: Dict[str, Tuple[PermissionCheckResult, float]] = {}

    def has_permission(
        self, user_id: str, resource: str, action: str, scope: str = "global"
    ) -> PermissionCheckResult:
        """Check if a user has permission to perform an action on a resource.

        Args:
            user_id: User identifier.
            resource: Resource identifier.
            action: Action to check (read/write/execute/admin/delete).
            scope: Scope context.

        Returns:
            PermissionCheckResult.
        """
        cache_key = f"{user_id}:{resource}:{action}:{scope}"
        now = time.time()

        cached = self._cache.get(cache_key)
        if cached and now < cached[1]:
            return cached[0]

        t0 = time.perf_counter()

        if self._enable_owner_override:
            owner_check = self._check_owner(user_id, resource, action)
            if owner_check is not None:
                elapsed = (time.perf_counter() - t0) * 1000
                owner_check.check_time_ms = round(elapsed, 2)
                self._cache[cache_key] = (owner_check, now + self._cache_ttl_seconds)
                return owner_check

        result = self._check_roles(user_id, resource, action, scope)
        if result.is_granted:
            elapsed = (time.perf_counter() - t0) * 1000
            result.check_time_ms = round(elapsed, 2)
            self._cache[cache_key] = (result, now + self._cache_ttl_seconds)
            return result

        result = self._check_custom(user_id, resource, action, scope)
        elapsed = (time.perf_counter() - t0) * 1000
        result.check_time_ms = round(elapsed, 2)

        if not result.is_granted:
            result.fallback_action = self._determine_fallback(resource, action)

        self._cache[cache_key] = (result, now + self._cache_ttl_seconds)
        return result

    def _check_owner(self, user_id: str, resource: str, action: str) -> Optional[PermissionCheckResult]:
        roles = self.role_manager.get_user_roles(user_id)
        for role in roles:
            if role.name == "owner":
                return PermissionCheckResult(
                    is_granted=True,
                    matched_role="owner",
                    reason="Owner override: full access granted",
                )
        return None

    def _check_roles(self, user_id: str, resource: str, action: str, scope: str) -> PermissionCheckResult:
        roles = self.role_manager.get_user_roles(user_id)
        sorted_roles = sorted(roles, key=lambda r: r.priority, reverse=True)

        for role in sorted_roles:
            permissions = self.role_manager.get_role_permissions(role.name)
            for perm in permissions:
                if self._permission_matches(perm, resource, action, scope):
                    if perm.grant:
                        return PermissionCheckResult(
                            is_granted=True,
                            matched_permission=perm,
                            matched_role=role.name,
                            reason=f"Granted by role '{role.name}': {perm.action} on {perm.resource}",
                        )

        return PermissionCheckResult(is_granted=False, reason="No matching role permission found")

    def _check_custom(self, user_id: str, resource: str, action: str, scope: str) -> PermissionCheckResult:
        user_perms = self.role_manager.get_user_permissions(user_id)
        if not user_perms:
            return PermissionCheckResult(is_granted=False, reason="No custom permissions found")

        for perm in user_perms.custom_permissions:
            if self._permission_matches(perm, resource, action, scope):
                if perm.grant:
                    return PermissionCheckResult(
                        is_granted=True,
                        matched_permission=perm,
                        matched_role="custom",
                        reason=f"Granted by custom permission: {perm.action} on {perm.resource}",
                    )

        return PermissionCheckResult(is_granted=False, reason="No matching custom permission")

    def _determine_fallback(self, resource: str, action: str) -> str:
        runtime_permission_resources = {
            "camera", "microphone", "location", "contacts",
            "storage", "sms", "phone", "calendar", "sensors",
        }
        if resource.lower() in runtime_permission_resources:
            return "ask"
        if action in ("admin", "delete", "execute"):
            return "degrade"
        if action in ("write",):
            return "skip"
        if action in ("read",):
            return "mock"
        return "none"

    def _permission_matches(self, perm: Permission, resource: str, action: str, scope: str) -> bool:
        if perm.resource == "*" or perm.resource == resource:
            pass
        elif perm.resource == "self":
            pass
        elif perm.resource != resource:
            return False

        if perm.action == "admin":
            pass
        elif perm.action != action:
            return False

        if self._enable_scoped_permissions:
            if perm.scope != "global" and perm.scope != scope:
                if perm.scope == "user" and scope != "user" and scope != "session":
                    return False
                if perm.scope == "session" and scope != "session":
                    return False
                if perm.scope == "resource" and scope != "resource" and scope != "global":
                    return False

        return True

    def invalidate_cache(self, user_id: Optional[str] = None) -> None:
        if user_id:
            keys_to_delete = [k for k in self._cache if k.startswith(f"{user_id}:")]
            for k in keys_to_delete:
                del self._cache[k]
        else:
            self._cache.clear()

    def clear(self) -> None:
        self._cache.clear()
