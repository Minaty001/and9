"""
Phase 15 — Skill Router Configuration.

Uses Pydantic v2 model_config style (not old class Config).
"""

from pydantic import Field
from services.base.config_base import BaseConfig


class SkillConfig(BaseConfig):
    """Configuration for the Skill Router service."""

    service_name: str = Field(default="jarvis_skill_router", description="Skill Router service name")
    max_skills: int = Field(default=100, description="Maximum number of registered skills")
    enable_versioning: bool = Field(default=True, description="Enable skill version history tracking")
    enable_fallback: bool = Field(default=True, description="Enable fallback to next skill on failure")
    fallback_timeout_ms: int = Field(default=5000, description="Timeout for fallback execution in ms")
    enable_plugin_discovery: bool = Field(default=True, description="Enable automatic plugin discovery")

    model_config = {"env_prefix": "JARVIS_PHASE15_"}
