"""
Phase 15 — Skill Router Models.

Data models for skill definitions and execution results.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SkillDefinition(BaseModel):
    """Definition of a registered skill."""

    id: str = Field(..., description="Unique skill identifier")
    name: str = Field(..., description="Human-readable skill name")
    version: str = Field(default="1.0.0", description="Skill version string")
    description: str = Field(default="", description="Description of what the skill does")
    intents: List[str] = Field(default_factory=list, description="List of intents this skill handles")
    required_entities: List[str] = Field(default_factory=list, description="Entities required for execution")
    optional_entities: List[str] = Field(default_factory=list, description="Entities that enhance execution")
    priority: int = Field(default=0, description="Execution priority (higher = preferred)")
    enabled: bool = Field(default=True, description="Whether the skill is active")
    config: Dict[str, Any] = Field(default_factory=dict, description="Skill-specific configuration")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), description="Creation timestamp")


class SkillResult(BaseModel):
    """Result of a single skill execution."""

    skill_id: str = Field(..., description="ID of the executed skill")
    success: bool = Field(default=True, description="Whether execution succeeded")
    output: str = Field(default="", description="Text output from the skill")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence in the result")
    duration_ms: float = Field(default=0.0, description="Execution duration in milliseconds")
    error: Optional[str] = Field(default=None, description="Error message if execution failed")
