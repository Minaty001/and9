"""
Phase 40 — L2 Cache.

Larger distributed LRU cache with TTL support.
Supports preload/warmup strategies.
"""

from __future__ import annotations

import time
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple
from collections import OrderedDict

from .config import PerformanceConfig
from .models import CacheStats

logger = logging.getLogger(__name__)


class L2Cache:
    """Larger LRU cache (Level 2).

    Usage:
        cache = L2Cache(capacity=1024)
        cache.set("key", "value", ttl_seconds=600)
        value, hit = cache.get("key")
        cache.preload(["a", "b"], loader_func)
    """

    def __init__(self, config: Optional[PerformanceConfig] = None):
        self.config = config or PerformanceConfig()
        self._capacity = self.config.l2_cache_size
        self._ttl = self.config.l2_cache_ttl_seconds
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._hit_count = 0
        self._miss_count = 0
        self._warmup_strategy = self.config.warmup_strategy

    def get(self, key: str) -> Tuple[Optional[Any], bool]:
        """Get a value from cache.

        Returns:
            Tuple of (value, hit).
        """
        entry = self._cache.get(key)
        if entry is None:
            self._miss_count += 1
            return None, False

        # Check TTL
        if entry["expires_at"] is not None and time.time() > entry["expires_at"]:
            del self._cache[key]
            self._miss_count += 1
            return None, False

        self._cache.move_to_end(key)
        entry["access_count"] += 1
        self._hit_count += 1
        return entry["value"], True

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set a value in cache."""
        if key in self._cache:
            self._cache.move_to_end(key)

        expires_at = None
        ttl_sec = ttl if ttl is not None else self._ttl
        if ttl_sec > 0:
            expires_at = time.time() + ttl_sec

        self._cache[key] = {
            "value": value,
            "expires_at": expires_at,
            "access_count": 0,
            "created_at": time.time(),
        }

        while len(self._cache) > self._capacity:
            self._cache.popitem(last=False)

    def preload(self, keys: List[str], loader_func: Callable[[str], Any],
                ttl: Optional[int] = None) -> int:
        """Preload multiple keys in batch.

        Args:
            keys: List of keys to load.
            loader_func: Function that takes a key and returns a value.
            ttl: Optional TTL in seconds.

        Returns:
            Number of keys successfully loaded.
        """
        loaded = 0
        for key in keys:
            if key in self._cache:
                continue
            try:
                value = loader_func(key)
                self.set(key, value, ttl)
                loaded += 1
            except Exception as e:
                logger.warning("Failed to preload key '%s': %s", key, e)
        if loaded:
            logger.debug("Preloaded %d/%d keys into L2 cache", loaded, len(keys))
        return loaded

    def warmup(self, keys: List[str], loader_func: Callable[[str], Any],
               ttl: Optional[int] = None) -> int:
        """Warm up the cache by preloading keys.

        Respects the configured warmup_strategy: under "lazy" strategy,
        this is a no-op. Under "eager" or "predictive", keys are loaded.

        Args:
            keys: List of keys to preload.
            loader_func: Function that takes a key and returns a value.
            ttl: Optional TTL in seconds.

        Returns:
            Number of keys loaded (0 if strategy is "lazy").
        """
        if self._warmup_strategy == "lazy":
            return 0
        return self.preload(keys, loader_func, ttl)

    def invalidate(self, key: str) -> bool:
        """Invalidate a cache entry."""
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        self._hit_count = 0
        self._miss_count = 0

    def stats(self) -> CacheStats:
        """Get cache statistics."""
        total = self._hit_count + self._miss_count
        oldest_age = 0.0
        if self._cache:
            oldest_key = next(iter(self._cache))
            oldest_entry = self._cache[oldest_key]
            oldest_age = time.time() - oldest_entry["created_at"]

        return CacheStats(
            cache_name="L2",
            size=len(self._cache),
            capacity=self._capacity,
            hit_count=self._hit_count,
            miss_count=self._miss_count,
            hit_ratio=round(self._hit_count / max(total, 1), 4),
            oldest_entry_age=round(oldest_age, 2),
        )
