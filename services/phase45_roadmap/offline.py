"""
Phase 45 — Offline Manager.

Provides offline-first caching, sync, and cache management.
Uses mock implementations for network checks.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

from .config import RoadmapConfig

logger = logging.getLogger(__name__)


class CacheEntry:
    """A single cache entry with TTL tracking."""

    def __init__(self, key: str, value: Any, ttl_seconds: int = 86400):
        self.key = key
        self.value = value
        self.created_at = datetime.now(timezone.utc)
        self.expires_at = self.created_at + timedelta(seconds=ttl_seconds)
        self.access_count = 0

    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) >= self.expires_at

    @property
    def size_bytes(self) -> int:
        try:
            data = str(self.value)
            return len(data.encode("utf-8"))
        except Exception:
            return 0


class OfflineManager:
    """Manages offline caching, sync, and cache statistics.

    Usage:
        om = OfflineManager()
        om.cache_data('key1', 'value1', ttl_hours=24)
        value = om.get_cached('key1')
        stats = om.get_cache_stats()
    """

    def __init__(self, config: Optional[RoadmapConfig] = None):
        self.config = config or RoadmapConfig()
        self._cache: Dict[str, CacheEntry] = {}
        self._max_size_bytes = self.config.offline_cache_size_mb * 1024 * 1024

    def cache_data(self, key: str, value: Any, ttl_hours: int = 24) -> bool:
        """Cache data for offline access.

        Args:
            key: Cache key.
            value: Data to cache.
            ttl_hours: Time-to-live in hours.

        Returns:
            True if cached successfully, False if cache is full.
        """
        ttl_seconds = ttl_hours * 3600
        entry = CacheEntry(key, value, ttl_seconds)

        # Check if adding this would exceed cache size
        current_size = self._get_current_size()
        if current_size + entry.size_bytes > self._max_size_bytes:
            self._evict_oldest()
            current_size = self._get_current_size()
            if current_size + entry.size_bytes > self._max_size_bytes:
                logger.warning("Cache full, could not cache '%s'", key)
                return False

        self._cache[key] = entry
        logger.debug("Cached '%s' (ttl=%d hours, size=%d bytes)", key, ttl_hours, entry.size_bytes)
        return True

    def get_cached(self, key: str) -> Optional[Any]:
        """Get cached data by key.

        Args:
            key: Cache key.

        Returns:
            The cached value, or None if not found or expired.
        """
        entry = self._cache.get(key)
        if not entry:
            return None
        if entry.is_expired:
            del self._cache[key]
            return None
        entry.access_count += 1
        return entry.value

    def is_online(self) -> bool:
        """Check if the system is online (mock — always True).

        Returns:
            True if online, False otherwise.
        """
        return True

    def sync_when_online(self) -> int:
        """Attempt to sync cached data (mock).

        Returns:
            Number of items synced.
        """
        synced = len(self._cache)
        logger.info("Synced %d cached item(s)", synced)
        return synced

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dict with cache usage statistics.
        """
        total_size = self._get_current_size()
        active = sum(1 for e in self._cache.values() if not e.is_expired)
        expired = sum(1 for e in self._cache.values() if e.is_expired)
        return {
            "total_entries": len(self._cache),
            "active_entries": active,
            "expired_entries": expired,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "max_size_mb": self.config.offline_cache_size_mb,
            "usage_percent": round(total_size / self._max_size_bytes * 100, 1) if self._max_size_bytes > 0 else 0,
        }

    def clear_cache(self) -> int:
        """Clear all cached data.

        Returns:
            Number of entries cleared.
        """
        count = len(self._cache)
        self._cache.clear()
        logger.info("Cleared cache (%d entries)", count)
        return count

    def get_cached_keys(self) -> List[str]:
        """Get all cache keys."""
        return list(self._cache.keys())

    # ── Internal ──────────────────────────────────────────────────

    def _get_current_size(self) -> int:
        return sum(e.size_bytes for e in self._cache.values())

    def _evict_oldest(self) -> None:
        """Remove the oldest entry by creation time."""
        if not self._cache:
            return
        oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].created_at)
        del self._cache[oldest_key]
        logger.debug("Evicted oldest cache entry '%s'", oldest_key)
