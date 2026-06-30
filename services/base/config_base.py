"""
Shared configuration base for all JARVIS services.

Uses Pydantic BaseSettings so each service can load its config
from environment variables, .env files, or defaults.
"""

from pydantic import BaseModel, Field
from typing import Optional


class BaseConfig(BaseModel):
    """Common configuration fields shared by all services.

    Each service subclasses this and adds its own fields.
    """

    service_name: str = Field(default="jarvis_service", description="Name of this service")
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format: json or text")
    log_file: Optional[str] = Field(default=None, description="Path to log file")
    max_log_size_mb: int = Field(default=5, description="Max log file size in MB")
    backup_count: int = Field(default=2, description="Number of log backups to keep")
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")
    enable_tracing: bool = Field(default=False, description="Enable request tracing")


class DatabaseConfig(BaseModel):
    """Shared database configuration."""

    db_path: str = Field(default=":memory:", description="Database path")
    pool_size: int = Field(default=5, description="Connection pool size")
    timeout_seconds: int = Field(default=30, description="Query timeout")
