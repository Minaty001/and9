"""
Phase 22 — Real-Time Info Engine Models.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class InfoSource(BaseModel):
    """An information source configuration."""

    source_type: str = Field(..., description="Source type: weather/news/search/time")
    name: str = Field(..., description="Human-readable source name")
    priority: int = Field(default=10, ge=0, le=100, description="Source priority (lower = higher)")
    enabled: bool = Field(default=True, description="Whether this source is enabled")
    cache_ttl: int = Field(default=120, ge=0, description="Cache TTL in seconds for this source")


class InfoRequest(BaseModel):
    """A request for real-time information."""

    query: str = Field(..., description="The information query string")
    source_types: List[str] = Field(default_factory=list, description="Source types to query (empty = all)")
    max_age_seconds: Optional[int] = Field(default=None, description="Maximum age of acceptable results")
    max_results: int = Field(default=5, ge=1, le=50, description="Maximum number of results")
    require_fresh: bool = Field(default=False, description="Force fresh fetch, bypassing cache")


class InfoResult(BaseModel):
    """A single information result from a source."""

    source: str = Field(..., description="Name of the source that produced this result")
    query: str = Field(..., description="Original query")
    data: Dict[str, Any] = Field(default_factory=dict, description="Result data payload")
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    freshness_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Freshness score 0-1")
    cache_hit: bool = Field(default=False, description="Whether result was from cache")
