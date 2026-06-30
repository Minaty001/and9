"""
Phase 14 — Decision Engine Service.

Wraps the BrainRouter in a ServiceBase lifecycle.
"""

from __future__ import annotations

import time
import logging
from typing import Any, Dict, Optional

from services.base.service_base import ServiceBase
from .config import DecisionConfig
from .router import BrainRouter
from .models import DecisionRequest, DecisionResult

logger = logging.getLogger(__name__)


class DecisionEngineService(ServiceBase):
    """Decision engine service wrapping the BrainRouter."""

    def __init__(self, config: Optional[DecisionConfig] = None):
        super().__init__(name="jarvis_decision", version="1.0.0")
        self.config = config or DecisionConfig()
        self.router = BrainRouter(self.config)
        self._start_time = 0.0

    async def initialize(self) -> bool:
        """Initialize the decision engine service."""
        self._start_time = time.time()
        try:
            self._metrics.reset()
            self._initialized = True
            elapsed = (time.time() - self._start_time) * 1000
            logger.info("DecisionEngineService initialized in %.0fms", elapsed)
            return True
        except Exception as e:
            logger.error("DecisionEngineService init failed: %s", e)
            return False

    async def shutdown(self) -> None:
        """Shut down the decision engine service."""
        logger.info("DecisionEngineService shutting down...")
        self._initialized = False

    # ── Core API ──────────────────────────────────────────────────

    async def decide(self, request: DecisionRequest) -> DecisionResult:
        """Route a request to the appropriate brain.

        Args:
            request: The decision request.

        Returns:
            A DecisionResult with selected brain and routing path.
        """
        t0 = time.perf_counter()
        result = self.router.route(request)
        elapsed = (time.perf_counter() - t0) * 1000

        self._metrics.counter("decisions_made")
        self._metrics.histogram("decision_time_ms", elapsed)
        self._metrics.counter(f"routed_to_{result.selected_brain}")

        return result

    # ── Health / Stats ────────────────────────────────────────────

    async def health(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "service_name": self.name,
            "version": self.version,
            "initialized": self._initialized,
            "uptime_seconds": round(uptime, 1),
        }

    async def stats(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        return {
            "service": self.name,
            "version": self.version,
            "uptime_seconds": round(uptime, 1),
            "reflex_threshold": self.config.reflex_confidence_threshold,
            "habit_threshold": self.config.habit_confidence_threshold,
            "enable_escalation": self.config.enable_escalation,
            "cost_aware_routing": self.config.cost_aware_routing,
            "metrics": self._metrics.snapshot(),
        }
