"""
Phase 28 — Scheduler Configuration.
"""

from pydantic import Field
from services.base.config_base import BaseConfig


class SchedulerConfig(BaseConfig):
    """Configuration for the scheduler service."""

    service_name: str = Field(default="jarvis_scheduler", description="Scheduler service name")
    enable_persistence: bool = Field(default=True, description="Enable schedule persistence")
    max_scheduled_items: int = Field(default=200, ge=10, le=10000, description="Max scheduled items")
    check_interval_seconds: int = Field(default=10, ge=1, le=3600, description="Interval between checks")
    default_reminder_offset_minutes: int = Field(default=5, ge=0, le=1440, description="Default reminder offset")
    enable_conflict_detection: bool = Field(default=True, description="Enable conflict detection")
    storage_path: str = Field(default="scheduler_data.json", description="Path to persistence file")

    model_config = {"env_prefix": "JARVIS_PHASE28_"}
