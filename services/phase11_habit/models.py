"""
Phase 11 — Habit Brain Models.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class HabitObservation(BaseModel):
    """A single observed event for habit learning."""

    command: str = Field(..., description="The command or intent observed")
    intent: str = Field(default="", description="Detected intent")
    time_hour: int = Field(default=0, ge=0, le=23, description="Hour of day (0-23)")
    time_minute: int = Field(default=0, ge=0, le=59, description="Minute of hour")
    day_of_week: int = Field(default=-1, ge=-1, le=6, description="Day of week (0=Mon, -1=any)")
    location: Optional[str] = Field(default=None, description="Location context")
    entities: Dict[str, List[str]] = Field(default_factory=dict, description="Extracted entities")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)


class HabitPattern(BaseModel):
    """A learned habit pattern tracked over time."""

    pattern_id: str = Field(..., description="Unique pattern identifier")
    command: str = Field(..., description="The command pattern")
    intent: str = Field(default="", description="Associated intent")
    typical_hour: float = Field(default=12.0, ge=0.0, le=23.99, description="Average hour of occurrence")
    typical_day: int = Field(default=-1, ge=-1, le=6, description="Typical day of week (-1=any)")
    location: Optional[str] = Field(default=None, description="Typical location")
    frequency: int = Field(default=1, ge=0, description="Number of observed occurrences")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Learned confidence score")
    last_observed: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    first_observed: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user_approved: bool = Field(default=False, description="User has approved this habit")
    user_rejected: bool = Field(default=False, description="User has rejected this habit")
    auto_execution_count: int = Field(default=0, description="Times auto-executed (with approval)")
    entities: Dict[str, List[str]] = Field(default_factory=dict, description="Typical entity values")
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def age_days(self) -> float:
        return (datetime.now(timezone.utc) - self.first_observed).total_seconds() / 86400.0


class HabitSuggestion(BaseModel):
    """A ranked habit suggestion for the user."""

    pattern_id: str = Field(..., description="Pattern identifier")
    command: str = Field(..., description="Suggested command")
    intent: str = Field(default="", description="Associated intent")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Suggestion confidence")
    reason: str = Field(default="", description="Human-readable reason")
    requires_approval: bool = Field(default=True, description="Whether user approval is needed")
    typical_time: str = Field(default="", description="Typical time description")
    frequency_text: str = Field(default="", description="How often this happens")


class HabitAuditEntry(BaseModel):
    """Audit log entry for habit actions."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    action: str = Field(..., description="Action taken (suggested, approved, rejected, auto_executed)")
    pattern_id: str = Field(default="", description="Pattern identifier")
    command: str = Field(default="", description="Command involved")
    details: str = Field(default="", description="Additional context")
