"""
Phase 21 — API Adapter.

Base adapter interface with rate limiting, retries with exponential backoff,
and timeout handling.
"""

import time
import random
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from .models import ApiRequest, ApiResponse

logger = logging.getLogger(__name__)


class ApiAdapter(ABC):
    """Base adapter for executing API requests with rate limiting and retries.

    Subclasses implement _execute() for the actual request logic.
    """

    def __init__(
        self,
        name: str = "default",
        max_retries: int = 3,
        requests_per_minute: int = 60,
        global_timeout_ms: int = 10000,
    ):
        self.name = name
        self.max_retries = max_retries
        self.requests_per_minute = requests_per_minute
        self.global_timeout_ms = global_timeout_ms
        self._last_request_time = 0.0
        self._request_timestamps: list = []

    def execute(self, request: ApiRequest) -> ApiResponse:
        """Execute an API request with rate limiting and retries.

        Args:
            request: The API request to execute.

        Returns:
            ApiResponse with the result.
        """
        self._enforce_rate_limit()

        retries = request.retry_count if request.retry_count is not None else self.max_retries
        timeout = request.timeout_ms if request.timeout_ms is not None else self.global_timeout_ms

        last_error: Optional[str] = None
        last_status = 500

        for attempt in range(retries + 1):
            try:
                t0 = time.perf_counter()
                response = self._execute(request, timeout)
                elapsed = (time.perf_counter() - t0) * 1000

                response.duration_ms = elapsed

                if response.success:
                    return response

                last_error = response.error
                last_status = response.status_code

                if attempt < retries:
                    wait = self._backoff(attempt)
                    logger.debug(
                        "Adapter %s: attempt %d failed (status=%d), retrying in %.2fs",
                        self.name, attempt + 1, response.status_code, wait,
                    )
                    time.sleep(wait)

            except Exception as e:
                elapsed = (time.perf_counter() - t0) * 1000 if 't0' in dir() else 0
                last_error = str(e)
                last_status = 0
                logger.debug("Adapter %s: attempt %d exception: %s", self.name, attempt + 1, e)

                if attempt < retries:
                    wait = self._backoff(attempt)
                    time.sleep(wait)

        return ApiResponse(
            success=False,
            status_code=last_status,
            error=last_error or "Request failed after all retries",
            duration_ms=0.0,
        )

    @abstractmethod
    def _execute(self, request: ApiRequest, timeout_ms: int) -> ApiResponse:
        """Execute the actual request. Override in subclasses."""
        ...

    def _enforce_rate_limit(self) -> None:
        """Enforce rate limiting by checking request frequency."""
        if self.requests_per_minute <= 0:
            return

        now = time.time()
        # Prune timestamps older than 60 seconds
        cutoff = now - 60
        self._request_timestamps = [t for t in self._request_timestamps if t > cutoff]

        # Check if we exceeded the limit
        if len(self._request_timestamps) >= self.requests_per_minute:
            sleep_time = self._request_timestamps[0] - cutoff
            if sleep_time > 0:
                logger.debug("Rate limit reached, sleeping %.2fs", sleep_time)
                time.sleep(sleep_time)
            self._request_timestamps = [t for t in self._request_timestamps if t > (time.time() - 60)]

        self._request_timestamps.append(time.time())

    def _backoff(self, attempt: int) -> float:
        """Calculate exponential backoff time with jitter.

        Args:
            attempt: The attempt number (0-based).

        Returns:
            Wait time in seconds.
        """
        base = 0.5 * (2 ** attempt)
        jitter = random.uniform(0, 0.5)
        return min(base + jitter, 10.0)


class MockHttpAdapter(ApiAdapter):
    """Mock HTTP adapter for testing with predefined responses."""

    def __init__(self, name: str = "mock_http", **kwargs):
        super().__init__(name=name, **kwargs)
        self._responses: Dict[str, ApiResponse] = {}
        self._call_history: list = []

    def register_response(self, endpoint: str, response: ApiResponse) -> None:
        """Register a mock response for a given endpoint."""
        self._responses[endpoint] = response

    def _execute(self, request: ApiRequest, timeout_ms: int) -> ApiResponse:
        """Return a registered mock response or a default 404."""
        self._call_history.append(request)

        if request.endpoint in self._responses:
            resp = self._responses[request.endpoint]
            # Simulate processing time
            time.sleep(0.01)
            return resp

        return ApiResponse(
            success=False,
            status_code=404,
            error=f"No mock response registered for endpoint: {request.endpoint}",
        )

    def clear_history(self) -> None:
        """Clear call history."""
        self._call_history.clear()
