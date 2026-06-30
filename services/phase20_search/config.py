"""
Phase 20 — Search Engine Configuration.
"""

from pydantic import Field
from services.base.config_base import BaseConfig


class SearchConfig(BaseConfig):
    """Configuration for the search engine."""

    service_name: str = Field(default="jarvis_search", description="Search engine service name")
    enable_web_search: bool = Field(default=True, description="Enable web search source")
    enable_memory_search: bool = Field(default=True, description="Enable memory search source")
    enable_document_search: bool = Field(default=True, description="Enable document search source")
    max_results: int = Field(default=20, ge=1, le=100, description="Maximum merged results")
    cache_ttl_seconds: int = Field(default=300, ge=1, le=86400, description="Cache TTL in seconds")
    enable_cache: bool = Field(default=True, description="Enable result caching")
    enable_telemetry: bool = Field(default=True, description="Enable search telemetry")
    web_search_timeout_ms: int = Field(default=5000, ge=100, le=60000, description="Web search timeout in ms")
    rerank_min_score: float = Field(default=0.3, ge=0.0, le=1.0, description="Minimum score for reranking")

    model_config = {"env_prefix": "JARVIS_PHASE20_"}
