"""
Phase 28 — Scheduler Models.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ScheduledItem(BaseModel):
    """A scheduled item (reminder, recurring task, alarm, calendar)."""

    id: str = Field(..., description="Unique item identifier")
    type: str = Field(..., description="Type: reminder/recurring/alarm/calendar")
    title: str = Field(..., description="Item title")
    description: str = Field(default="", description="Item description")
    trigger_time: datetime = Field(..., description="When to trigger")
    end_time: Optional[datetime] = Field(default=None, description="End time (for windows)")
    recurrence_rule: Optional[str] = Field(default=None, description="Recurrence: daily/weekly/weekdays/weekends/monthly")
    recurrence_interval: int = Field(default=1, ge=1, description="Recurrence interval")
    is_active: bool = Field(default=True, description="Whether item is active")
    tags: List[str] = Field(default_factory=list, description="Tags")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_triggered: Optional[datetime] = Field(default=None, description="Last triggered time")
    next_trigger_time: Optional[datetime] = Field(default=None, description="Next scheduled trigger")


class TimeExpression(BaseModel):
    """A parsed time expression."""

    raw: str = Field(..., description="Original raw expression")
    parsed_time: datetime = Field(..., description="Parsed datetime")
    is_recurring: bool = Field(default=False, description="Whether expression is recurring")
    recurrence_pattern: str = Field(default="", description="Recurrence pattern string")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Parse confidence")


class ConflictInfo(BaseModel):
    """Information about scheduling conflicts."""

    has_conflict: bool = Field(default=False, description="Whether conflict exists")
    conflicting_items: List[str] = Field(default_factory=list, description="Conflicting item IDs")
    conflict_type: str = Field(default="", description="Conflict type: time/resource/recurrence")
    suggestion: str = Field(default="", description="Resolution suggestion")
