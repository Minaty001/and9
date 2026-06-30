"""
Phase 8 — Context Builder Configuration.
"""

from pydantic import Field
from typing import List
from services.base.config_base import BaseConfig


class ContextConfig(BaseConfig):
    """Configuration for context management."""

    service_name: str = Field(default="jarvis_context", description="Context builder service name")
    max_turns: int = Field(default=10, ge=1, le=100, description="Maximum conversation turns to retain")
    decay_rate: float = Field(default=0.85, ge=0.0, le=1.0, description="Exponential decay per turn (1.0 = no decay)")
    entity_overlap_weight: float = Field(default=0.50, ge=0.0, le=1.0, description="Weight for entity overlap in relevance scoring")
    intent_match_weight: float = Field(default=0.25, ge=0.0, le=1.0, description="Weight for intent match in relevance scoring")
    recency_weight: float = Field(default=0.25, ge=0.0, le=1.0, description="Weight for recency in relevance scoring")
    relevance_threshold: float = Field(default=0.3, ge=0.0, le=1.0, description="Minimum relevance score to retain context")
    enable_auto_decay: bool = Field(default=True, description="Apply decay automatically on each turn")
    enable_entity_tracking: bool = Field(default=True, description="Track entities across turns")
    session_timeout_minutes: int = Field(default=30, ge=1, description="Minutes before session auto-expires")

    model_config = {"env_prefix": "JARVIS_CONTEXT_"}
