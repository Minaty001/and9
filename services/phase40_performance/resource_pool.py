"""
Phase 40 — Resource Pool.

Pool reusable resources (connections, workers, etc.).
"""

from __future__ import annotations

import time
import uuid
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple
from collections import OrderedDict

from .config import PerformanceConfig

logger = logging.getLogger(__name__)


class ResourcePool:
    """Pool of reusable resources.

    Usage:
        pool = ResourcePool(creator=lambda: create_connection())
        resource, rid = pool.acquire()
        pool.release(rid)
    """

    def __init__(self, config: Optional[PerformanceConfig] = None,
                 creator: Optional[Callable[[], Any]] = None,
                 resetter: Optional[Callable[[Any], None]] = None,
                 destroyer: Optional[Callable[[Any], None]] = None):
        self.config = config or PerformanceConfig()
        self._creator = creator or (lambda: {})
        self._resetter = resetter
        self._destroyer = destroyer
        self._max_size = self.config.pool_max_size
        self._idle_timeout = self.config.pool_idle_timeout

        self._available: OrderedDict[str, Tuple[Any, float]] = OrderedDict()  # id -> (resource, idle_since)
        self._active: Dict[str, Any] = {}  # id -> resource
        self._total_created = 0
        self._total_destroyed = 0
        self._total_acquired = 0
        self._total_released = 0

    def acquire(self) -> Tuple[Optional[Any], Optional[str]]:
        """Acquire a resource from the pool.

        Returns:
            Tuple of (resource, resource_id) or (None, None) if pool exhausted.
        """
        # Check for idle resources
        self._evict_expired()

        if self._available:
            rid, (resource, _) = self._available.popitem(last=False)
            self._active[rid] = resource
            self._total_acquired += 1
            return resource, rid

        # Create new resource if under max
        if self._total_created - self._total_destroyed < self._max_size and self._creator:
            rid = uuid.uuid4().hex[:12]
            resource = self._creator()
            self._active[rid] = resource
            self._total_created += 1
            self._total_acquired += 1
            return resource, rid

        return None, None

    def release(self, rid: str) -> bool:
        """Release a resource back to the pool.

        Returns True if released.
        """
        resource = self._active.pop(rid, None)
        if resource is None:
            return False

        if self._resetter:
            try:
                self._resetter(resource)
            except Exception as e:
                logger.warning("Failed to reset resource '%s': %s", rid, e)

        self._available[rid] = (resource, time.time())
        self._total_released += 1
        return True

    def stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        self._evict_expired()
        return {
            "available": len(self._available),
            "active": len(self._active),
            "total_created": self._total_created,
            "total_destroyed": self._total_destroyed,
            "total_acquired": self._total_acquired,
            "total_released": self._total_released,
            "max_size": self._max_size,
            "idle_timeout": self._idle_timeout,
        }

    def _evict_expired(self):
        """Evict idle resources that have exceeded idle timeout."""
        now = time.time()
        expired_ids = []
        for rid, (resource, idle_since) in self._available.items():
            if now - idle_since > self._idle_timeout:
                expired_ids.append(rid)
                if self._destroyer:
                    try:
                        self._destroyer(resource)
                    except Exception as e:
                        logger.warning("Failed to destroy resource '%s': %s", rid, e)
                self._total_destroyed += 1

        for rid in expired_ids:
            del self._available[rid]

        if expired_ids:
            logger.debug("Evicted %d expired idle resources", len(expired_ids))
