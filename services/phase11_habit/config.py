"""
Phase 11 — Habit Brain Configuration.
"""

from pydantic import Field
from services.base.config_base import BaseConfig


class HabitConfig(BaseConfig):
    """Configuration for habit learning."""

    service_name: str = Field(default="jarvis_habit", description="Habit brain service name")
    min_observations: int = Field(default=3, ge=1, le=100, description="Min occurrences before suggesting a habit")
    confidence_threshold: float = Field(default=0.6, ge=0.0, le=1.0, description="Min confidence to surface suggestion")
    decay_rate: float = Field(default=0.9, ge=0.0, le=1.0, description="Per-day decay multiplier for unused habits")
    max_habits: int = Field(default=200, ge=10, le=10000, description="Max tracked habits")
    time_window_minutes: int = Field(default=30, ge=1, le=1440, description="Time tolerance for matching (minutes)")
    require_user_approval: bool = Field(default=True, description="Require user ok before auto-executing")
    enable_audit_log: bool = Field(default=True, description="Log all habit suggestions and outcomes")
    max_suggestions: int = Field(default=5, ge=1, le=50, description="Max suggestions per request")

    model_config = {"env_prefix": "JARVIS_HABIT_"}
