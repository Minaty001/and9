"""
app/services/realtime/service.py — Real-Time Info Service.

Service wrapper for the real-time info engine with
initialize/shutdown/health/stats lifecycle.
"""

from __future__ import annotations

import time
import logging
from typing import Any, Dict, List, Optional

from .models import InfoRequest, InfoResult
from .engine import RealtimeEngine
from .providers import MockWeatherProvider, MockNewsProvider, MockSearchProvider, TimeProvider

logger = logging.getLogger(__name__)


class RealtimeInfoService:
    """Real-time information service aggregating weather, news, search, and time.

    Usage:
        svc = RealtimeInfoService()
        await svc.initialize()
        results = await svc.fetch(InfoRequest(query="weather in mumbai"))

    Follows the Service lifecycle pattern: initialize/shutdown/health/stats.
    """

    def __init__(self, cache_ttl: int = 120, freshness_timeout_ms: int = 3000):
        self._cache_ttl = cache_ttl
        self._freshness_timeout_ms = freshness_timeout_ms
        self.engine: Optional[RealtimeEngine] = None
        self._initialized = False
        self._start_time = 0.0
        self._stats = {
            "fetches": 0,
            "refreshes": 0,
            "results_count": 0,
            "fetch_duration_ms": [],
        }

    async def initialize(self) -> bool:
        """Initialize the real-time info service with default providers."""
        self._start_time = time.time()
        try:
            self.engine = RealtimeEngine(
                cache_ttl=self._cache_ttl,
                freshness_timeout_ms=self._freshness_timeout_ms,
            )
            self.engine.register_provider("weather", MockWeatherProvider())
            self.engine.register_provider("news", MockNewsProvider())
            self.engine.register_provider("search", MockSearchProvider())
            self.engine.register_provider("time", TimeProvider())
            self._initialized = True
            logger.info("RealtimeInfoService initialized")
            return True
        except Exception as e:
            logger.error("RealtimeInfoService init failed: %s", e)
            return False

    async def shutdown(self) -> None:
        """Shut down the real-time info service."""
        logger.info("RealtimeInfoService shutting down...")
        self._initialized = False

    async def fetch(self, request: InfoRequest) -> List[InfoResult]:
        """Fetch real-time information from registered providers.

        Args:
            request: The information request.

        Returns:
            List of InfoResult objects.
        """
        if not self._initialized or not self.engine:
            raise RuntimeError("RealtimeInfoService not initialized")

        self._stats["fetches"] += 1
        t0 = time.perf_counter()
        results = self.engine.fetch(request)
        elapsed = (time.perf_counter() - t0) * 1000
        self._stats["fetch_duration_ms"].append(elapsed)
        self._stats["results_count"] += len(results)
        return results

    async def refresh(self) -> int:
        """Refresh all providers.

        Returns:
            Number of providers refreshed.
        """
        if not self._initialized or not self.engine:
            raise RuntimeError("RealtimeInfoService not initialized")
        count = self.engine.refresh()
        self._stats["refreshes"] += count
        return count

    def get_providers(self) -> Dict[str, Any]:
        """Get all registered providers."""
        if not self.engine:
            raise RuntimeError("RealtimeInfoService not initialized")
        return self.engine.get_providers()

    async def health(self) -> Dict[str, Any]:
        """Return current health status."""
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "service_name": "jarvis_realtime",
            "initialized": self._initialized,
            "uptime_seconds": round(uptime, 1),
        }

    async def stats(self) -> Dict[str, Any]:
        """Return service statistics."""
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        provider_count = len(self.engine.get_providers()) if self.engine else 0
        avg_duration = (
            sum(self._stats["fetch_duration_ms"]) / len(self._stats["fetch_duration_ms"])
            if self._stats["fetch_duration_ms"]
            else 0
        )
        return {
            "service": "jarvis_realtime",
            "uptime_seconds": round(uptime, 1),
            "providers": provider_count,
            "fetches": self._stats["fetches"],
            "refreshes": self._stats["refreshes"],
            "results_count": self._stats["results_count"],
            "avg_fetch_duration_ms": round(avg_duration, 2),
        }
