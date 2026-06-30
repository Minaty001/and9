"""
Phase 8 — Context Models.

TurnContext represents a single conversation turn.
ContextSnapshot is the full context state returned by the service.
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TurnContext(BaseModel):
    """A single conversation turn with its processing results."""

    turn_id: int = Field(..., description="Sequential turn number")
    query: str = Field(..., description="The user query text")
    normalized_query: str = Field(default="", description="Normalized query text")
    intent: str = Field(default="", description="Detected intent")
    intent_confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Confidence of detected intent")
    entities: Dict[str, List[str]] = Field(default_factory=dict, description="Entities grouped by type")
    embedding: Optional[List[float]] = Field(default=None, description="Query embedding vector")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="When this turn occurred")
    response: str = Field(default="", description="Assistant response text")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    def age_seconds(self, now: Optional[datetime] = None) -> float:
        """Seconds since this turn occurred."""
        ref = now or datetime.now(timezone.utc)
        return (ref - self.timestamp).total_seconds()

    def decay_factor(self, config_decay_rate: float) -> float:
        """Compute exponential decay factor based on turn age and configured rate."""
        age_minutes = self.age_seconds() / 60.0
        return config_decay_rate ** (age_minutes / 5.0)  # half-life approximately every ~5 minutes


class ContextSnapshot(BaseModel):
    """Snapshot of the current context state."""

    session_id: str = Field(default="default", description="Session identifier")
    turn_count: int = Field(default=0, description="Total turns in session")
    recent_turns: List[TurnContext] = Field(default_factory=list, description="Recent conversation turns")
    current_turn: Optional[TurnContext] = Field(default=None, description="The most recent turn")
    active_entities: Dict[str, List[str]] = Field(default_factory=dict, description="Active entities across recent turns")
    recent_intents: List[str] = Field(default_factory=list, description="Intents from recent turns in order")
    elapsed_seconds: float = Field(default=0.0, description="Session duration in seconds")
    is_active: bool = Field(default=True, description="Whether session is still active")
