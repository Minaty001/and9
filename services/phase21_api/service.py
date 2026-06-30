"""
Phase 21 — API Manager Service.

ServiceBase wrapper for centralized API integration with adapters,
caching, rate limiting, and fallback.
"""

from __future__ import annotations

import time
import logging
from typing import Any, Dict, List, Optional

from services.base.service_base import ServiceBase
from .config import ApiConfig
from .models import ApiRequest, ApiResponse
from .adapter import ApiAdapter, MockHttpAdapter
from .cache import ApiCache

logger = logging.getLogger(__name__)


class ApiManagerService(ServiceBase):
    """Centralized API manager service supporting adapters, caching, and retries.

    Usage:
        svc = ApiManagerService()
        await svc.initialize()
        response = await svc.execute(ApiRequest(endpoint="/api/data"))
    """

    def __init__(self, config: Optional[ApiConfig] = None):
        super().__init__(name="jarvis_api", version="1.0.0")
        self.config = config or ApiConfig()
        self.cache: Optional[ApiCache] = None
        self._adapters: Dict[str, ApiAdapter] = {}
        self._start_time = 0.0

    async def initialize(self) -> bool:
        """Initialize the API manager."""
        self._start_time = time.time()
        try:
            self.cache = ApiCache(
                default_ttl=self.config.cache_ttl_seconds,
            )
            self._metrics.reset()
            self._initialized = True
            logger.info("ApiManagerService initialized")
            return True
        except Exception as e:
            logger.error("ApiManagerService init failed: %s", e)
            return False

    async def shutdown(self) -> None:
        """Shut down the API manager."""
        logger.info("ApiManagerService shutting down...")
        self._adapters.clear()
        self._initialized = False

    async def execute(self, request: ApiRequest) -> ApiResponse:
        """Execute an API request through the appropriate adapter.

        If an adapter_name is specified, uses that adapter.
        Otherwise falls back to the first available adapter.

        Args:
            request: The API request to execute.

        Returns:
            ApiResponse with the result.
        """
        if not self._initialized:
            raise RuntimeError("ApiManagerService not initialized")

        # Check cache
        cache_key = self._make_cache_key(request)
        if self.config.enable_caching and self.cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                self._metrics.counter("cache_hits", 1)
                cached.cached = True
                return cached

        t0 = time.perf_counter()
        self._metrics.counter("requests_total", 1)

        # Resolve adapter
        adapter = self._resolve_adapter(request)

        if not adapter:
            self._metrics.counter("errors", 1)
            return ApiResponse(
                success=False,
                status_code=503,
                error="No adapter available for request",
            )

        response = adapter.execute(request)
        elapsed = (time.perf_counter() - t0) * 1000
        self._metrics.histogram("request_duration_ms", elapsed)

        if response.success:
            self._metrics.counter("successes", 1)
            # Cache successful responses
            if self.config.enable_caching and self.cache:
                self.cache.set(cache_key, response)
        else:
            self._metrics.counter("errors", 1)
            # Try fallback adapters if enabled
            if self.config.fallback_enabled:
                fallback_response = self._try_fallback(request)
                if fallback_response and fallback_response.success:
                    self._metrics.counter("fallback_successes", 1)
                    return fallback_response

        return response

    def register_adapter(self, name: str, adapter: ApiAdapter) -> None:
        """Register an adapter by name.

        Args:
            name: Name for the adapter.
            adapter: ApiAdapter instance.
        """
        self._adapters[name] = adapter
        logger.info("Registered adapter: %s", name)

    async def get_cached(self, key: str) -> Optional[ApiResponse]:
        """Get a cached response by cache key.

        Args:
            key: Cache key.

        Returns:
            Cached ApiResponse if found, None otherwise.
        """
        if not self.cache:
            raise RuntimeError("ApiManagerService not initialized")
        return self.cache.get(key)

    async def clear_cache(self) -> int:
        """Clear all cached responses.

        Returns:
            Number of entries cleared.
        """
        if not self.cache:
            raise RuntimeError("ApiManagerService not initialized")
        return self.cache.clear()

    async def invalidate_cache(self, key: str) -> bool:
        """Invalidate a specific cache entry.

        Args:
            key: Cache key to invalidate.

        Returns:
            True if an entry was removed.
        """
        if not self.cache:
            raise RuntimeError("ApiManagerService not initialized")
        return self.cache.invalidate(key)

    def list_adapters(self) -> List[str]:
        """List registered adapter names."""
        return list(self._adapters.keys())

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
        return {
            "service": self.name,
            "version": self.version,
            "uptime_seconds": round(uptime, 1),
            "adapters": list(self._adapters.keys()),
            "cache_size": self.cache.size if self.cache else 0,
            "metrics": self._metrics.snapshot(),
        }

    def _resolve_adapter(self, request: ApiRequest) -> Optional[ApiAdapter]:
        """Resolve the adapter for a request."""
        if request.adapter_name and request.adapter_name in self._adapters:
            return self._adapters[request.adapter_name]
        if self._adapters:
            return next(iter(self._adapters.values()))
        return None

    def _try_fallback(self, request: ApiRequest) -> Optional[ApiResponse]:
        """Try fallback adapters in order."""
        for name, adapter in self._adapters.items():
            if request.adapter_name and name == request.adapter_name:
                continue
            try:
                resp = adapter.execute(request)
                if resp.success:
                    return resp
            except Exception:
                continue
        return None

    def _make_cache_key(self, request: ApiRequest) -> str:
        """Create a cache key from a request."""
        return f"{request.method}:{request.endpoint}:{str(request.params)}"
