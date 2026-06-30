"""
Phase 39 — Plugin SDK Configuration.
"""

from typing import List
from pydantic import Field
from services.base.config_base import BaseConfig


class PluginSdkConfig(BaseConfig):
    """Configuration for the plugin SDK service."""

    service_name: str = Field(default="jarvis_plugin_sdk", description="Plugin SDK service name")
    plugin_dir: str = Field(default="./plugins", description="Directory to discover plugins")
    enable_sandbox: bool = Field(default=True, description="Enable sandboxed execution")
    enable_hooks: bool = Field(default=True, description="Enable hook system")
    max_plugins: int = Field(default=20, ge=1, le=100, description="Maximum number of loaded plugins")
    enable_version_check: bool = Field(default=True, description="Check plugin API version compatibility")
    enable_dependency_resolution: bool = Field(default=True, description="Resolve plugin dependencies")
    sandbox_timeout_ms: int = Field(default=5000, ge=100, le=60000,
                                    description="Sandbox execution timeout in milliseconds")
    allowed_imports: List[str] = Field(default_factory=list, description="Allowed imports in sandbox")
    plugin_auto_load: bool = Field(default=True, description="Auto-load plugins from plugin_dir")

    model_config = {"env_prefix": "JARVIS_PHASE39_"}
