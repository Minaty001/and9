"""
Phase 26 — Learning Engine Models.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class LearningObservation(BaseModel):
    """A single observation for learning."""

    observation_type: str = Field(..., description="Type: preference/pattern/summary/feedback")
    category: str = Field(..., description="Observation category")
    key: str = Field(..., description="Observation key")
    value: Any = Field(..., description="Observed value")
    context: Dict[str, Any] = Field(default_factory=dict, description="Context at time of observation")
    source: str = Field(default="user", description="Source of observation")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence in observation")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user_verified: bool = Field(default=False, description="Whether user has verified this")


class LearnedPreference(BaseModel):
    """A learned user preference."""

    category: str = Field(..., description="Preference category")
    key: str = Field(..., description="Preference key")
    preferred_value: Any = Field(..., description="The learned preferred value")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Confidence score")
    observation_count: int = Field(default=1, ge=0, description="Number of observations")
    last_observed: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    alternatives: List[Any] = Field(default_factory=list, description="Alternative values observed")
    context_conditions: Dict[str, Any] = Field(default_factory=dict, description="Context conditions")


class LearnedPattern(BaseModel):
    """A learned recurring interaction pattern."""

    pattern_id: str = Field(..., description="Unique pattern identifier")
    trigger: str = Field(..., description="Trigger condition/event")
    action: str = Field(..., description="Action taken")
    frequency: int = Field(default=1, ge=0, description="Times observed")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Pattern confidence")
    contexts: List[Dict[str, Any]] = Field(default_factory=list, description="Contexts where pattern occurred")
    last_triggered: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    success_rate: float = Field(default=1.0, ge=0.0, le=1.0, description="Historical success rate")


class ActivitySummary(BaseModel):
    """A summary of activity over a period."""

    period: str = Field(..., description="Summary period: hourly/daily/weekly")
    start_time: datetime = Field(..., description="Period start")
    end_time: datetime = Field(..., description="Period end")
    total_interactions: int = Field(default=0, ge=0, description="Total interactions in period")
    top_intents: List[Dict[str, Any]] = Field(default_factory=list, description="Top intents with counts")
    top_entities: List[Dict[str, Any]] = Field(default_factory=list, description="Top entities with counts")
    avg_confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Average confidence")
    top_queries: List[Dict[str, Any]] = Field(default_factory=list, description="Top queries")
    insights: List[str] = Field(default_factory=list, description="Generated insights")
