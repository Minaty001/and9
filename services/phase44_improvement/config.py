"""
Phase 44 — Continuous Improvement Configuration.
"""

from pydantic import Field
from services.base.config_base import BaseConfig


class ImprovementConfig(BaseConfig):
    """Configuration for continuous improvement subsystem."""

    service_name: str = Field(default="jarvis_improvement", description="Improvement service name")
    enable_feedback_collection: bool = Field(default=True, description="Enable user feedback collection")
    enable_benchmarking: bool = Field(default=True, description="Enable benchmark running")
    enable_prompt_refinement: bool = Field(default=True, description="Enable prompt versioning")
    enable_a_b_testing: bool = Field(default=False, description="Enable A/B testing")
    feedback_retention_days: int = Field(default=90, ge=1, description="Days to retain feedback")
    benchmark_retention_days: int = Field(default=365, ge=1, description="Days to retain benchmark results")
    refinement_cooldown_hours: int = Field(default=24, ge=1, description="Cooldown between prompt refinements")
    max_prompt_versions: int = Field(default=10, ge=1, le=100, description="Maximum prompt versions to keep")

    model_config = {"env_prefix": "JARVIS_PHASE44_"}
