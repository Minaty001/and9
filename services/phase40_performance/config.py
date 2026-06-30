"""
Phase 40 — Performance Optimization Configuration.
"""

from pydantic import Field
from typing import Optional
from services.base.config_base import BaseConfig


class PerformanceConfig(BaseConfig):
    """Configuration for the performance optimization service."""

    service_name: str = Field(default="jarvis_performance", description="Performance optimization service name")
    enable_l1_cache: bool = Field(default=True, description="Enable L1 cache")
    enable_l2_cache: bool = Field(default=True, description="Enable L2 cache")
    enable_lazy_loading: bool = Field(default=True, description="Enable lazy loading")
    enable_request_coalescing: bool = Field(default=True, description="Enable request coalescing")
    enable_resource_pooling: bool = Field(default=True, description="Enable resource pooling")
    l1_cache_size: int = Field(default=128, ge=16, le=65536, description="L1 cache capacity (entries)")
    l2_cache_size: int = Field(default=1024, ge=64, le=262144, description="L2 cache capacity (entries)")
    l1_cache_ttl_seconds: int = Field(default=60, ge=1, le=3600, description="L1 cache TTL in seconds")
    l2_cache_ttl_seconds: int = Field(default=600, ge=1, le=86400, description="L2 cache TTL in seconds")
    pool_max_size: int = Field(default=10, ge=1, le=1000, description="Resource pool max size")
    pool_idle_timeout: int = Field(default=300, ge=1, le=86400, description="Pool idle timeout in seconds")
    enable_benchmark: bool = Field(default=True, description="Enable benchmark utilities")
    warmup_strategy: str = Field(
        default="lazy",
        description="Cache warmup strategy: lazy (load on demand), eager (load on initialize), predictive (load likely keys)",
    )

    model_config = {"env_prefix": "JARVIS_PHASE40_"}
