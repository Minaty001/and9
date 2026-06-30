"""
Performance — Data Models.

CacheEntry, CacheStats as plain Python classes.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional


class CacheEntry:
    """A single cache entry."""

    def __init__(self, key: str, value: Any, size_bytes: int = 0,
                 created_at: Optional[datetime] = None,
                 expires_at: Optional[datetime] = None,
                 access_count: int = 0, level: int = 1):
        self.key = key
        self.value = value
        self.size_bytes = size_bytes
        self.cached_at = created_at or datetime.now(timezone.utc)
        self.expires_at = expires_at
        self.access_count = access_count
        self.level = level


class CacheStats:
    """Statistics for a cache."""

    def __init__(self, cache_name: str, size: int = 0, capacity: int = 128,
                 hit_count: int = 0, miss_count: int = 0,
                 hit_ratio: float = 0.0, oldest_entry_age: float = 0.0):
        self.cache_name = cache_name
        self.size = size
        self.capacity = capacity
        self.hit_count = hit_count
        self.miss_count = miss_count
        self.hit_ratio = hit_ratio
        self.oldest_entry_age = oldest_entry_age
