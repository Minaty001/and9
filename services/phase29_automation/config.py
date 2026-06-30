"""
Phase 29 — Automation Engine Configuration.
"""

from pydantic import Field
from services.base.config_base import BaseConfig


class AutomationConfig(BaseConfig):
    """Configuration for the automation engine."""

    service_name: str = Field(default="jarvis_automation", description="Automation engine service name")
    max_rules: int = Field(default=50, ge=1, le=500, description="Max automation rules")
    enable_rule_validation: bool = Field(default=True, description="Enable rule validation")
    enable_execution_history: bool = Field(default=True, description="Enable execution history")
    max_history_entries: int = Field(default=200, ge=10, le=10000, description="Max history entries")
    enable_rollback: bool = Field(default=True, description="Enable action rollback")
    default_cooldown_seconds: int = Field(default=60, ge=0, le=86400, description="Default cooldown between executions")

    model_config = {"env_prefix": "JARVIS_PHASE29_"}
