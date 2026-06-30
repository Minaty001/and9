"""
Phase 21 — API Manager Configuration.
"""

from typing import Dict, Any
from pydantic import Field
from services.base.config_base import BaseConfig


class ApiConfig(BaseConfig):
    """Configuration for the API Manager."""

    service_name: str = Field(default="jarvis_api", description="API manager service name")
    global_timeout_ms: int = Field(default=10000, ge=100, le=120000, description="Global timeout in ms")
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")
    enable_rate_limiting: bool = Field(default=True, description="Enable rate limiting")
    requests_per_minute: int = Field(default=60, ge=1, le=10000, description="Max requests per minute")
    enable_caching: bool = Field(default=True, description="Enable response caching")
    cache_ttl_seconds: int = Field(default=300, ge=1, le=86400, description="Cache TTL in seconds")
    adapters: Dict[str, Any] = Field(default_factory=dict, description="Registered adapter configs")
    fallback_enabled: bool = Field(default=True, description="Enable fallback adapters")

    model_config = {"env_prefix": "JARVIS_PHASE21_"}
