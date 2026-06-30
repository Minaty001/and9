"""
Phase 13 — Planner Service.

Wraps the Planner in a ServiceBase lifecycle.
"""

from __future__ import annotations

import time
import logging
from typing import Any, Dict, Optional

from services.base.service_base import ServiceBase
from .config import PlannerConfig
from .planner import Planner
from .models import ExecutionPlan

logger = logging.getLogger(__name__)


class PlannerService(ServiceBase):
    """Planner service wrapping the Planner component."""

    def __init__(self, config: Optional[PlannerConfig] = None):
        super().__init__(name="jarvis_planner", version="1.0.0")
        self.config = config or PlannerConfig()
        self.planner = Planner(self.config)
        self._start_time = 0.0

    async def initialize(self) -> bool:
        """Initialize the planner service."""
        self._start_time = time.time()
        try:
            self._metrics.reset()
            self._initialized = True
            elapsed = (time.time() - self._start_time) * 1000
            logger.info("PlannerService initialized in %.0fms", elapsed)
            return True
        except Exception as e:
            logger.error("PlannerService init failed: %s", e)
            return False

    async def shutdown(self) -> None:
        """Shut down the planner service."""
        logger.info("PlannerService shutting down...")
        self._initialized = False

    # ── Core API ──────────────────────────────────────────────────

    async def plan(self, goal: str, context: Optional[Dict[str, Any]] = None) -> ExecutionPlan:
        """Create an execution plan from a goal.

        Args:
            goal: The goal to decompose.
            context: Optional context.

        Returns:
            An ExecutionPlan with ordered subtasks.
        """
        t0 = time.perf_counter()
        plan = self.planner.create_plan(goal, context)
        elapsed = (time.perf_counter() - t0) * 1000

        self._metrics.counter("plans_created")
        self._metrics.histogram("plan_creation_time_ms", elapsed)
        self._metrics.histogram("plan_subtasks", len(plan.tasks))

        return plan

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
            "max_subtasks": self.config.max_subtasks,
            "max_depth": self.config.max_depth,
            "enable_parallel": self.config.enable_parallel,
            "enable_rollback": self.config.enable_rollback,
            "metrics": self._metrics.snapshot(),
        }
