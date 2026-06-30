"""
Phase 9 — Memory Models.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    """Type of memory storage."""
    LONG_TERM = "long_term"
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"


class MemoryItem(BaseModel):
    """A single stored memory."""

    key: str = Field(..., description="Unique memory key")
    value: Any = Field(..., description="Memory value (string, dict, number, etc.)")
    memory_type: MemoryType = Field(default=MemoryType.WORKING, description="Type of memory")
    importance: float = Field(default=0.3, ge=0.0, le=1.0, description="Importance score 0-1")
    access_count: int = Field(default=0, description="Number of times accessed")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_accessed: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    embedding: Optional[List[float]] = Field(default=None, description="Optional embedding vector")

    def touch(self) -> None:
        """Record an access."""
        self.access_count += 1
        self.last_accessed = datetime.now(timezone.utc)

    def age_seconds(self) -> float:
        """Seconds since creation."""
        return (datetime.now(timezone.utc) - self.created_at).total_seconds()


class MemoryQuery(BaseModel):
    """Query parameters for memory retrieval."""

    text: str = Field(default="", description="Text to match against keys/tags")
    memory_type: Optional[MemoryType] = Field(default=None, description="Filter by memory type")
    tags: List[str] = Field(default_factory=list, description="Filter by tags (any match)")
    min_importance: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum importance threshold")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum results")


class MemoryStats(BaseModel):
    """Memory system statistics."""

    total_items: int = Field(default=0)
    working_count: int = Field(default=0)
    long_term_count: int = Field(default=0)
    episodic_count: int = Field(default=0)
    semantic_count: int = Field(default=0)
    avg_importance: float = Field(default=0.0)
    total_accesses: int = Field(default=0)
    oldest_memory_age_seconds: float = Field(default=0.0)
