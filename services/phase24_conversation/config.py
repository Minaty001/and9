"""
Phase 24 — Conversation Manager Configuration.
"""

from pydantic import Field
from services.base.config_base import BaseConfig


class ConversationConfig(BaseConfig):
    """Configuration for the Conversation Manager."""

    service_name: str = Field(default="jarvis_conversation", description="Conversation manager service name")
    max_session_duration_minutes: int = Field(default=30, ge=1, le=1440, description="Max session duration")
    max_turns_per_session: int = Field(default=100, ge=1, le=10000, description="Max turns per session")
    enable_reference_resolution: bool = Field(default=True, description="Enable reference resolution")
    enable_topic_tracking: bool = Field(default=True, description="Enable topic tracking")
    enable_goal_tracking: bool = Field(default=True, description="Enable user goal tracking")
    session_timeout_seconds: int = Field(default=1800, ge=60, le=86400, description="Session timeout in seconds")

    model_config = {"env_prefix": "JARVIS_PHASE24_"}
