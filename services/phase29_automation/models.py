"""
Phase 29 — Automation Engine Models.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Trigger(BaseModel):
    """A trigger configuration."""

    type: str = Field(..., description="Trigger type: time/schedule/event/context/system")
    params: Dict[str, Any] = Field(default_factory=dict, description="Trigger parameters")
    cooldown_remaining: int = Field(default=0, ge=0, description="Cooldown remaining in seconds")


class Action(BaseModel):
    """An action to execute."""

    type: str = Field(..., description="Action type: notify/command/system/message/api")
    params: Dict[str, Any] = Field(default_factory=dict, description="Action parameters")
    success: bool = Field(default=False, description="Whether execution succeeded")
    error: str = Field(default="", description="Error message if failed")


class AutomationRule(BaseModel):
    """An automation rule (if-this-then-that)."""

    id: str = Field(..., description="Unique rule identifier")
    name: str = Field(..., description="Rule name")
    description: str = Field(default="", description="Rule description")
    trigger: Dict[str, Any] = Field(..., description="Trigger config: {type: ..., params: {...}}")
    conditions: List[Dict[str, Any]] = Field(default_factory=list, description="Condition list")
    actions: List[Dict[str, Any]] = Field(..., description="Action list: [{type: ..., params: {...}}]")
    is_active: bool = Field(default=True, description="Whether rule is active")
    isenabled: bool = Field(default=True, description="Whether rule is enabled")
    priority: int = Field(default=0, ge=-10, le=10, description="Rule priority")
    cooldown_seconds: int = Field(default=60, ge=0, description="Cooldown between executions")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_triggered: Optional[datetime] = Field(default=None)
    execution_count: int = Field(default=0, ge=0, description="Times rule executed")
    tags: List[str] = Field(default_factory=list, description="Tags")


class RuleExecution(BaseModel):
    """A record of a rule execution."""

    rule_id: str = Field(..., description="Rule identifier")
    rule_name: str = Field(..., description="Rule name")
    triggered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    trigger_type: str = Field(..., description="Type of trigger that fired")
    actions_taken: List[Dict[str, Any]] = Field(default_factory=list, description="Actions taken")
    success: bool = Field(default=True, description="Whether execution succeeded")
    duration_ms: float = Field(default=0.0, description="Execution duration in ms")
    error: str = Field(default="", description="Error message if failed")
    rollback_performed: bool = Field(default=False, description="Whether rollback was performed")
