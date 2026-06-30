"""
Phase 13 — Planner Configuration.
"""

from pydantic import Field
from services.base.config_base import BaseConfig


class PlannerConfig(BaseConfig):
    """Configuration for the planner service."""

    service_name: str = Field(default="jarvis_planner", description="Planner service name")

    # ── Planning limits ──────────────────────────────────────────
    max_subtasks: int = Field(default=20, ge=1, le=1000, description="Maximum subtasks per plan")
    max_depth: int = Field(default=5, ge=1, le=50, description="Maximum decomposition depth")

    # ── Confidence ────────────────────────────────────────────────
    min_confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Minimum confidence for subtasks")

    # ── Execution settings ────────────────────────────────────────
    enable_parallel: bool = Field(default=True, description="Enable parallel subtask execution")
    enable_rollback: bool = Field(default=True, description="Enable rollback on failure")
    max_retries: int = Field(default=3, ge=0, le=10, description="Max retries per subtask")

    model_config = {"env_prefix": "JARVIS_PHASE13_"}
