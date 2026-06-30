"""
Phase 9 — Memory System Configuration.
"""

from pydantic import Field
from services.base.config_base import BaseConfig


class MemoryConfig(BaseConfig):
    """Configuration for memory management."""

    service_name: str = Field(default="jarvis_memory", description="Memory service name")
    max_working_memories: int = Field(default=50, ge=10, le=10000, description="Max working memory items before eviction")
    max_long_term_memories: int = Field(default=500, ge=50, le=100000, description="Max long-term memory items")
    consolidation_importance_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Min importance to promote working→long-term")
    auto_consolidate_on_store: bool = Field(default=True, description="Run consolidation after each store")
    default_importance: float = Field(default=0.3, ge=0.0, le=1.0, description="Default importance for new memories")
    relevance_recency_weight: float = Field(default=0.3, ge=0.0, le=1.0, description="Weight for recency in relevance scoring")
    relevance_frequency_weight: float = Field(default=0.3, ge=0.0, le=1.0, description="Weight for access frequency in relevance scoring")
    relevance_importance_weight: float = Field(default=0.4, ge=0.0, le=1.0, description="Weight for importance in relevance scoring")
    search_default_limit: int = Field(default=10, ge=1, le=100, description="Default search result limit")

    model_config = {"env_prefix": "JARVIS_MEMORY_"}
