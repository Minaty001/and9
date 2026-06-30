"""
Phase 43 — Maintenance Configuration.
"""

from pydantic import Field
from services.base.config_base import BaseConfig


class MaintenanceConfig(BaseConfig):
    """Configuration for maintenance subsystem."""

    service_name: str = Field(default="jarvis_maintenance", description="Maintenance service name")
    enable_versioning: bool = Field(default=True, description="Enable version tracking")
    enable_migration: bool = Field(default=True, description="Enable migration scripts")
    enable_backup: bool = Field(default=True, description="Enable backup management")
    enable_diagnostics: bool = Field(default=True, description="Enable diagnostics engine")
    backup_interval_minutes: int = Field(default=1440, ge=1, description="Backup interval in minutes (default daily)")
    backup_retention_days: int = Field(default=30, ge=1, description="Days to retain backups")
    max_backups: int = Field(default=10, ge=1, le=1000, description="Maximum number of backups to keep")
    deprecation_warning_days: int = Field(default=90, ge=1, description="Days before removal to warn")
    diagnostic_log_retention_days: int = Field(default=7, ge=1, description="Days to retain diagnostic logs")
    data_dir: str = Field(default="./maintenance_data", description="Directory for maintenance data files")

    model_config = {"env_prefix": "JARVIS_PHASE43_"}
