"""
Phase 41 — Mock API Server.

Provides a lightweight mock HTTP server that simulates external API endpoints
for testing purposes. Supports endpoint registration, call tracking, reset,
and auto-generated responses for common service types.
"""

import time
import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from .models import MockEndpoint

logger = logging.getLogger(__name__)


class MockApiServer:
    """Simulates external API endpoints for testing.

    Usage:
        server = MockApiServer()
        server.register_endpoint("GET", "/weather", {"temp": 22})
        response = server.handle_request("GET", "/weather")
        stats = server.get_stats()
        server.reset()
    """

    # Auto-generated responses for well-known service patterns
    AUTO_RESPONSES: Dict[str, Dict[str, Any]] = {
        "weather": {
            "status_code": 200,
            "response_data": {
                "temperature": 22,
                "conditions": "sunny",
                "humidity": 45,
                "wind_speed": 12,
            },
        },
        "news": {
            "status_code": 200,
            "response_data": {
                "articles": [
                    {"title": "Mock News Story 1", "source": "Mock News"},
                    {"title": "Mock News Story 2", "source": "Mock News"},
                ],
                "total_results": 2,
            },
        },
        "search": {
            "status_code": 200,
            "response_data": {
                "results": [
                    {"title": "Mock Result 1", "url": "http://example.com/1"},
                    {"title": "Mock Result 2", "url": "http://example.com/2"},
                ],
                "total_results": 2,
            },
        },
    }

    def __init__(self, base_url: str = "http://mock.jarvis.local"):
        self._base_url = base_url.rstrip("/")
        self._endpoints: Dict[str, MockEndpoint] = {}
        self._auto_register_common()

    def _auto_register_common(self) -> None:
        """Auto-register endpoints for common API patterns."""
        for service, config in self.AUTO_RESPONSES.items():
            self.register_endpoint(
                method="GET",
                path=f"/api/{service}",
                response_data=config["response_data"],
                status_code=config["status_code"],
            )

    def register_endpoint(
        self,
        method: str,
        path: str,
        response_data: Any,
        status_code: int = 200,
        delay_ms: int = 0,
        headers: Optional[Dict[str, str]] = None,
    ) -> MockEndpoint:
        """Register a new mock endpoint.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.).
            path: URL path (e.g., /api/weather).
            response_data: Response payload to return.
            status_code: HTTP status code.
            delay_ms: Artificial response delay in ms.
            headers: Response headers.

        Returns:
            The registered MockEndpoint.
        """
        key = self._endpoint_key(method, path)
        endpoint = MockEndpoint(
            method=method.upper(),
            path=path,
            response_data=response_data,
            status_code=status_code,
            delay_ms=delay_ms,
            headers=headers or {},
        )
        # Preserve call count if re-registering
        if key in self._endpoints:
            endpoint.call_count = self._endpoints[key].call_count
        self._endpoints[key] = endpoint
        logger.debug("Registered mock endpoint: %s %s", method.upper(), path)
        return endpoint

    def handle_request(self, method: str, path: str) -> Dict[str, Any]:
        """Handle a simulated HTTP request.

        Args:
            method: HTTP method.
            path: URL path.

        Returns:
            Dict with "status_code", "data", and optionally "headers".
        """
        # Strip base URL if path includes it
        clean_path = path
        if clean_path.startswith(self._base_url):
            clean_path = clean_path[len(self._base_url):]
        if not clean_path.startswith("/"):
            clean_path = "/" + clean_path

        # Parse query params off the path for matching
        parsed = urlparse(clean_path)
        clean_path = parsed.path

        key = self._endpoint_key(method.upper(), clean_path)
        endpoint = self._endpoints.get(key)

        if endpoint is None:
            return {
                "status_code": 404,
                "data": {"error": f"No mock endpoint registered for {method} {clean_path}"},
            }

        # Simulate delay
        if endpoint.delay_ms > 0:
            time.sleep(endpoint.delay_ms / 1000.0)

        endpoint.call_count += 1

        return {
            "status_code": endpoint.status_code,
            "data": endpoint.response_data,
            "headers": dict(endpoint.headers),
        }

    def get_endpoint(self, method: str, path: str) -> Optional[MockEndpoint]:
        """Get a registered endpoint by method and path."""
        key = self._endpoint_key(method.upper(), path)
        return self._endpoints.get(key)

    def reset(self) -> None:
        """Clear all registered endpoints and call counts."""
        self._endpoints.clear()
        self._auto_register_common()
        logger.debug("MockApiServer reset")

    def clear_endpoints(self) -> None:
        """Clear all endpoints without re-registering auto ones."""
        self._endpoints.clear()

    def get_stats(self) -> Dict[str, int]:
        """Return call counts per endpoint key.

        Returns:
            Dict mapping "METHOD path" to call_count.
        """
        return {key: ep.call_count for key, ep in self._endpoints.items()}

    def get_all_endpoints(self) -> List[MockEndpoint]:
        """Return all registered endpoints."""
        return list(self._endpoints.values())

    @staticmethod
    def _endpoint_key(method: str, path: str) -> str:
        return f"{method.upper()} {path}"
