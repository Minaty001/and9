"""
Plugin SDK — Data Models.

PluginManifest, PluginHook, PluginState.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class PluginManifest:
    """Plugin manifest/metadata."""

    def __init__(self, plugin_id: str, name: str, version: str,
                 description: str = "", author: str = "",
                 min_api_version: str = "1.0.0",
                 dependencies: Optional[List[str]] = None,
                 hooks: Optional[List[str]] = None,
                 permissions: Optional[List[str]] = None,
                 entry_point: str = "main",
                 enabled: bool = True):
        self.id = plugin_id
        self.name = name
        self.version = version
        self.description = description
        self.author = author
        self.min_api_version = min_api_version
        self.dependencies = dependencies or []
        self.hooks = hooks or []
        self.permissions = permissions or []
        self.entry_point = entry_point
        self.enabled = enabled


class PluginHook:
    """A hook registered by a plugin."""

    def __init__(self, hook_type: str, priority: int = 100,
                 handler: str = "", plugin_id: str = ""):
        self.hook_type = hook_type
        self.priority = priority
        self.handler = handler
        self.plugin_id = plugin_id


class PluginState:
    """Runtime state of a plugin with lifecycle tracking."""

    VALID_STATUSES = {
        "installed", "enabled", "disabled", "updating",
        "blocked", "error", "loaded", "unloaded",
    }

    def __init__(self, status: str = "installed",
                 loaded_at: Optional[datetime] = None,
                 error: str = "", execution_count: int = 0,
                 last_execution: Optional[datetime] = None,
                 lifecycle_events: Optional[List[Dict[str, Any]]] = None):
        self.status = status if status in self.VALID_STATUSES else "installed"
        self.loaded_at = loaded_at or datetime.now(timezone.utc)
        self.error = error
        self.execution_count = execution_count
        self.last_execution = last_execution
        self.lifecycle_events = lifecycle_events or []
