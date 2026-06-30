"""
Phase 42 — Deployment Configuration.
"""

from pydantic import Field
from services.base.config_base import BaseConfig


class DeploymentConfig(BaseConfig):
    """Configuration for deployment, packaging, health checks, and updates."""

    service_name: str = Field(default="jarvis_deployment", description="Deployment service name")
    environment: str = Field(default="development", description="Deployment environment (development/staging/production)")
    platform: str = Field(default="desktop", description="Target platform (android/desktop/cloud)")
    enable_health_checks: bool = Field(default=True, description="Enable health check monitoring")
    enable_packaging: bool = Field(default=True, description="Enable package creation/extraction")
    enable_updates: bool = Field(default=True, description="Enable update checking and application")
    enable_rollback: bool = Field(default=True, description="Enable rollback support")
    health_check_interval_seconds: int = Field(default=30, ge=1, le=3600, description="Interval between periodic health checks")
    package_format: str = Field(default="zip", description="Package archive format (zip/tar)")
    update_check_url: str = Field(default="", description="URL to check for updates")
    rollback_max_versions: int = Field(default=5, ge=1, le=100, description="Maximum stored rollback versions")
    termux_data_dir: str = Field(default="/data/data/com.termux/files/home/.jarvis", description="Termux/Android data directory")
    desktop_data_dir: str = Field(default="~/.jarvis", description="Desktop data directory")
    cloud_endpoint: str = Field(default="", description="Cloud deployment endpoint")

    model_config = {"env_prefix": "JARVIS_PHASE42_"}
