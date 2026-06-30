"""
Tests for Phase 32 — Permission Manager.
"""

import pytest
from services.phase32_permissions import (
    PermissionConfig,
    Permission,
    Role,
    UserPermissions,
    PermissionCheckResult,
    RoleManager,
    PermissionChecker,
    PermissionManagerService,
)


class TestRoleManager:
    """Verify role CRUD and user role assignments."""

    def test_default_roles_exist(self):
        mgr = RoleManager()
        roles = mgr.list_roles()
        assert len(roles) >= 3

    def test_create_role(self):
        mgr = RoleManager()
        role = mgr.create_role("editor", "Can edit", priority=30)
        assert role.name == "editor"
        assert mgr.get_role("editor") is not None

    def test_update_role(self):
        mgr = RoleManager()
        mgr.create_role("editor", "Old description")
        updated = mgr.update_role("editor", description="New description")
        assert updated is not None
        assert updated.description == "New description"

    def test_delete_role(self):
        mgr = RoleManager()
        mgr.create_role("temp", "Temporary")
        assert mgr.delete_role("temp") is True
        assert mgr.get_role("temp") is None

    def test_delete_nonexistent(self):
        mgr = RoleManager()
        assert mgr.delete_role("nonexistent") is False

    def test_assign_role(self):
        mgr = RoleManager()
        assert mgr.assign_role("user1", "admin") is True
        roles = mgr.get_user_roles("user1")
        assert any(r.name == "admin" for r in roles)

    def test_assign_nonexistent_role(self):
        mgr = RoleManager()
        assert mgr.assign_role("user1", "nonexistent") is False

    def test_remove_role(self):
        mgr = RoleManager()
        mgr.assign_role("user1", "admin")
        assert mgr.remove_role("user1", "admin") is True

    def test_get_user_roles_with_default(self):
        mgr = RoleManager()
        roles = mgr.get_user_roles("newuser")
        assert len(roles) >= 1  # should get default role

    def test_get_role_permissions(self):
        mgr = RoleManager()
        perms = mgr.get_role_permissions("admin")
        assert len(perms) > 0

    def test_reset_user(self):
        mgr = RoleManager()
        mgr.assign_role("user1", "admin")
        mgr.reset_user("user1")
        roles = mgr.get_user_roles("user1")
        assert all(r.is_default or r.name == "user" for r in roles)

    def test_add_custom_permission(self):
        mgr = RoleManager()
        perm = Permission(resource="doc", action="read")
        assert mgr.add_custom_permission("user1", perm) is True


class TestPermissionChecker:
    """Verify permission checking logic."""

    def test_admin_has_permission(self):
        mgr = RoleManager()
        checker = PermissionChecker(mgr)
        mgr.assign_role("admin_user", "admin")
        result = checker.has_permission("admin_user", "system", "read")
        assert result.is_granted is True

    def test_owner_has_full_access(self):
        mgr = RoleManager()
        checker = PermissionChecker(mgr)
        mgr.assign_role("owner_user", "owner")
        result = checker.has_permission("owner_user", "anything", "admin")
        assert result.is_granted is True

    def test_user_no_permission(self):
        mgr = RoleManager()
        checker = PermissionChecker(mgr)
        result = checker.has_permission("regular_user", "system", "admin")
        # Regular user shouldn't have admin on system
        assert result.is_granted is False

    def test_custom_permission_granted(self):
        mgr = RoleManager()
        checker = PermissionChecker(mgr)
        perm = Permission(resource="special", action="execute")
        mgr.add_custom_permission("user1", perm)
        result = checker.has_permission("user1", "special", "execute")
        assert result.is_granted is True

    def test_cache_invalidation(self):
        mgr = RoleManager()
        checker = PermissionChecker(mgr)
        result1 = checker.has_permission("user1", "resource", "read")
        checker.invalidate_cache("user1")
        result2 = checker.has_permission("user1", "resource", "read")
        assert result1.is_granted == result2.is_granted

    def test_invalidate_all(self):
        mgr = RoleManager()
        checker = PermissionChecker(mgr)
        checker.has_permission("user1", "resource", "read")
        checker.invalidate_cache()
        checker.has_permission("user2", "resource", "read")
        # Should not raise


class TestPermissionManagerService:
    """Verify service wrapper."""

    @pytest.mark.asyncio
    async def test_initialize(self):
        svc = PermissionManagerService()
        assert await svc.initialize() is True

    @pytest.mark.asyncio
    async def test_create_role(self):
        svc = PermissionManagerService()
        await svc.initialize()
        role = await svc.create_role("moderator", "Can moderate")
        assert role.name == "moderator"

    @pytest.mark.asyncio
    async def test_list_roles(self):
        svc = PermissionManagerService()
        await svc.initialize()
        roles = await svc.list_roles()
        assert len(roles) >= 3

    @pytest.mark.asyncio
    async def test_has_permission(self):
        svc = PermissionManagerService()
        await svc.initialize()
        await svc.assign_role("user1", "admin")
        result = await svc.has_permission("user1", "system", "read")
        assert result.is_granted is True

    @pytest.mark.asyncio
    async def test_assign_remove_role(self):
        svc = PermissionManagerService()
        await svc.initialize()
        assert await svc.assign_role("user1", "admin") is True
        assert await svc.remove_role("user1", "admin") is True

    @pytest.mark.asyncio
    async def test_get_user_permissions(self):
        svc = PermissionManagerService()
        await svc.initialize()
        perms = await svc.get_user_permissions("user1")
        assert perms is not None
        assert perms.user_id == "user1"

    @pytest.mark.asyncio
    async def test_reset_user(self):
        svc = PermissionManagerService()
        await svc.initialize()
        assert await svc.reset_user("user1") is True

    @pytest.mark.asyncio
    async def test_health(self):
        svc = PermissionManagerService()
        await svc.initialize()
        health = await svc.health()
        assert health["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_shutdown(self):
        svc = PermissionManagerService()
        await svc.initialize()
        await svc.shutdown()
        assert not svc.is_initialized()
