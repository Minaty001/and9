"""
Phase 20 — Search Engine Models.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    """A single search result item."""

    id: str = Field(..., description="Unique result identifier")
    title: str = Field(..., description="Result title")
    snippet: str = Field(default="", description="Text snippet")
    url: Optional[str] = Field(default=None, description="Source URL")
    source: str = Field(default="web", description="Source type: web/memory/document")
    score: float = Field(default=1.0, ge=0.0, le=1.0, description="Relevance score 0-1")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SearchQuery(BaseModel):
    """A search query with filters and options."""

    text: str = Field(..., description="Search query text")
    intent: Optional[str] = Field(default=None, description="Detected search intent")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Search filters")
    max_results: int = Field(default=20, ge=1, le=100, description="Maximum results")
    sources: List[str] = Field(default_factory=list, description="Sources to search (empty = all)")
    min_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum result score")
