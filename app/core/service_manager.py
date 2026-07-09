"""
app/core/service_manager.py — Service lifecycle manager

Every AND9 feature is a named BaseService.
The ServiceManager owns the lifecycle of every service.

Service states:
  REGISTERED -> STARTING -> RUNNING -> STOPPING -> STOPPED
                        ↘ FAILED -> (restart attempt)
"""

import logging
import threading
from enum import Enum
from typing import Dict, Optional
from app.core.event_bus import EventBus, Event

logger = logging.getLogger(__name__)


class ServiceState(Enum):
    REGISTERED = "registered"
    STARTING   = "starting"
    RUNNING    = "running"
    STOPPING   = "stopping"
    STOPPED    = "stopped"
    FAILED     = "failed"
    DEGRADED   = "degraded"


class BaseService:
    """
    Contract that every AND9 service must implement.

    Subclass this and implement initialize(), health_check(), shutdown().
    """
    name: str = "unnamed"
    lazy: bool = False          # If True, starts only when first requested
    ram_estimate_mb: int = 5    # Expected RAM usage (for budget tracking)

    def initialize(self) -> None:
        """Start the service. Raise on failure."""
        raise NotImplementedError

    def health_check(self) -> bool:
        """Return True if service is healthy."""
        return True

    def shutdown(self) -> None:
        """Clean up resources."""
        pass


class ServiceManager:
    def __init__(self, event_bus: EventBus):
        self._bus = event_bus
        self._services: Dict[str, BaseService] = {}
        self._states: Dict[str, ServiceState] = {}
        self._lock = threading.Lock()

    def register(self, service: BaseService) -> None:
        with self._lock:
            self._services[service.name] = service
            self._states[service.name] = ServiceState.REGISTERED
        logger.debug(f"ServiceManager: registered '{service.name}'")

    def start_all(self) -> None:
        for name, service in self._services.items():
            if not service.lazy:
                self.start(name)

    def start(self, name: str) -> bool:
        service = self._services.get(name)
        if not service:
            logger.error(f"ServiceManager: unknown service '{name}'")
            return False
        try:
            self._states[name] = ServiceState.STARTING
            service.initialize()
            self._states[name] = ServiceState.RUNNING
            self._bus.publish("service.started", {"service": name}, source="service_manager")
            logger.info(f"ServiceManager: '{name}' started.")
            return True
        except Exception as e:
            self._states[name] = ServiceState.FAILED
            self._bus.publish("service.failed", {"service": name, "error": str(e)},
                              source="service_manager")
            logger.error(f"ServiceManager: '{name}' failed to start: {e}")
            return False

    def stop(self, name: str) -> None:
        service = self._services.get(name)
        if not service:
            return
        try:
            self._states[name] = ServiceState.STOPPING
            service.shutdown()
            self._states[name] = ServiceState.STOPPED
            self._bus.publish("service.stopped", {"service": name}, source="service_manager")
        except Exception as e:
            logger.error(f"ServiceManager: error stopping '{name}': {e}")

    def stop_all(self) -> None:
        for name in reversed(list(self._services.keys())):
            if self._states.get(name) == ServiceState.RUNNING:
                self.stop(name)

    def status(self) -> dict:
        return {name: state.value for name, state in self._states.items()}

    def get(self, name: str) -> Optional[BaseService]:
        return self._services.get(name)