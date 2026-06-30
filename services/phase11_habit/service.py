"""
Phase 11 — Habit Brain Service.

ServiceBase wrapper for the Habit Brain.
"""

from __future__ import annotations

import time
import logging
from typing import Any, Dict, List, Optional

from services.base.service_base import ServiceBase
from .config import HabitConfig
from .models import HabitObservation, HabitPattern, HabitSuggestion, HabitAuditEntry
from .habit_tracker import HabitTracker
from .habit_suggester import HabitSuggester

logger = logging.getLogger(__name__)


class HabitBrainService(ServiceBase):
    """Habit brain service for learning and suggesting routines.

    Usage:
        svc = HabitBrainService()
        await svc.initialize()
        await svc.observe("play music", intent="play_music", hour=9)
        suggestions = await svc.suggest(hour=9)
    """

    def __init__(self, config: Optional[HabitConfig] = None):
        super().__init__(name="jarvis_habit", version="1.0.0")
        self.config = config or HabitConfig()
        self.tracker: Optional[HabitTracker] = None
        self.suggester: Optional[HabitSuggester] = None
        self._start_time = 0.0

    async def initialize(self) -> bool:
        self._start_time = time.time()
        try:
            self.tracker = HabitTracker(self.config)
            self.suggester = HabitSuggester(self.tracker, self.config)
            self._metrics.reset()
            self._initialized = True
            logger.info("HabitBrainService initialized")
            return True
        except Exception as e:
            logger.error("HabitBrainService init failed: %s", e)
            return False

    async def shutdown(self) -> None:
        logger.info("HabitBrainService shutting down...")
        self._initialized = False

    async def observe(
        self,
        command: str,
        intent: str = "",
        hour: int = 0,
        minute: int = 0,
        day_of_week: int = -1,
        location: Optional[str] = None,
        entities: Optional[Dict[str, List[str]]] = None,
    ) -> HabitPattern:
        """Observe a command execution for habit learning.

        Args:
            command: The command executed.
            intent: Detected intent.
            hour: Hour of day (0-23).
            minute: Minute of hour.
            day_of_week: Day (0=Mon, -1=any).
            location: Location context.
            entities: Extracted entities.

        Returns:
            The matched or created HabitPattern.
        """
        if not self.tracker:
            raise RuntimeError("HabitBrainService not initialized")
        obs = HabitObservation(
            command=command,
            intent=intent,
            time_hour=hour,
            time_minute=minute,
            day_of_week=day_of_week,
            location=location,
            entities=entities or {},
        )
        t0 = time.perf_counter()
        pattern = self.tracker.observe(obs)
        elapsed = (time.perf_counter() - t0) * 1000
        self._metrics.counter("observations", 1)
        self._metrics.histogram("observe_time_ms", elapsed)
        return pattern

    async def suggest(
        self, hour: int, day_of_week: int = -1, location: Optional[str] = None, limit: Optional[int] = None
    ) -> List[HabitSuggestion]:
        """Get habit suggestions for the current context."""
        if not self.suggester:
            raise RuntimeError("HabitBrainService not initialized")
        t0 = time.perf_counter()
        results = self.suggester.suggest(hour, day_of_week, location, limit)
        elapsed = (time.perf_counter() - t0) * 1000
        self._metrics.counter("suggestions_generated", len(results))
        self._metrics.histogram("suggest_time_ms", elapsed)
        return results

    async def approve(self, pattern_id: str) -> bool:
        if not self.tracker:
            raise RuntimeError("HabitBrainService not initialized")
        return self.tracker.approve(pattern_id)

    async def reject(self, pattern_id: str) -> bool:
        if not self.tracker:
            raise RuntimeError("HabitBrainService not initialized")
        return self.tracker.reject(pattern_id)

    async def remove(self, pattern_id: str) -> bool:
        if not self.tracker:
            raise RuntimeError("HabitBrainService not initialized")
        return self.tracker.remove(pattern_id)

    async def get_patterns(self, min_confidence: float = 0.0) -> List[HabitPattern]:
        if not self.tracker:
            raise RuntimeError("HabitBrainService not initialized")
        return self.tracker.get_patterns(min_confidence)

    async def get_pattern(self, pattern_id: str) -> Optional[HabitPattern]:
        if not self.tracker:
            raise RuntimeError("HabitBrainService not initialized")
        return self.tracker.get_pattern(pattern_id)

    async def get_audit_log(self, limit: int = 50) -> List[HabitAuditEntry]:
        if not self.tracker:
            raise RuntimeError("HabitBrainService not initialized")
        return self.tracker.get_audit_log(limit)

    async def health(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        pattern_count = self.tracker.get_pattern_count() if self.tracker else 0
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "service_name": self.name,
            "version": self.version,
            "initialized": self._initialized,
            "uptime_seconds": round(uptime, 1),
            "tracked_patterns": pattern_count,
        }

    async def stats(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        return {
            "service": self.name,
            "version": self.version,
            "uptime_seconds": round(uptime, 1),
            "metrics": self._metrics.snapshot(),
        }
