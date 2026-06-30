"""
Abstract base class for all JARVIS services.

Defines the lifecycle contract that every phase service must implement:
    - initialize()      — Set up resources, connections, models
    - health()          — Return service health status
    - stats()           — Return service statistics / metrics
    - shutdown()        — Gracefully tear down resources

Usage:
    class MyService(ServiceBase):
        async def initialize(self) -> bool: ...
        async def health(self) -> dict: ...
        async def stats(self) -> dict: ...
        async def shutdown(self) -> None: ...
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from .metrics_base import MetricsTracker


class ServiceBase(ABC):
    """Abstract base for all JARVIS services.

    Attributes:
        name: Human-readable service name.
        version: Service version string.
        _initialized: Whether the service has been initialized.
        _metrics: MetricsTracker instance.
    """

    def __init__(self, name: str = "jarvis_service", version: str = "1.0.0"):
        self.name = name
        self.version = version
        self._initialized = False
        self._metrics = MetricsTracker(service_name=name)

    # ── Lifecycle ───────────────────────────────────────────────

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the service.

        Returns:
            True if initialization succeeded, False otherwise.

        Raises:
            ServiceError: If initialization encounters a fatal error.
        """
        ...

    @abstractmethod
    async def shutdown(self) -> None:
        """Gracefully shut down the service.

        Should release all resources, close connections, and flush logs/metrics.
        Must not raise.
        """
        ...

    # ── Introspection ──────────────────────────────────────────

    @abstractmethod
    async def health(self) -> Dict[str, Any]:
        """Return current health status.

        Returns a dict with at least:
            {"status": "healthy"|"degraded"|"unhealthy", "uptime_seconds": ...}
        """
        ...

    @abstractmethod
    async def stats(self) -> Dict[str, Any]:
        """Return service statistics and metrics snapshot."""
        ...

    # ── Convenience ─────────────────────────────────────────────

    def is_initialized(self) -> bool:
        """Check if the service has been successfully initialized."""
        return self._initialized

    def __repr__(self) -> str:
        return f"{type(self).__name__}(name={self.name}, init={self._initialized})"
