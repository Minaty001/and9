"""
Phase 45 — Roadmap Configuration.
"""

from pydantic import Field
from services.base.config_base import BaseConfig


class RoadmapConfig(BaseConfig):
    """Configuration for roadmap subsystem."""

    service_name: str = Field(default="jarvis_roadmap", description="Roadmap service name")
    enable_multi_agent: bool = Field(default=True, description="Enable multi-agent orchestration")
    enable_multimodal: bool = Field(default=True, description="Enable multimodal processing")
    enable_offline_first: bool = Field(default=True, description="Enable offline-first caching")
    enable_plugin_marketplace: bool = Field(default=True, description="Enable plugin marketplace")
    enable_autonomous_workflows: bool = Field(default=True, description="Enable autonomous workflows")
    multi_agent_max_agents: int = Field(default=5, ge=1, le=100, description="Maximum number of agents")
    offline_cache_size_mb: int = Field(default=500, ge=1, description="Offline cache size in MB")

    model_config = {"env_prefix": "JARVIS_PHASE45_"}
