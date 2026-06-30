"""
Phase 25 — Personality Engine Models.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Persona(BaseModel):
    """A personality persona with tone, style, and constraints."""

    id: str = Field(..., description="Unique persona identifier")
    name: str = Field(..., description="Human-readable persona name")
    tone: str = Field(default="helpful", description="Default tone for this persona")
    style_guide: str = Field(default="", description="Style guide text")
    greeting_rules: Dict[str, Any] = Field(default_factory=dict, description="Greeting configuration")
    response_constraints: Dict[str, Any] = Field(default_factory=dict, description="Response constraints")
    vocabulary_whitelist: List[str] = Field(default_factory=list, description="Allowed vocabulary")
    vocabulary_blacklist: List[str] = Field(default_factory=list, description="Disallowed vocabulary")
    emoji_usage: str = Field(default="normal", description="Emoji usage: never/rarely/normal/expressive")
    formality_level: int = Field(default=5, ge=1, le=10, description="Formality level 1-10")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class PersonalityProfile(BaseModel):
    """Current personality profile state."""

    active_persona_id: str = Field(..., description="Currently active persona ID")
    tone_scores: Dict[str, float] = Field(default_factory=dict, description="Tone usage scores")
    style_attributes: Dict[str, Any] = Field(default_factory=dict, description="Current style attributes")
    greeting_history: List[str] = Field(default_factory=list, description="Greeting history")
    response_count: int = Field(default=0, ge=0, description="Number of responses generated")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
