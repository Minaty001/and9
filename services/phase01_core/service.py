"""
Phase 1 — Core Service.

The central entry point that wires all JARVIS services together.
In production, it discovers and initializes all phase services.

In this implementation, it serves as the orchestrator that:
    1. Validates configuration
    2. Sets up cross-cutting logging and metrics
    3. Provides the main `process()` entry point
    4. Coordinates health checks across all services
"""

import time
import logging
from typing import Any, Dict, List, Optional

from services.base.service_base import ServiceBase
from services.base.metrics_base import MetricsTracker
from services.phase01_core.config import CoreConfig
from services.phase01_core.models import (
    BrainResult,
    BrainType,
    IntentType,
    ProcessingResult,
    ProcessingStage,
    PipelineStageResult,
    ServiceStatus,
)
from services.phase01_core.errors import (
    ConfigError,
    InitializationError,
    InvalidQueryError,
    ProcessingError,
)
from services.phase01_core.logging_setup import setup_logging


class CoreService(ServiceBase):
    """Central JARVIS core service.

    Coordinates initialization, processing, and health of all
    registered phase services.
    """

    def __init__(self, config: Optional[CoreConfig] = None):
        super().__init__(name="jarvis_core", version="1.0.0")
        self.config = config or CoreConfig()
        self._logger = None
        self._start_time = 0.0
        self._sub_services: Dict[str, ServiceBase] = {}

    # ── Lifecycle ───────────────────────────────────────────────

    async def initialize(self) -> bool:
        """Initialize the core service and all sub-services.

        Returns:
            True if all services initialized successfully.
        """
        self._start_time = time.time()

        try:
            # 1. Validate config
            self._validate_config()

            # 2. Set up logging
            self._logger = setup_logging(
                service_name=self.config.service_name,
                level=self.config.log_level,
                log_format=self.config.log_format,
                log_file=self.config.log_file,
                max_size_mb=self.config.max_log_size_mb,
                backup_count=self.config.backup_count,
            )
            self._logger.info("CoreService initializing - JARVIS v%s", self.version)

            # 3. Initialize metrics
            if self.config.enable_metrics:
                self._metrics.reset()
                self._metrics.gauge("services_initialized", 0)

            # 4. Validate design rules
            if self.config.deterministic_execution:
                self._logger.info("Deterministic execution mode enabled")

            if self.config.local_first:
                self._logger.info("Local-first execution mode enabled")

            self._initialized = True
            self._metrics.gauge("services_initialized", 1.0)
            elapsed = (time.time() - self._start_time) * 1000
            self._logger.info("CoreService initialized in %.0fms", elapsed)
            return True

        except Exception as e:
            self._logger.error("CoreService initialization failed: %s", e)
            self._initialized = False
            return False

    async def shutdown(self) -> None:
        """Gracefully shut down all services."""
        if self._logger:
            self._logger.info("CoreService shutting down...")

        # Shut down sub-services in reverse registration order
        for name, service in reversed(list(self._sub_services.items())):
            try:
                await service.shutdown()
                if self._logger:
                    self._logger.info("  Service '%s' shut down", name)
            except Exception as e:
                if self._logger:
                    self._logger.warning("  Service '%s' shutdown error: %s", name, e)

        self._initialized = False
        if self._logger:
            self._logger.info("CoreService shut down complete")

    # ── Processing ──────────────────────────────────────────────

    async def process(self, query: str, **kwargs) -> ProcessingResult:
        """Process a user query through the full JARVIS pipeline.

        Args:
            query: Raw user input string.
            **kwargs: Additional processing parameters.

        Returns:
            ProcessingResult with full pipeline trace.

        Raises:
            InvalidQueryError: If query is empty or invalid.
            ProcessingError: If pipeline processing fails.
        """
        start = time.perf_counter()

        # Validate
        if not query or not query.strip():
            raise InvalidQueryError("Query cannot be empty")

        result = ProcessingResult(
            query=query,
            timestamp=self._timestamp(),
        )
        result.stages.append(PipelineStageResult(
            stage=ProcessingStage.RECEIVED,
            success=True,
            time_ms=(time.perf_counter() - start) * 1000,
        ))

        # Pipeline will be extended by sub-services
        # For now, return a basic result (sub-services register later)
        result.normalized_query = query.strip()
        result.response = f"Processing: '{query}'"
        result.total_time_ms = (time.perf_counter() - start) * 1000

        self._metrics.counter("queries_processed")
        return result

    # ── Health / Stats ──────────────────────────────────────────

    async def health(self) -> Dict[str, Any]:
        """Return core service health status."""
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        status = "healthy" if self._initialized else "unhealthy"

        # Collect sub-service health
        sub_health = {}
        all_healthy = True
        for name, svc in self._sub_services.items():
            try:
                h = await svc.health()
                sub_health[name] = h
                if h.get("status") != "healthy":
                    all_healthy = False
            except Exception as e:
                sub_health[name] = {"status": "unhealthy", "error": str(e)}
                all_healthy = False

        overall = "healthy" if (status == "healthy" and all_healthy) else "degraded"

        return {
            "status": overall,
            "service_name": self.name,
            "version": self.version,
            "initialized": self._initialized,
            "uptime_seconds": round(uptime, 1),
            "sub_services": sub_health,
            "config": {
                "log_level": self.config.log_level,
                "local_first": self.config.local_first,
                "deterministic": self.config.deterministic_execution,
            },
        }

    async def stats(self) -> Dict[str, Any]:
        """Return core service metrics."""
        metrics_snapshot = self._metrics.snapshot()
        uptime = time.time() - self._start_time if self._start_time > 0 else 0

        sub_stats = {}
        for name, svc in self._sub_services.items():
            try:
                sub_stats[name] = await svc.stats()
            except Exception:
                sub_stats[name] = {"error": "unavailable"}

        return {
            "service": self.name,
            "version": self.version,
            "uptime_seconds": round(uptime, 1),
            "initialized": self._initialized,
            "sub_services_count": len(self._sub_services),
            "metrics": metrics_snapshot,
            "sub_services": sub_stats,
        }

    # ── Sub-service Registration ────────────────────────────────

    def register_service(self, name: str, service: ServiceBase) -> None:
        """Register a sub-service for coordinated lifecycle management.

        Args:
            name: Unique service name.
            service: ServiceBase instance.
        """
        if name in self._sub_services:
            raise ValueError(f"Service '{name}' is already registered")
        self._sub_services[name] = service
        if self._logger:
            self._logger.info("Registered sub-service: '%s'", name)

    def get_service(self, name: str) -> Optional[ServiceBase]:
        """Retrieve a registered sub-service by name."""
        return self._sub_services.get(name)

    @property
    def sub_services(self) -> Dict[str, ServiceBase]:
        """Return all registered sub-services."""
        return dict(self._sub_services)

    # ── Internal ────────────────────────────────────────────────

    def _validate_config(self) -> None:
        """Validate core configuration."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.config.log_level.upper() not in valid_levels:
            raise ConfigError(f"Invalid log level: {self.config.log_level}")
        if self.config.log_format not in ("json", "text"):
            raise ConfigError(f"Invalid log format: {self.config.log_format}")

    @staticmethod
    def _timestamp() -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
