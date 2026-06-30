"""
Phase 27 — Knowledge Base Models.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class KnowledgeEntry(BaseModel):
    """A single knowledge entry."""

    id: str = Field(..., description="Unique entry identifier")
    question: str = Field(..., description="Question or trigger phrase")
    answer: str = Field(..., description="Answer or response")
    category: str = Field(default="general", description="Knowledge category")
    tags: List[str] = Field(default_factory=list, description="Tags for organization")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score")
    source: str = Field(default="manual", description="Source of knowledge")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    access_count: int = Field(default=0, ge=0, description="Times accessed")
    linked_entries: List[str] = Field(default_factory=list, description="Linked entry IDs")


class KnowledgeQuery(BaseModel):
    """A query against the knowledge base."""

    query: str = Field(..., description="Search query text")
    category: Optional[str] = Field(default=None, description="Category filter")
    tags: List[str] = Field(default_factory=list, description="Tag filters")
    min_confidence: float = Field(default=0.3, ge=0.0, le=1.0, description="Minimum confidence")
    max_results: int = Field(default=10, ge=1, le=100, description="Max results to return")


class KnowledgeResult(BaseModel):
    """Result of a knowledge query."""

    entries: List[KnowledgeEntry] = Field(default_factory=list, description="Matching entries")
    query: str = Field(..., description="Original query")
    total_found: int = Field(default=0, description="Total matches found")
    search_time_ms: float = Field(default=0.0, description="Search time in milliseconds")
    confidence_scores: Dict[str, float] = Field(default_factory=dict, description="Per-entry confidence scores")
