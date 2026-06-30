"""
Phase 1 — Core Configuration.

All configurable parameters for the core JARVIS framework.
Uses Pydantic BaseModel for validation and serialization.
"""

from pydantic import Field
from typing import Optional
from services.base.config_base import BaseConfig


class CoreConfig(BaseConfig):
    """Core JARVIS configuration.

    All parameters have sensible defaults suitable for Android Termux
    with a 50MB RAM budget.
    """

    service_name: str = Field(default="jarvis_core", description="Core service name")
    version: str = Field(default="1.0.0", description="JARVIS version")
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format: json or text")
    log_file: Optional[str] = Field(default=None, description="Path to log file")
    max_log_size_mb: int = Field(default=5, description="Max log file size in MB")
    backup_count: int = Field(default=2, description="Number of log backups to keep")
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")
    enable_tracing: bool = Field(default=False, description="Enable request tracing")

    # Design rules
    deterministic_execution: bool = Field(
        default=True,
        description="If True, same input always produces same output",
    )
    local_first: bool = Field(
        default=True,
        description="If True, prefer local execution over cloud",
    )
    max_response_length: int = Field(
        default=2000,
        description="Maximum response text length in characters",
    )
    default_locale: str = Field(
        default="en-IN",
        description="Default locale for responses",
    )

    class Config:
        env_prefix = "JARVIS_CORE_"
