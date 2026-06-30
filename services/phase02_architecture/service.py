"""
Phase 2 — Architecture Service.

Coordinates the module registry and event bus to provide
a unified system architecture layer.
"""

import time
import logging
from typing import Any, Dict, List, Optional

from services.base.service_base import ServiceBase
from services.base.metrics_base import MetricsTracker
from services.phase01_core.models import ServiceStatus
from .config import ArchitectureConfig
from .event_bus import EventBus, Event
from .module_registry import ModuleRegistry
from .models import ModuleRegistration, ModuleStatus, SystemStatus
from .errors import ArchitectureError

logger = logging.getLogger(__name__)


class ArchitectureService(ServiceBase):
    """System architecture service.

    Manages module registration, event-driven communication,
    and system-wide lifecycle coordination.
    """

    def __init__(self, config: Optional[ArchitectureConfig] = None):
        super().__init__(name="jarvis_architecture", version="1.0.0")
        self.config = config or ArchitectureConfig()
        self.bus = EventBus(max_queue_size=self.config.event_queue_max_size)
        self.registry = ModuleRegistry(max_modules=self.config.max_modules)
        self._start_time = 0.0

    # ── Lifecycle ───────────────────────────────────────────────

    async def initialize(self) -> bool:
        """Initialize the architecture layer."""
        self._start_time = time.time()
        try:
            self._metrics.reset()
            self._metrics.gauge("modules_registered", 0)
            self._metrics.gauge("events_processed", 0)

            if self.config.enable_event_logging:
                @self.bus.on("*")
                async def log_all_events(event: Event):
                    logger.debug("Event: %s from %s (pri=%s)",
                                 event.type, event.source, event.priority.name)

            self._initialized = True
            elapsed = (time.time() - self._start_time) * 1000
            logger.info("ArchitectureService initialized in %.0fms", elapsed)
            return True

        except Exception as e:
            logger.error("ArchitectureService init failed: %s", e)
            return False

    async def shutdown(self) -> None:
        """Shut down the architecture layer."""
        logger.info("ArchitectureService shutting down...")
        self._initialized = False
        self.bus.reset()
        self.registry.clear()

    # ── Module Management ───────────────────────────────────────

    async def register_module(
        self,
        name: str,
        service: ServiceBase,
        dependencies: Optional[List[str]] = None,
        description: str = "",
    ) -> ModuleRegistration:
        """Register a new module in the system.

        Args:
            name: Unique module name.
            service: ServiceBase instance.
            dependencies: Module dependency names.
            description: Module description.

        Returns:
            ModuleRegistration instance.
        """
        reg = self.registry.register(name, service, dependencies, description)
        self._metrics.gauge("modules_registered", self.registry.count)
        return reg

    async def get_module(self, name: str) -> ServiceBase:
        """Get a registered module by name."""
        return self.registry.get(name)

    async def list_modules(self) -> List[Dict[str, Any]]:
        """List all registered modules with their status."""
        return self.registry.list_modules()

    # ── Event Bus ───────────────────────────────────────────────

    async def emit_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
        source: str = "architecture",
        priority: int = 5,
    ) -> int:
        """Emit an event to all subscribers.

        Args:
            event_type: Event type identifier.
            payload: Event data.
            source: Source module name.
            priority: Priority (0-10).

        Returns:
            Number of handlers that processed the event.
        """
        event = Event(
            type=event_type,
            payload=payload,
            source=source,
            priority=EventBus._priority_from_int(priority),
        )
        count = await self.bus.emit(event)
        self._metrics.counter("events_emitted")
        self._metrics.gauge("events_processed", self.bus.get_stats()["total_events"])
        return count

    async def subscribe(self, event_type: str, handler) -> None:
        """Subscribe a handler to an event type."""
        self.bus.subscribe(event_type, handler)

    # ── Health / Stats ──────────────────────────────────────────

    async def health(self) -> Dict[str, Any]:
        """Return architecture service health."""
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        status = "healthy" if self._initialized else "unhealthy"

        # Check modules health
        degraded_modules = []
        for mod in self.registry.list_modules():
            if mod["status"] in ("error", "degraded"):
                degraded_modules.append(mod["name"])

        if degraded_modules:
            status = "degraded"

        return {
            "status": status,
            "service_name": self.name,
            "version": self.version,
            "initialized": self._initialized,
            "uptime_seconds": round(uptime, 1),
            "modules_count": self.registry.count,
            "degraded_modules": degraded_modules,
        }

    async def stats(self) -> Dict[str, Any]:
        """Return architecture service statistics."""
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        bus_stats = self.bus.get_stats()
        return {
            "service": self.name,
            "version": self.version,
            "uptime_seconds": round(uptime, 1),
            "modules": {
                "count": self.registry.count,
                "list": self.registry.list_modules(),
            },
            "event_bus": bus_stats,
            "metrics": self._metrics.snapshot(),
        }


# Helper for EventBus to accept int priority
def _int_to_priority(value: int):
    from .event_bus import EventPriority
    if value >= 9:
        return EventPriority.CRITICAL
    elif value >= 7:
        return EventPriority.HIGH
    elif value >= 4:
        return EventPriority.NORMAL
    elif value >= 1:
        return EventPriority.LOW
    return EventPriority.BACKGROUND

EventBus._priority_from_int = staticmethod(_int_to_priority)
