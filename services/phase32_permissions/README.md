# Phase 32: Permission Manager

## Overview

Granular permissions, roles, resource scoping, and permission checking with owner/admin/user model.

## Architecture

```
┌──────────────────────┐
│   RoleManager         │  ◄── CRUD roles, assign/remove user roles
│   ┌────────────────┐  │      Default roles: owner, admin, user
│   │ Role Store      │  │
│   └────────────────┘  │
└─────────┬────────────┘
          │
          ▼
┌──────────────────────┐
│ PermissionChecker     │  ◄── Role-based → custom → scoped check
│ ┌──────────────────┐  │      Cached results with TTL
│ │ Cache (TTL)       │  │
│ └──────────────────┘  │
└─────────┬────────────┘
          │
          ▼
┌──────────────────────┐
│ PermissionManagerService│
└──────────────────────┘
```

## Components

- **RoleManager**: Create, update, delete roles. Assign/remove roles for users. Role inheritance (parent_role). Default roles: owner, admin, user.
- **PermissionChecker**: Check permissions by role (sorted by priority), then custom permissions. Owner override. Cached results with configurable TTL.
- **Permission**: Resource + action + scope + conditions + grant/deny.
- **Role**: Name, permissions, priority, parent_role, is_default.

## Usage

```python
from services.phase32_permissions import PermissionManagerService
svc = PermissionManagerService()
await svc.initialize()

# Check permission
result = await svc.has_permission("user123", "document", "read")
if result.is_granted:
    print(f"Granted by: {result.matched_role}")

# Manage roles
await svc.create_role("editor", "Can edit documents",
    permissions=[Permission(resource="doc", action="write")])
await svc.assign_role("user123", "editor")
```

## Test Coverage

22+ tests covering all components and the service wrapper.
