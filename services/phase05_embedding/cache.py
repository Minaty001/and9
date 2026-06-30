"""
Phase 5 — Embedding Cache.

LRU cache for generated embeddings with TTL expiration.
"""

import time
import threading
import logging
from typing import Dict, List, Optional, Tuple

from .errors import EmbeddingCacheError

logger = logging.getLogger(__name__)


class EmbeddingCache:
    """Thread-safe LRU cache for embedding vectors with TTL.

    Usage:
        cache = EmbeddingCache(max_size=500, ttl_seconds=300)
        cache.put("hello", [0.1, 0.2, ...])
        vector = cache.get("hello")  # returns vector or None
        stats = cache.get_stats()
    """

    def __init__(self, max_size: int = 500, ttl_seconds: int = 300):
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._lock = threading.RLock()
        self._cache: Dict[str, Tuple[List[float], float]] = {}  # text -> (vector, expiry)
        self._access_order: List[str] = []  # LRU tracking
        self._hits = 0
        self._misses = 0

    def get(self, text: str) -> Optional[List[float]]:
        """Retrieve a cached embedding.

        Args:
            text: The source text (cache key).

        Returns:
            The embedding vector if found and not expired, else None.
        """
        with self._lock:
            entry = self._cache.get(text)
            if entry is None:
                self._misses += 1
                return None

            vector, expiry = entry
            if time.time() > expiry:
                # Expired
                self._cache.pop(text, None)
                self._remove_from_access(text)
                self._misses += 1
                return None

            # Update LRU
            self._remove_from_access(text)
            self._access_order.append(text)
            self._hits += 1
            return vector

    def put(self, text: str, vector: List[float]) -> None:
        """Store an embedding in the cache.

        Args:
            text: The source text (cache key).
            vector: The embedding vector.
        """
        with self._lock:
            expiry = time.time() + self._ttl
            self._cache[text] = (vector, expiry)
            self._remove_from_access(text)
            self._access_order.append(text)

            # Evict oldest if over max size
            while len(self._cache) > self._max_size:
                oldest = self._access_order.pop(0) if self._access_order else None
                if oldest and oldest in self._cache:
                    del self._cache[oldest]
                    logger.debug("Evicted '%s' from embedding cache", oldest)

    def invalidate(self, text: str) -> None:
        """Remove a specific entry from the cache."""
        with self._lock:
            self._cache.pop(text, None)
            self._remove_from_access(text)

    def clear(self) -> None:
        """Clear all cached embeddings."""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
            self._hits = 0
            self._misses = 0

    def get_stats(self) -> dict:
        """Return cache statistics."""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = self._hits / total if total > 0 else 0.0
            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "ttl_seconds": self._ttl,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(hit_rate, 3),
            }

    def _remove_from_access(self, text: str) -> None:
        """Remove text from the access order list."""
        try:
            self._access_order.remove(text)
        except ValueError:
            pass

    @property
    def size(self) -> int:
        """Current number of cached entries."""
        with self._lock:
            return len(self._cache)
