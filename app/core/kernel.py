"""
app/core/kernel.py — AND9 AI Kernel

The kernel is the single entry point for booting AND9.
All requests route through the kernel to the event bus.

Singleton — only one kernel per process.

Boot order:
  1. ResourceManager (must start first — monitors RAM)
  2. EventBus       (needed by everything else)
  3. ServiceManager (registers and starts all services)
  4. TaskQueue      (starts worker thread — needed by BrainManager)
  5. BrainManager   (connects sub/conscious brains, depends on TaskQueue)
  6. SecurityManager
  7. Observability

Shutdown order: reverse of boot.
"""

import logging
import threading
from typing import Optional
from datetime import datetime, timezone
from app.core.service_manager import BaseService

logger = logging.getLogger(__name__)


class AND9Kernel:
    """AND9 AI Operating System Kernel — Singleton."""

    _instance: Optional["AND9Kernel"] = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def boot(self) -> None:
        """
        Boot AND9. Called once from app/main.py create_app().
        """
        if self._initialized:
            logger.warning("Kernel already booted — skipping.")
            return

        self._start_time = datetime.now(timezone.utc)
        logger.info("AND9 Kernel booting...")

        # 1. Resource Manager (first — so we know RAM before loading anything)
        from app.core.resource_manager import ResourceManager
        self.resource_manager = ResourceManager()
        self.resource_manager.start()

        # 2. Event Bus
        from app.core.event_bus import get_event_bus
        self.event_bus = get_event_bus()

        # 3. Service Manager
        from app.core.service_manager import ServiceManager
        self.service_manager = ServiceManager(self.event_bus)
        self._register_services()
        self.service_manager.start_all()

        # 4. Task Queue
        from app.core.task_queue import TaskQueue
        self.task_queue = TaskQueue(self.event_bus)
        self.task_queue.start()

        # 5. Brain Manager
        from app.brain.manager import BrainManager
        self.brain_manager = BrainManager(self.event_bus, self.task_queue)

        # 6. Security Manager
        from app.core.security_manager import SecurityManager
        self.security_manager = SecurityManager()

        # 7. Observability
        from app.core.observability import Observability
        self.observability = Observability(self)

        self._initialized = True
        self.event_bus.publish("system.startup.complete", {
            "boot_time_ms": int((datetime.now(timezone.utc) - self._start_time)
                                .total_seconds() * 1000)
        }, source="kernel")
        logger.info("AND9 Kernel boot complete.")

    def _register_services(self) -> None:
        """Register all AND9 services with the ServiceManager."""
        from app.core.memory import get_memory
        from app.core.understanding import UnderstandingEngine

        class _MemoryService(BaseService):
            name = "MemoryService"
            lazy = False
            ram_estimate_mb = 20
            def initialize(self):
                self._mem = get_memory()
            def health_check(self) -> bool:
                return self._mem is not None
            def shutdown(self):
                pass

        class _ChatService(BaseService):
            name = "ChatService"
            lazy = False
            ram_estimate_mb = 10
            def initialize(self):
                pass
            def health_check(self) -> bool:
                return True

        class _IntentService(BaseService):
            name = "IntentService"
            lazy = False
            ram_estimate_mb = 5
            def initialize(self):
                self._engine = UnderstandingEngine()
            def health_check(self) -> bool:
                return self._engine is not None

        self.service_manager.register(_MemoryService())
        self.service_manager.register(_ChatService())
        self.service_manager.register(_IntentService())

    def handle_request(self, text: str, source: str = "text") -> dict:
        """
        Main entry point for all user requests.
        Routes through Event Bus -> Brain Manager -> Task Queue -> Response.
        """
        if not self._initialized:
            return {"response": "AND9 is starting up. Please wait.", "status": "booting"}

        # Check for emergency mode (RAM too high)
        if self.resource_manager.is_emergency():
            return {
                "response": "AND9 is under heavy load. Please try again in a moment.",
                "status": "degraded",
            }

        import uuid
        request_id = uuid.uuid4().hex[:12]
        self.event_bus.publish(f"input.{source}", {
            "text": text,
            "request_id": request_id,
        }, source="kernel")

        # Brain Manager handles the event and returns a result
        return self.brain_manager.process(text, request_id=request_id)

    def health(self) -> dict:
        """Return kernel + all service health."""
        if not self._initialized:
            return {"status": "booting"}
        return {
            "status": "running",
            "uptime_seconds": int((datetime.now(timezone.utc) - self._start_time).total_seconds()),
            "services": self.service_manager.status(),
            "resources": self.resource_manager.snapshot(),
            "queue_depth": self.task_queue.depth(),
        }

    def shutdown(self) -> None:
        """Graceful shutdown. Called on app teardown."""
        logger.info("AND9 Kernel shutting down...")
        self.event_bus.publish("system.shutdown.started", {}, source="kernel")
        self.task_queue.drain()
        self.service_manager.stop_all()
        self.resource_manager.stop()
        self._initialized = False
        logger.info("AND9 Kernel stopped.")


# Module-level singleton accessor
_kernel: AND9Kernel | None = None

def get_kernel() -> AND9Kernel:
    global _kernel
    if _kernel is None:
        _kernel = AND9Kernel()
    return _kernel