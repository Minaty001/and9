"""
Performance — L2 Cache.

Larger LRU cache with TTL support.
Supports preload/warmup strategies.
"""

from __future__ import annotations

import time
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple
from collections import OrderedDict

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

    def __init__(self, capacity: int = 1024, ttl_seconds: int = 600,
                 warmup_strategy: str = "lazy"):
        self._capacity = capacity
        self._ttl = ttl_seconds
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._hit_count = 0
        self._miss_count = 0
        self._warmup_strategy = warmup_strategy

    def get(self, key: str) -> Tuple[Optional[Any], bool]:
        entry = self._cache.get(key)
        if entry is None:
            self._miss_count += 1
            return None, False

        if entry["expires_at"] is not None and time.time() > entry["expires_at"]:
            del self._cache[key]
            self._miss_count += 1
            return None, False

        self._cache.move_to_end(key)
        entry["access_count"] += 1
        self._hit_count += 1
        return entry["value"], True

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
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
        if self._warmup_strategy == "lazy":
            return 0
        return self.preload(keys, loader_func, ttl)

    def invalidate(self, key: str) -> bool:
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self) -> None:
        self._cache.clear()
        self._hit_count = 0
        self._miss_count = 0

    def stats(self) -> CacheStats:
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
