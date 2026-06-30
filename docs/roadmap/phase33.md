# Phase 33: Permissions

## Purpose
Role-based permission checking with user-role assignments, custom permissions, scoped access, and Android runtime permission tracking. `PermissionChecker` evaluates whether a user can perform an action on a resource using role-based checks first, then custom permissions, with result caching. `RoleManager` provides CRUD for roles, permissions, and user-role assignments with built-in roles (owner, admin, user, guest). `AndroidPermissionManager` simulates Android runtime permission states (granted, denied, never_asked, blocked) with permission groups.

## Architecture
```
PermissionChecker
  ├── has_permission(user_id, resource, action, scope) → PermissionCheckResult
  ├── invalidate_cache(user_id) / clear()
  └── Internal: role check → owner override → custom permission → fallback

RoleManager
  ├── create_role(name, description, permissions, priority) → Role
  ├── assign_role(user_id, role_name) / unassign_role(user_id, role_name)
  ├── get_user_roles(user_id) → List[Role]
  ├── get_role_permissions(role_name) → List[Permission]
  ├── set_user_permissions(user_id, UserPermissions)
  └── Built-in: owner, admin, user, guest

AndroidPermissionManager
  ├── request_permission(name) → AndroidPermissionState
  ├── get_permission_state(name) → state
  ├── grant_permission(name) / deny_permission(name)
  └── get_all_permissions() → List[AndroidPermission]

Models: Permission, Role, UserPermissions, PermissionCheckResult, AndroidPermission
```

## Code
```python
class PermissionChecker:
    def has_permission(self, user_id, resource, action, scope="global") -> PermissionCheckResult:
        cache_key = f"{user_id}:{resource}:{action}:{scope}"
        cached = self._cache.get(cache_key)
        if cached: return cached[0]

        result = self._check_roles(user_id, resource, action, scope)
        if not result.is_granted:
            result = self._check_custom(user_id, resource, action, scope)
        if not result.is_granted:
            result.fallback_action = self._determine_fallback(resource, action)
        self._cache[cache_key] = (result, time.time() + self._cache_ttl_seconds)
        return result

class RoleManager:
    def assign_role(self, user_id, role_name) -> bool:
        if role_name not in self._roles: return False
        if user_id not in self._user_permissions:
            self._user_permissions[user_id] = UserPermissions(user_id=user_id)
        if role_name not in self._user_permissions[user_id].roles:
            self._user_permissions[user_id].roles.append(role_name)
        return True
```

## Location
`app/core/permissions/` — permission checker, role manager, Android permission manager, models
