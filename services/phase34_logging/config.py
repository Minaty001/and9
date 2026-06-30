"""
Phase 34 — Logging System Configuration.
"""

from pydantic import Field
from services.base.config_base import BaseConfig


class LoggingConfig(BaseConfig):
    """Configuration for the logging system."""

    service_name: str = Field(default="jarvis_logging", description="Logging service name")
    default_level: str = Field(default="INFO", description="Default log level")
    enable_structured_logging: bool = Field(default=True, description="Enable structured JSON logging")
    enable_async_logging: bool = Field(default=True, description="Enable asynchronous logging")
    sinks: dict = Field(default_factory=lambda: {
        "console": {"enabled": True, "level": "DEBUG"},
        "file": {"enabled": True, "level": "INFO", "path": "logs/jarvis.log"},
        "remote": {"enabled": False, "level": "WARN"},
    }, description="Log sink configurations")
    log_format: str = Field(default="json", description="Log format: json or text")
    file_retention_days: int = Field(default=7, ge=1, le=365, description="File retention in days")
    max_file_size_mb: int = Field(default=10, ge=1, le=1000, description="Max log file size in MB")
    remote_endpoint: str = Field(default="", description="Remote log endpoint URL")
    enable_trace_ids: bool = Field(default=True, description="Enable trace ID generation")
    enable_batch_logging: bool = Field(default=False, description="Enable batch logging")
    batch_size: int = Field(default=50, ge=1, le=1000, description="Batch size for logging")
    audit_log_path: str = Field(default="logs/jarvis_audit.log", description="Audit log file path")
    telemetry_log_path: str = Field(default="logs/jarvis_telemetry.log", description="Telemetry log file path")
    rotation_interval_hours: int = Field(default=24, ge=1, le=720, description="Time-based rotation interval")
    enable_rotation_compression: bool = Field(default=False, description="Gzip compressed rotated files")

    model_config = {"env_prefix": "JARVIS_PHASE34_"}
