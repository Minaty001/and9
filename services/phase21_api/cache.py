"""
Phase 21 — API Cache.

LRU cache with TTL support for API responses.
"""

import time
from typing import Any, Dict, List, Optional, Tuple
from collections import OrderedDict

from .models import ApiResponse


class ApiCache:
    """LRU cache with TTL for API responses.

    Supports get, set, invalidate, clear operations.
    """

    def __init__(self, default_ttl: int = 300, max_size: int = 200):
        self._default_ttl = default_ttl
        self._max_size = max_size
        self._cache: OrderedDict[str, Tuple[ApiResponse, float]] = OrderedDict()

    def get(self, key: str) -> Optional[ApiResponse]:
        """Get cached response for a key.

        Args:
            key: Cache key.

        Returns:
            Cached response if found and not expired, None otherwise.
        """
        if key not in self._cache:
            return None

        response, expiry = self._cache[key]
        if time.time() > expiry:
            del self._cache[key]
            return None

        # Mark as recently used
        self._cache.move_to_end(key)
        return response

    def set(self, key: str, response: ApiResponse, ttl: Optional[int] = None) -> bool:
        """Store a response in cache.

        Args:
            key: Cache key.
            response: ApiResponse to cache.
            ttl: Time-to-live in seconds (defaults to instance default).

        Returns:
            True if stored successfully.
        """
        ttl = ttl if ttl is not None else self._default_ttl
        expiry = time.time() + ttl
        self._cache[key] = (response, expiry)
        self._cache.move_to_end(key)

        while len(self._cache) > self._max_size:
            self._cache.popitem(last=False)

        return True

    def invalidate(self, key: str) -> bool:
        """Invalidate a cached entry.

        Args:
            key: Cache key to invalidate.

        Returns:
            True if an entry was removed.
        """
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self) -> int:
        """Clear all cached entries.

        Returns:
            Number of entries cleared.
        """
        count = len(self._cache)
        self._cache.clear()
        return count

    @property
    def size(self) -> int:
        """Current number of cached entries."""
        return len(self._cache)

    def keys(self) -> List[str]:
        """Return all cache keys."""
        return list(self._cache.keys())
