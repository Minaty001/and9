"""
Phase 39 — Plugin SDK Models.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PluginManifest(BaseModel):
    """Plugin manifest/metadata."""

    id: str = Field(..., description="Unique plugin identifier")
    name: str = Field(..., description="Human-readable plugin name")
    version: str = Field(..., description="Plugin version string")
    description: str = Field(default="", description="Plugin description")
    author: str = Field(default="", description="Plugin author")
    min_api_version: str = Field(default="1.0.0", description="Minimum API version required")
    dependencies: List[str] = Field(default_factory=list, description="Plugin dependency IDs")
    hooks: List[str] = Field(default_factory=list, description="Hook types this plugin implements")
    permissions: List[str] = Field(default_factory=list, description="Required permissions")
    entry_point: str = Field(default="main", description="Plugin entry point function")
    enabled: bool = Field(default=True, description="Whether the plugin is enabled")


class PluginHook(BaseModel):
    """A hook registered by a plugin."""

    hook_type: str = Field(..., description="Hook type: on_initialize/on_shutdown/on_intent/on_response/on_error/on_turn")
    priority: int = Field(default=100, description="Execution priority (lower = first)")
    handler: str = Field(..., description="Handler function name")
    plugin_id: str = Field(..., description="ID of the owning plugin")


class PluginState(BaseModel):
    """Runtime state of a plugin with lifecycle tracking."""

    status: str = Field(
        default="installed",
        description="Plugin lifecycle status: "
        "installed/enabled/disabled/updating/blocked/error/loaded/unloaded",
    )
    loaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error: str = Field(default="", description="Error message if status is error")
    execution_count: int = Field(default=0, description="Number of times executed")
    last_execution: Optional[datetime] = Field(default=None, description="Last execution timestamp")
    lifecycle_events: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of lifecycle transition events, each a dict with "
        "from_state, to_state, timestamp, reason",
    )
