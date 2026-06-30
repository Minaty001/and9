"""
Phase 10 — Reflex Brain Configuration.
"""

from pydantic import Field
from services.base.config_base import BaseConfig


class ReflexConfig(BaseConfig):
    """Configuration for the reflex brain."""

    service_name: str = Field(default="jarvis_reflex", description="Reflex brain service name")
    enable_default_actions: bool = Field(default=True, description="Register built-in default reflex actions")
    case_sensitive: bool = Field(default=False, description="Whether pattern matching is case-sensitive")
    max_actions: int = Field(default=100, ge=1, le=500, description="Maximum registered reflex actions")
    default_confidence: float = Field(default=0.95, ge=0.0, le=1.0, description="Default confidence for reflex matches")
    response_prefix: str = Field(default="", description="Optional prefix for reflex responses")
    enable_handler_execution: bool = Field(default=True, description="Execute handler callbacks on match")

    model_config = {"env_prefix": "JARVIS_REFLEX_"}
