"""
Phase 2 — Architecture Configuration.
"""

from pydantic import Field
from services.base.config_base import BaseConfig


class ArchitectureConfig(BaseConfig):
    """Configuration for the system architecture layer."""

    service_name: str = Field(default="jarvis_architecture", description="Architecture service name")
    event_queue_max_size: int = Field(default=1000, description="Max events in the event queue")
    event_timeout_seconds: float = Field(default=30.0, description="Max time to process an event")
    max_modules: int = Field(default=50, description="Maximum registered modules")
    enable_event_logging: bool = Field(default=True, description="Log all events")
    enable_module_health_checks: bool = Field(default=True, description="Periodic health checks on modules")

    class Config:
        env_prefix = "JARVIS_ARCH_"
