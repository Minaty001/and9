"""
Phase 26 — Learning Engine Configuration.
"""

from pydantic import Field
from services.base.config_base import BaseConfig


class LearningConfig(BaseConfig):
    """Configuration for the learning engine."""

    service_name: str = Field(default="jarvis_learning", description="Learning engine service name")
    enable_preference_learning: bool = Field(default=True, description="Enable preference learning from feedback")
    enable_pattern_learning: bool = Field(default=True, description="Enable learning of recurring patterns")
    enable_summarization: bool = Field(default=True, description="Enable activity summarization")
    min_observations_for_learning: int = Field(default=3, ge=1, le=100, description="Min observations before learning")
    learning_rate: float = Field(default=0.3, ge=0.0, le=1.0, description="Learning rate for preference updates")
    max_patterns_per_category: int = Field(default=50, ge=1, le=1000, description="Max patterns per category")
    summarization_interval_minutes: int = Field(default=60, ge=5, le=1440, description="Interval between summaries")
    store_positive_feedback_only: bool = Field(default=False, description="Only store positive feedback")

    model_config = {"env_prefix": "JARVIS_PHASE26_"}
