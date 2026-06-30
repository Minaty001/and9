"""
Phase 42 — Health Checker.

Monitors service health with support for periodic background checks,
per-service health queries, and aggregated health reporting.
"""

from __future__ import annotations

import time
import logging
import threading
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from .models import HealthCheckResult

logger = logging.getLogger(__name__)


class HealthChecker:
    """Performs health checks on registered services.

    Usage:
        checker = HealthChecker()
        checker.register_service("api", my_health_func)
        result = checker.check_all()
        checker.start_periodic_checks(interval=30, callback=my_cb)
        ...
        checker.stop_periodic_checks()
    """

    def __init__(self):
        self._services: Dict[str, Callable[[], Dict[str, Any]]] = {}
        self._results: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._periodic_thread: Optional[threading.Thread] = None
        self._periodic_stop = threading.Event()
        self._periodic_callback: Optional[Callable[[HealthCheckResult], None]] = None

    def register_service(
        self,
        service_name: str,
        health_func: Callable[[], Dict[str, Any]],
    ) -> None:
        """Register a service for health checks.

        Args:
            service_name: Unique service name.
            health_func: Callable that returns a health dict with at least "status".
        """
        with self._lock:
            self._services[service_name] = health_func

    def unregister_service(self, service_name: str) -> None:
        """Remove a registered service."""
        with self._lock:
            self._services.pop(service_name, None)
            self._results.pop(service_name, None)

    def check_service(self, service_name: str) -> Dict[str, Any]:
        """Check health of a single registered service.

        Args:
            service_name: Name of the service to check.

        Returns:
            Health dict with at least "status" and "service_name".
        """
        with self._lock:
            if service_name not in self._services:
                return {
                    "service_name": service_name,
                    "status": "unhealthy",
                    "error": "Service not registered",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            health_func = self._services[service_name]
            try:
                result = health_func()
                result.setdefault("service_name", service_name)
                result.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
                self._results[service_name] = result
                return result
            except Exception as e:
                error_result = {
                    "service_name": service_name,
                    "status": "unhealthy",
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                self._results[service_name] = error_result
                return error_result

    def check_all(self) -> HealthCheckResult:
        """Check health of all registered services.

        Returns:
            A HealthCheckResult with aggregated status.
        """
        with self._lock:
            service_checks = []
            unhealthy_count = 0
            degraded_count = 0

            for service_name in list(self._services.keys()):
                result = self.check_service(service_name)
                service_checks.append(result)
                status = result.get("status", "unhealthy")
                if status == "unhealthy":
                    unhealthy_count += 1
                elif status == "degraded":
                    degraded_count += 1

            if unhealthy_count > 0:
                overall = "unhealthy"
            elif degraded_count > 0:
                overall = "degraded"
            else:
                overall = "healthy"

            return HealthCheckResult(
                status=overall,
                service_checks=service_checks,
                details={
                    "total_services": len(self._services),
                    "unhealthy_services": unhealthy_count,
                    "degraded_services": degraded_count,
                },
            )

    def is_healthy(self) -> bool:
        """Check if all registered services are healthy.

        Returns:
            True if all services report healthy status.
        """
        result = self.check_all()
        return result.status == "healthy"

    def get_unhealthy_services(self) -> List[str]:
        """Get a list of currently unhealthy registered services.

        Returns:
            List of service names with non-healthy status.
        """
        unhealthy = []
        with self._lock:
            for service_name in list(self._services.keys()):
                result = self.check_service(service_name)
                if result.get("status") != "healthy":
                    unhealthy.append(service_name)
        return unhealthy

    def start_periodic_checks(
        self,
        interval: int = 30,
        callback: Optional[Callable[[HealthCheckResult], None]] = None,
    ) -> None:
        """Start periodic health checks in a background thread.

        Args:
            interval: Interval between checks in seconds.
            callback: Optional callback invoked with each HealthCheckResult.
        """
        if self._periodic_thread and self._periodic_thread.is_alive():
            logger.warning("Periodic checks already running")
            return

        self._periodic_stop.clear()
        self._periodic_callback = callback
        self._periodic_thread = threading.Thread(
            target=self._periodic_loop,
            args=(interval,),
            daemon=True,
            name="health-checker",
        )
        self._periodic_thread.start()
        logger.info("Periodic health checks started (interval=%ds)", interval)

    def stop_periodic_checks(self) -> None:
        """Stop periodic health checks."""
        self._periodic_stop.set()
        if self._periodic_thread:
            self._periodic_thread.join(timeout=5)
            self._periodic_thread = None
        logger.info("Periodic health checks stopped")

    def _periodic_loop(self, interval: int) -> None:
        """Background loop running periodic health checks."""
        while not self._periodic_stop.is_set():
            result = self.check_all()
            if self._periodic_callback:
                try:
                    self._periodic_callback(result)
                except Exception as e:
                    logger.error("Health check callback error: %s", e)
            self._periodic_stop.wait(timeout=interval)
