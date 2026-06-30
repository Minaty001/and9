"""
Phase 22 — Real-Time Info Service.

ServiceBase wrapper for the real-time info engine.
"""

from __future__ import annotations

import time
import logging
from typing import Any, Dict, List, Optional

from services.base.service_base import ServiceBase
from .config import RealtimeConfig
from .models import InfoRequest, InfoResult
from .engine import RealtimeEngine
from .providers import MockWeatherProvider, MockNewsProvider, MockSearchProvider, TimeProvider

logger = logging.getLogger(__name__)


class RealtimeInfoService(ServiceBase):
    """Real-time information service aggregating weather, news, search, and time.

    Usage:
        svc = RealtimeInfoService()
        await svc.initialize()
        results = await svc.fetch(InfoRequest(query="weather in mumbai"))
    """

    def __init__(self, config: Optional[RealtimeConfig] = None):
        super().__init__(name="jarvis_realtime", version="1.0.0")
        self.config = config or RealtimeConfig()
        self.engine: Optional[RealtimeEngine] = None
        self._start_time = 0.0

    async def initialize(self) -> bool:
        """Initialize the real-time info service."""
        self._start_time = time.time()
        try:
            self.engine = RealtimeEngine(config=self.config)
            self.engine.register_provider("weather", MockWeatherProvider())
            self.engine.register_provider("news", MockNewsProvider())
            self.engine.register_provider("search", MockSearchProvider())
            self.engine.register_provider("time", TimeProvider())
            self._metrics.reset()
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

        self._metrics.counter("fetches", 1)
        t0 = time.perf_counter()
        results = self.engine.fetch(request)
        elapsed = (time.perf_counter() - t0) * 1000
        self._metrics.histogram("fetch_duration_ms", elapsed)
        self._metrics.counter("results_count", len(results))
        return results

    async def refresh(self) -> int:
        """Refresh all providers.

        Returns:
            Number of providers refreshed.
        """
        if not self._initialized or not self.engine:
            raise RuntimeError("RealtimeInfoService not initialized")
        count = self.engine.refresh()
        self._metrics.counter("refreshes", count)
        return count

    def get_providers(self) -> Dict[str, Any]:
        """Get all registered providers."""
        if not self.engine:
            raise RuntimeError("RealtimeInfoService not initialized")
        return self.engine.get_providers()

    async def health(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "service_name": self.name,
            "version": self.version,
            "initialized": self._initialized,
            "uptime_seconds": round(uptime, 1),
        }

    async def stats(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        provider_count = len(self.engine.get_providers()) if self.engine else 0
        return {
            "service": self.name,
            "version": self.version,
            "uptime_seconds": round(uptime, 1),
            "providers": provider_count,
            "metrics": self._metrics.snapshot(),
        }
