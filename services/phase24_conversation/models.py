"""
Phase 24 — Conversation Manager Models.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DialogueState(BaseModel):
    """Current state of a dialogue session."""

    session_id: str = Field(..., description="Session identifier")
    turn_count: int = Field(default=0, ge=0, description="Number of turns in this session")
    active_topic: str = Field(default="general", description="Current active topic")
    user_goal: Optional[str] = Field(default=None, description="Detected user goal")
    pending_questions: List[str] = Field(default_factory=list, description="Questions awaiting answer")
    recent_entities: Dict[str, Any] = Field(default_factory=dict, description="Recently mentioned entities")
    references: Dict[str, str] = Field(default_factory=dict, description="Reference mappings")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="State confidence score")
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_active: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Session(BaseModel):
    """A conversation session."""

    id: str = Field(..., description="Unique session identifier")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    dialogue_states: List[DialogueState] = Field(default_factory=list, description="Dialogue history")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Session metadata")
    active: bool = Field(default=True, description="Whether session is active")
