"""
Performance — Lazy Loader.

Cache loaded results on demand with loading statistics.
"""

from __future__ import annotations

import time
import logging
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class LazyLoader:
    """Lazily load and cache values on demand.

    Usage:
        loader = LazyLoader()
        value = loader.load("my_key", lambda: expensive_computation())
    """

    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._loading_stats: Dict[str, Dict[str, Any]] = {}
        self._total_loaded = 0
        self._total_hits = 0
        self._total_load_time_ms = 0.0

    def load(self, key: str, loader_func: Callable[[], Any]) -> Any:
        """Load a value, caching it on first access."""
        if key in self._cache:
            self._total_hits += 1
            if key in self._loading_stats:
                self._loading_stats[key]["access_count"] += 1
            return self._cache[key]

        t0 = time.perf_counter()
        try:
            value = loader_func()
            elapsed = (time.perf_counter() - t0) * 1000
            self._cache[key] = value
            self._total_loaded += 1
            self._total_load_time_ms += elapsed

            self._loading_stats[key] = {
                "load_time_ms": round(elapsed, 3),
                "access_count": 1,
                "loaded_at": time.time(),
            }
            logger.debug("Lazy-loaded: %s (%.2f ms)", key, elapsed)
            return value
        except Exception as e:
            elapsed = (time.perf_counter() - t0) * 1000
            logger.error("Failed to load '%s' after %.2f ms: %s", key, elapsed, e)
            raise

    def is_loaded(self, key: str) -> bool:
        return key in self._cache

    def invalidate(self, key: str) -> bool:
        if key in self._cache:
            del self._cache[key]
            self._loading_stats.pop(key, None)
            return True
        return False

    def clear(self) -> None:
        self._cache.clear()
        self._loading_stats.clear()
        self._total_loaded = 0
        self._total_hits = 0
        self._total_load_time_ms = 0.0

    def get_stats(self) -> Dict[str, Any]:
        return {
            "cached_items": len(self._cache),
            "total_loaded": self._total_loaded,
            "total_hits": self._total_hits,
            "total_load_time_ms": round(self._total_load_time_ms, 2),
            "average_load_time_ms": round(
                self._total_load_time_ms / max(self._total_loaded, 1), 2
            ),
        }
