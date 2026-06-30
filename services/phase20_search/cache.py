"""
Phase 20 — Search Cache.

LRU cache with TTL support for search results.
"""

import time
from typing import Any, Dict, List, Optional, Tuple
from collections import OrderedDict

from .models import SearchResult


class SearchCache:
    """LRU cache with TTL for search results.

    Supports get, set, invalidate, clear operations.
    """

    def __init__(self, default_ttl: int = 300, max_size: int = 100):
        self._default_ttl = default_ttl
        self._max_size = max_size
        self._cache: OrderedDict[str, Tuple[List[SearchResult], float]] = OrderedDict()

    def get(self, key: str) -> Optional[List[SearchResult]]:
        """Get cached results for a key.

        Args:
            key: Cache key (typically the query string).

        Returns:
            Cached results if found and not expired, None otherwise.
        """
        if key not in self._cache:
            return None

        results, expiry = self._cache[key]
        if time.time() > expiry:
            del self._cache[key]
            return None

        # Move to end (most recently used)
        self._cache.move_to_end(key)
        return results

    def set(self, key: str, results: List[SearchResult], ttl: Optional[int] = None) -> bool:
        """Store results in cache.

        Args:
            key: Cache key.
            results: List of SearchResult to cache.
            ttl: Time-to-live in seconds (defaults to instance default).

        Returns:
            True if stored successfully.
        """
        ttl = ttl if ttl is not None else self._default_ttl
        expiry = time.time() + ttl
        self._cache[key] = (list(results), expiry)
        self._cache.move_to_end(key)

        # Evict oldest if over max size
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
