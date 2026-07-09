"""
app/core/resource_manager.py — RAM and CPU watchdog for Render

Polls system resources every 30 seconds.
Takes automated action before Render kills the process.

Thresholds (MB):
  200 -> evict LRU cache
  230 -> shutdown idle services
  250 -> publish system.memory.warning
  270 -> force garbage collect + publish system.memory.critical
  290 -> emergency: reject new requests until RAM drops
"""

import gc
import logging
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False


class ResourceManager:
    EVICT_CACHE_MB     = 200
    IDLE_SHUTDOWN_MB   = 230
    WARNING_MB         = 250
    CRITICAL_MB        = 270
    EMERGENCY_MB       = 290
    POLL_INTERVAL_SEC  = 30

    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._event_bus = None   # Set lazily after kernel boots event bus
        self._emergency = False  # If True, reject new requests

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(
            target=self._poll_loop, daemon=True, name="ResourceManager"
        )
        self._thread.start()
        logger.info("ResourceManager: started.")

    def stop(self) -> None:
        self._running = False

    def get_ram_mb(self) -> float:
        """Return current process RAM in MB."""
        if _HAS_PSUTIL:
            import os
            proc = psutil.Process(os.getpid())
            return proc.memory_info().rss / 1024 / 1024
        return 0.0

    def get_cpu_percent(self) -> float:
        if _HAS_PSUTIL:
            return psutil.cpu_percent(interval=0.1)
        return 0.0

    def snapshot(self) -> dict:
        return {
            "ram_mb": round(self.get_ram_mb(), 1),
            "cpu_percent": round(self.get_cpu_percent(), 1),
            "emergency_mode": self._emergency,
        }

    def is_emergency(self) -> bool:
        return self._emergency

    def _poll_loop(self) -> None:
        while self._running:
            try:
                self._enforce_limits()
            except Exception as e:
                logger.error(f"ResourceManager poll error: {e}")
            time.sleep(self.POLL_INTERVAL_SEC)

    def _enforce_limits(self) -> None:
        ram = self.get_ram_mb()
        if ram == 0:
            return

        if ram >= self.EMERGENCY_MB:
            self._emergency = True
            logger.critical(f"ResourceManager: EMERGENCY — RAM {ram:.0f} MB, rejecting requests")
            gc.collect()
            self._publish("system.memory.critical", {"ram_mb": ram, "emergency": True})

        elif ram >= self.CRITICAL_MB:
            self._emergency = False
            logger.error(f"ResourceManager: CRITICAL — RAM {ram:.0f} MB, force GC")
            gc.collect()
            self._publish("system.memory.critical", {"ram_mb": ram})

        elif ram >= self.WARNING_MB:
            self._emergency = False
            logger.warning(f"ResourceManager: WARNING — RAM {ram:.0f} MB")
            self._publish("system.memory.warning", {"ram_mb": ram})

        elif ram >= self.IDLE_SHUTDOWN_MB:
            logger.info(f"ResourceManager: idle services check — RAM {ram:.0f} MB")
            self._publish("system.idle.check", {"ram_mb": ram})

        elif ram >= self.EVICT_CACHE_MB:
            logger.info(f"ResourceManager: evicting cache — RAM {ram:.0f} MB")
            self._publish("system.cache.evict", {"ram_mb": ram})

        else:
            if self._emergency:
                self._emergency = False
                logger.info(f"ResourceManager: RAM recovered to {ram:.0f} MB")

    def _publish(self, event: str, payload: dict) -> None:
        if self._event_bus is None:
            try:
                from app.core.event_bus import get_event_bus
                self._event_bus = get_event_bus()
            except Exception:
                return
        try:
            self._event_bus.publish(event, payload, source="resource_manager")
        except Exception as e:
            logger.warning(f"ResourceManager: could not publish event: {e}")