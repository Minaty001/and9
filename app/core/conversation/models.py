"""
app/core/conversation/models.py — Conversation Manager Models.

Data models for sessions and dialogue state.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class DialogueState:
    """Current state of a dialogue session."""

    session_id: str
    turn_count: int = 0
    active_topic: str = "general"
    user_goal: Optional[str] = None
    pending_questions: List[str] = field(default_factory=list)
    recent_entities: Dict[str, Any] = field(default_factory=dict)
    references: Dict[str, str] = field(default_factory=dict)
    confidence: float = 1.0
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_active: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Session:
    """A conversation session."""

    id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    dialogue_states: List[DialogueState] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    active: bool = True
