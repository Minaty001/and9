"""
Phase 38 — Configuration System Configuration.
"""

from typing import List
from pydantic import Field
from services.base.config_base import BaseConfig


class ConfigSystemConfig(BaseConfig):
    """Configuration for the config system service."""

    service_name: str = Field(default="jarvis_config", description="Config system service name")
    sources: List[str] = Field(default_factory=lambda: ["memory", "file", "env"],
                               description="Configuration sources in order of priority")
    config_file_path: str = Field(default="./jarvis_config.json", description="Path to config file")
    enable_profiles: bool = Field(default=True, description="Enable configuration profiles")
    active_profile: str = Field(default="default", description="Active profile name")
    enable_overrides: bool = Field(default=True, description="Enable config overrides")
    enable_validation: bool = Field(default=True, description="Enable config validation")
    enable_env_watch: bool = Field(default=False, description="Watch environment variables")
    enable_encryption: bool = Field(default=False, description="Enable secret encryption")
    auto_save_interval_seconds: int = Field(default=0, ge=0, le=86400,
                                            description="Auto-save interval (0=disabled)")
    hot_reload_interval_seconds: int = Field(default=30, ge=0, le=3600,
                                             description="Hot reload polling interval (0=disabled)")

    model_config = {"env_prefix": "JARVIS_PHASE38_"}
