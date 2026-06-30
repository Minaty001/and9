"""
Phase 3 — Query Understanding Configuration.
"""

from pydantic import Field
from services.base.config_base import BaseConfig


class QueryConfig(BaseConfig):
    """Configuration for the query understanding pipeline."""

    service_name: str = Field(default="jarvis_query", description="Query service name")
    min_confidence_to_act: float = Field(default=0.7, ge=0.0, le=1.0, description="Min confidence to execute")
    clarification_confidence_threshold: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Below this, request clarification",
    )
    max_query_length: int = Field(default=500, description="Max input query length")
    enable_fallback: bool = Field(default=True, description="Enable fallback to clarification")
    pipeline_timeout_ms: float = Field(default=5000.0, description="Max pipeline execution time")

    class Config:
        env_prefix = "JARVIS_QUERY_"
