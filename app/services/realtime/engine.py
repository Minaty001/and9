"""
app/services/realtime/engine.py — Realtime Engine.

Core engine that fetches info from multiple providers, checks freshness,
and merges results.
"""

import time
import logging
from typing import Any, Dict, List, Optional, Tuple

from .models import InfoRequest, InfoResult

logger = logging.getLogger(__name__)


class RealtimeEngine:
    """Core engine for fetching and merging real-time information from multiple sources.

    Manages InfoSource registration, caching with TTL, freshness checking,
    and provider orchestration.
    """

    def __init__(self, cache_ttl: int = 120, freshness_timeout_ms: int = 3000):
        self._cache_ttl = cache_ttl
        self._freshness_timeout_ms = freshness_timeout_ms
        self._providers: Dict[str, Any] = {}
        self._cache: Dict[str, Tuple[float, InfoResult]] = {}

    def register_provider(self, source_type: str, provider: Any) -> None:
        """Register a provider for a source type.

        Args:
            source_type: The source type (weather, news, search, time).
            provider: Provider instance with get_data(request) method.
        """
        self._providers[source_type] = provider
        logger.info("Registered provider for source type: %s", source_type)

    def get_providers(self) -> Dict[str, Any]:
        """Get all registered providers."""
        return dict(self._providers)

    def _cache_key(self, source_type: str, query: str) -> str:
        """Build a cache key for a source type and query."""
        return f"{source_type}:{query}"

    def _is_cache_valid(self, cached_at: float) -> bool:
        """Check if a cached entry is still valid based on TTL."""
        return (time.time() - cached_at) < self._cache_ttl

    def fetch(self, request: InfoRequest) -> List[InfoResult]:
        """Fetch information from relevant providers.

        Args:
            request: The info request.

        Returns:
            List of InfoResult objects from matching providers.
        """
        results: List[InfoResult] = []
        source_types = request.source_types or list(self._providers.keys())

        for stype in source_types:
            if stype not in self._providers:
                logger.warning("No provider registered for source type: %s", stype)
                continue

            # Check cache first (unless require_fresh is set)
            ckey = self._cache_key(stype, request.query)
            if not request.require_fresh and ckey in self._cache:
                cached_at, cached_result = self._cache[ckey]
                if self._is_cache_valid(cached_at):
                    cached_result.cache_hit = True
                    results.append(cached_result)
                    continue

            provider = self._providers[stype]
            try:
                t0 = time.perf_counter()
                result = provider.get_data(request)
                elapsed = (time.perf_counter() - t0) * 1000

                # Check freshness timeout
                if elapsed > self._freshness_timeout_ms:
                    logger.warning(
                        "Provider %s exceeded freshness timeout: %.2fms", stype, elapsed,
                    )
                    result.freshness_score = max(0.0, result.freshness_score - 0.2)

                # Cache the result
                self._cache[ckey] = (time.time(), result)

                results.append(result)
            except Exception as e:
                logger.error("Provider %s error: %s", stype, e)

        # Sort by freshness score descending
        results.sort(key=lambda r: r.freshness_score, reverse=True)

        # Apply max results
        if request.max_results and len(results) > request.max_results:
            results = results[:request.max_results]

        return results

    def refresh(self) -> int:
        """Refresh all providers (clear any internal caches).

        Returns:
            Number of providers refreshed.
        """
        self._cache.clear()
        count = 0
        for stype, provider in self._providers.items():
            if hasattr(provider, 'refresh'):
                try:
                    provider.refresh()
                    count += 1
                except Exception as e:
                    logger.error("Failed to refresh provider %s: %s", stype, e)
        return count
