"""
Phase 7 — Entity Models.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Entity(BaseModel):
    """A single extracted entity."""

    type: str = Field(..., description="Entity type: app, contact, time, location, media, etc.")
    value: str = Field(..., description="Entity value (normalized)")
    original: str = Field(..., description="Original text span")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Extraction confidence")
    start: int = Field(default=0, description="Start position in query")
    end: int = Field(default=0, description="End position in query")
    normalized: Optional[str] = Field(default=None, description="Further normalized form")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class EntityResult(BaseModel):
    """Result of entity extraction."""

    entities: List[Entity] = Field(default_factory=list, description="Extracted entities")
    grouped: Dict[str, List[Entity]] = Field(default_factory=dict, description="Entities grouped by type")
    validated: bool = Field(default=False, description="Whether entities were validated")
    validation_errors: List[str] = Field(default_factory=list, description="Validation error messages")
    time_ms: float = Field(default=0.0, description="Extraction time in milliseconds")
