"""
Performance — Request Coalescer.

Deduplicate concurrent requests for the same key.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Dict, Optional, Awaitable
from collections import defaultdict

logger = logging.getLogger(__name__)


class RequestCoalescer:
    """Coalesce concurrent requests for the same key.

    When multiple callers request the same key simultaneously,
    only the first one triggers the actual work; others wait
    on the same result.

    Usage:
        coalescer = RequestCoalescer()
        result = await coalescer.coalesce("my_key", loader_func)
    """

    def __init__(self):
        self._futures: Dict[str, asyncio.Future] = {}
        self._stats: Dict[str, int] = defaultdict(int)

    async def coalesce(self, key: str, request_func: Callable[[], Awaitable[Any]],
                       timeout: Optional[float] = None) -> Any:
        """Coalesce requests for the same key.

        Args:
            key: The cache/request key.
            request_func: Async function to call if first request.
            timeout: Optional timeout in seconds.

        Returns:
            The result from the request function.
        """
        if key in self._futures:
            self._stats["coalesced_hits"] += 1
            future = self._futures[key]
            if timeout:
                try:
                    return await asyncio.wait_for(future, timeout)
                except asyncio.TimeoutError:
                    self._stats["coalesced_timeouts"] += 1
                    raise
            return await future

        self._stats["coalesced_misses"] += 1
        future = asyncio.get_event_loop().create_future()
        self._futures[key] = future

        try:
            if timeout:
                result = await asyncio.wait_for(request_func(), timeout)
            else:
                result = await request_func()
            future.set_result(result)
            return result
        except Exception as e:
            future.set_exception(e)
            raise
        finally:
            self._futures.pop(key, None)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "pending_requests": len(self._futures),
            "total_coalesced_hits": self._stats.get("coalesced_hits", 0),
            "total_coalesced_misses": self._stats.get("coalesced_misses", 0),
            "total_coalesced_timeouts": self._stats.get("coalesced_timeouts", 0),
        }

    def clear(self) -> None:
        for future in self._futures.values():
            if not future.done():
                future.cancel()
        self._futures.clear()
        self._stats.clear()
