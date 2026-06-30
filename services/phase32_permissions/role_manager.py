"""
Phase 32 — Role Manager.

CRUD for roles and user role assignments.
"""

from __future__ import annotations

import uuid
import logging
from typing import Dict, List, Optional

from .config import PermissionConfig
from .models import Role, Permission, UserPermissions

logger = logging.getLogger(__name__)


class RoleManager:
    """Manages roles and user-role assignments.

    Usage:
        mgr = RoleManager(config)
        role = mgr.create_role("admin", "Administrator", priority=100)
        mgr.assign_role("user123", "admin")
        roles = mgr.get_user_roles("user123")
    """

    def __init__(self, config: Optional[PermissionConfig] = None):
        self.config = config or PermissionConfig()
        self._roles: Dict[str, Role] = {}
        self._user_permissions: Dict[str, UserPermissions] = {}

        # Create default roles
        self._create_default_roles()

    def _create_default_roles(self) -> None:
        """Create built-in default roles."""
        # Owner role
        owner_role = Role(
            id=self._role_id("owner"),
            name="owner",
            description="Full system access",
            permissions=[
                Permission(resource="*", action="admin", scope="global", grant=True),
                Permission(resource="*", action="write", scope="global", grant=True),
                Permission(resource="*", action="read", scope="global", grant=True),
                Permission(resource="*", action="delete", scope="global", grant=True),
                Permission(resource="*", action="execute", scope="global", grant=True),
            ],
            priority=100,
            is_default=False,
        )
        self._roles["owner"] = owner_role

        # Admin role
        admin_role = Role(
            id=self._role_id("admin"),
            name="admin",
            description="Administrative access",
            permissions=[
                Permission(resource="*", action="read", scope="global", grant=True),
                Permission(resource="*", action="write", scope="global", grant=True),
                Permission(resource="*", action="execute", scope="global", grant=True),
                Permission(resource="system", action="admin", scope="global", grant=True),
            ],
            priority=50,
            is_default=False,
        )
        self._roles["admin"] = admin_role

        # User role (default)
        user_role = Role(
            id=self._role_id("user"),
            name="user",
            description="Standard user access",
            permissions=[
                Permission(resource="self", action="read", scope="user", grant=True),
                Permission(resource="self", action="write", scope="user", grant=True),
                Permission(resource="public", action="read", scope="global", grant=True),
            ],
            priority=10,
            is_default=True,
        )
        self._roles["user"] = user_role

    def _role_id(self, name: str) -> str:
        return f"role_{name}"

    def create_role(
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
            permissions: List of Permission objects or strings.
            priority: Priority (higher = more precedence).
            is_default: Whether this is a default role.
            parent_role: Parent role name.

        Returns:
            The created Role.
        """
        # Convert string permissions to Permission objects
        # A string like 'read' becomes Permission(resource='*', action='read')
        converted_perms: List[Permission] = []
        if permissions:
            for perm in permissions:
                if isinstance(perm, str):
                    converted_perms.append(Permission(resource='*', action=perm))
                else:
                    converted_perms.append(perm)
        else:
            converted_perms = []

        role = Role(
            id=self._role_id(name),
            name=name,
            description=description,
            permissions=converted_perms,
            priority=priority,
            is_default=is_default,
            parent_role=parent_role,
        )
        self._roles[role.name] = role
        logger.debug("Created role: %s", name)
        return role

    def update_role(self, name: str, **updates) -> Optional[Role]:
        """Update an existing role.

        Args:
            name: Role name to update.
            **updates: Fields to update.

        Returns:
            Updated Role or None if not found.
        """
        if name not in self._roles:
            return None
        role = self._roles[name]
        for key, value in updates.items():
            if hasattr(role, key):
                setattr(role, key, value)
        logger.debug("Updated role: %s", name)
        return role

    def delete_role(self, name: str) -> bool:
        """Delete a role.

        Args:
            name: Role name.

        Returns:
            True if deleted.
        """
        if name not in self._roles:
            return False
        del self._roles[name]
        logger.debug("Deleted role: %s", name)
        return True

    def get_role(self, name: str) -> Optional[Role]:
        """Get a role by name.

        Args:
            name: Role name.

        Returns:
            Role or None.
        """
        role = self._roles.get(name)
        if role:
            return role
        # Try by id
        for r in self._roles.values():
            if r.id == name:
                return r
        return None

    def list_roles(self) -> List[Role]:
        """List all roles.

        Returns:
            List of Role objects.
        """
        return list(self._roles.values())

    def assign_role(self, user_id: str, role_name: str) -> bool:
        """Assign a role to a user.

        Args:
            user_id: User identifier.
            role_name: Role name to assign.

        Returns:
            True if assigned.
        """
        if role_name not in self._roles:
            return False
        if user_id not in self._user_permissions:
            self._user_permissions[user_id] = UserPermissions(user_id=user_id)
        perms = self._user_permissions[user_id]
        if role_name not in perms.roles:
            if len(perms.roles) >= self.config.max_roles_per_user:
                return False
            perms.roles.append(role_name)
        return True

    def remove_role(self, user_id: str, role_name: str) -> bool:
        """Remove a role from a user.

        Args:
            user_id: User identifier.
            role_name: Role name.

        Returns:
            True if removed.
        """
        if user_id not in self._user_permissions:
            return False
        perms = self._user_permissions[user_id]
        if role_name in perms.roles:
            perms.roles.remove(role_name)
            return True
        return False

    def get_user_roles(self, user_id: str) -> List[Role]:
        """Get all roles assigned to a user.

        Args:
            user_id: User identifier.

        Returns:
            List of Role objects.
        """
        if user_id not in self._user_permissions:
            return [self._roles.get(self.config.default_role, self._roles.get("user"))]
        role_names = self._user_permissions[user_id].roles
        result = []
        for name in role_names:
            r = self._roles.get(name)
            if r:
                result.append(r)
        # Always include default role
        default = self._roles.get(self.config.default_role)
        if default and default not in result:
            result.append(default)
        return result

    def get_role_permissions(self, role_name: str) -> List[Permission]:
        """Get all permissions for a role, including inherited.

        Args:
            role_name: Role name.

        Returns:
            List of Permission objects.
        """
        role = self._roles.get(role_name)
        if not role:
            return []

        permissions = list(role.permissions)

        # Inherit from parent
        if role.parent_role and role.parent_role in self._roles:
            parent_perms = self.get_role_permissions(role.parent_role)
            permissions.extend(parent_perms)

        return permissions

    def get_user_permissions(self, user_id: str) -> Optional[UserPermissions]:
        """Get the UserPermissions record for a user.

        Args:
            user_id: User identifier.

        Returns:
            UserPermissions or None.
        """
        if user_id not in self._user_permissions:
            # Create with default role
            perms = UserPermissions(user_id=user_id)
            default = self.config.default_role
            if default in self._roles:
                perms.roles.append(default)
            self._user_permissions[user_id] = perms
        return self._user_permissions[user_id]

    def reset_user(self, user_id: str) -> bool:
        """Reset a user's permissions to default.

        Args:
            user_id: User identifier.

        Returns:
            True if reset.
        """
        self._user_permissions[user_id] = UserPermissions(
            user_id=user_id,
            roles=[self.config.default_role],
        )
        return True

    def add_custom_permission(self, user_id: str, permission: Permission) -> bool:
        """Add a custom permission for a user.

        Args:
            user_id: User identifier.
            permission: Permission to add.

        Returns:
            True if added.
        """
        perms = self.get_user_permissions(user_id)
        perms.custom_permissions.append(permission)
        return True

    def clear(self) -> None:
        """Clear all data (for testing)."""
        self._roles.clear()
        self._user_permissions.clear()
        self._create_default_roles()
