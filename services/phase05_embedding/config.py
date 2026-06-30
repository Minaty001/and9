"""
Phase 5 — Embedding Engine Configuration.
"""

from pydantic import Field
from services.base.config_base import BaseConfig


class EmbeddingConfig(BaseConfig):
    """Configuration for the embedding engine."""

    service_name: str = Field(default="jarvis_embedding", description="Embedding service name")
    embedding_dim: int = Field(default=128, description="Embedding vector dimension")
    cache_size: int = Field(default=500, description="Max cache entries")
    cache_ttl_seconds: int = Field(default=300, description="Cache TTL in seconds")
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Similarity threshold for matching")
    max_batch_size: int = Field(default=64, description="Max batch embedding size")

    class Config:
        env_prefix = "JARVIS_EMBED_"
