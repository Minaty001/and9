"""
Phase 40 — Performance Optimization Models.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class CacheEntry(BaseModel):
    """A single cache entry."""

    key: str = Field(..., description="Cache key")
    value: Any = Field(..., description="Cached value")
    size_bytes: int = Field(default=0, ge=0, description="Approximate size in bytes")
    cached_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = Field(default=None, description="Expiration timestamp")
    access_count: int = Field(default=0, ge=0, description="Number of times accessed")
    level: int = Field(default=1, ge=1, le=2, description="Cache level (1 or 2)")


class CacheStats(BaseModel):
    """Statistics for a cache."""

    cache_name: str = Field(..., description="Cache name")
    size: int = Field(default=0, ge=0, description="Current number of entries")
    capacity: int = Field(default=128, ge=1, description="Maximum capacity")
    hit_count: int = Field(default=0, ge=0, description="Number of cache hits")
    miss_count: int = Field(default=0, ge=0, description="Number of cache misses")
    hit_ratio: float = Field(default=0.0, ge=0.0, le=1.0, description="Hit ratio")
    oldest_entry_age: float = Field(default=0.0, ge=0.0, description="Age of oldest entry in seconds")
