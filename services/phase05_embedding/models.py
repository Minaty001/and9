"""
Phase 5 — Embedding Models.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EmbeddingVector(BaseModel):
    """A single embedding vector with metadata."""

    vector: List[float] = Field(..., description="Embedding vector")
    dimension: int = Field(..., description="Vector dimension")
    text: str = Field(..., description="Source text")
    created_at: float = Field(default=0.0, description="Creation timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class SearchResult(BaseModel):
    """Result from a semantic search."""

    text: str = Field(..., description="Matched text")
    score: float = Field(..., ge=-1.0, le=1.0, description="Similarity score")
    vector: Optional[List[float]] = Field(default=None, description="Matched vector")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Result metadata")
