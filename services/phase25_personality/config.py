"""
Phase 25 — Personality Engine Configuration.
"""

from pydantic import Field
from services.base.config_base import BaseConfig


class PersonalityConfig(BaseConfig):
    """Configuration for the Personality Engine."""

    service_name: str = Field(default="jarvis_personality", description="Personality engine service name")
    active_persona: str = Field(default="jarvis_default", description="Active persona ID")
    enable_persona_switching: bool = Field(default=True, description="Enable persona switching")
    enable_greeting_rules: bool = Field(default=True, description="Enable greeting rules")
    max_response_length: int = Field(default=500, ge=50, le=2000, description="Max response length")
    default_tone: str = Field(default="helpful", description="Default tone")
    personas_dir: str = Field(default="", description="Personas directory path")

    model_config = {"env_prefix": "JARVIS_PHASE25_"}
