"""
Phase 28 — Scheduler Service.

ServiceBase wrapper for the Scheduler.
"""

from __future__ import annotations

import time
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from services.base.service_base import ServiceBase
from .config import SchedulerConfig
from .models import ScheduledItem, TimeExpression, ConflictInfo
from .time_parser import TimeParser
from .scheduler_engine import SchedulerEngine
from .reminder_manager import ReminderManager

logger = logging.getLogger(__name__)


class SchedulerService(ServiceBase):
    """Scheduler service for reminders and recurring tasks.

    Usage:
        svc = SchedulerService()
        await svc.initialize()
        item_id = await svc.schedule(ScheduledItem(...))
        upcoming = await svc.get_upcoming()
    """

    def __init__(self, config: Optional[SchedulerConfig] = None):
        super().__init__(name="jarvis_scheduler", version="1.0.0")
        self.config = config or SchedulerConfig()
        self.parser: Optional[TimeParser] = None
        self.engine: Optional[SchedulerEngine] = None
        self.reminder_manager: Optional[ReminderManager] = None
        self._start_time = 0.0

    async def initialize(self) -> bool:
        self._start_time = time.time()
        try:
            self.parser = TimeParser()
            self.engine = SchedulerEngine(self.config)
            self.reminder_manager = ReminderManager(self.engine, self.parser, self.config)
            self._metrics.reset()
            self._initialized = True
            logger.info("SchedulerService initialized")
            return True
        except Exception as e:
            logger.error("SchedulerService init failed: %s", e)
            return False

    async def shutdown(self) -> None:
        logger.info("SchedulerService shutting down...")
        self._initialized = False

    async def schedule(
        self,
        item_or_title,
        trigger_time=None,
        *,
        tags=None,
        **kwargs,
    ) -> str:
        """Schedule an item.

        Accepts either a ScheduledItem object or individual params
        (title, trigger_time, tags=...)."""
        if not self.engine:
            raise RuntimeError("SchedulerService not initialized")
        t0 = time.perf_counter()
        if isinstance(item_or_title, ScheduledItem):
            result = self.engine.schedule(item_or_title)
        else:
            import uuid
            item = ScheduledItem(
                id=kwargs.pop("id", uuid.uuid4().hex[:12]),
                type=kwargs.pop("type", "reminder"),
                title=item_or_title,
                trigger_time=trigger_time,
                tags=tags or [],
                **kwargs,
            )
            result = self.engine.schedule(item)
        elapsed = (time.perf_counter() - t0) * 1000
        self._metrics.counter("items_scheduled", 1)
        self._metrics.histogram("schedule_time_ms", elapsed)
        return result

    async def cancel(self, item_id: str) -> bool:
        """Cancel a scheduled item."""
        if not self.engine:
            raise RuntimeError("SchedulerService not initialized")
        self._metrics.counter("items_cancelled", 1)
        return self.engine.cancel(item_id)

    async def get_scheduled(self, item_id: str) -> Optional[ScheduledItem]:
        """Get a scheduled item by ID."""
        if not self.engine:
            raise RuntimeError("SchedulerService not initialized")
        return self.engine.get_scheduled(item_id)

    async def get_upcoming(self, limit: int = 10, filter_types: Optional[List[str]] = None) -> List[ScheduledItem]:
        """Get upcoming scheduled items."""
        if not self.engine:
            raise RuntimeError("SchedulerService not initialized")
        return self.engine.get_upcoming(limit, filter_types)

    async def create_reminder(
        self,
        title: str,
        trigger_time: datetime | str,
        description: str = "",
        tags: Optional[List[str]] = None,
        recurrence_rule: Optional[str] = None,
    ) -> str:
        """Create a reminder."""
        if not self.reminder_manager:
            raise RuntimeError("SchedulerService not initialized")
        t0 = time.perf_counter()
        if isinstance(trigger_time, str):
            parsed = self.parser.parse(trigger_time)
            trigger_time = parsed.parsed_time
        result = self.reminder_manager.create_reminder(title, trigger_time, description, tags, recurrence_rule)
        elapsed = (time.perf_counter() - t0) * 1000
        self._metrics.counter("reminders_created", 1)
        self._metrics.histogram("reminder_create_time_ms", elapsed)
        return result

    async def snooze(self, item_id: str, minutes: int = 5) -> bool:
        """Snooze a reminder."""
        if not self.reminder_manager:
            raise RuntimeError("SchedulerService not initialized")
        return self.reminder_manager.snooze(item_id, minutes)

    async def dismiss(self, item_id: str) -> bool:
        """Dismiss a reminder."""
        if not self.reminder_manager:
            raise RuntimeError("SchedulerService not initialized")
        return self.reminder_manager.dismiss(item_id)

    async def detect_conflicts(self, item: ScheduledItem) -> ConflictInfo:
        """Detect scheduling conflicts."""
        if not self.engine:
            raise RuntimeError("SchedulerService not initialized")
        return self.engine.detect_conflicts(item)

    async def parse_time(self, expression: str) -> Optional[TimeExpression]:
        """Parse a time expression."""
        if not self.parser:
            raise RuntimeError("SchedulerService not initialized")
        return self.parser.parse(expression)

    async def health(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        item_count = self.engine.get_item_count() if self.engine else 0
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "service_name": self.name,
            "version": self.version,
            "initialized": self._initialized,
            "uptime_seconds": round(uptime, 1),
            "scheduled_items": item_count,
        }

    async def stats(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        item_count = self.engine.get_item_count() if self.engine else 0
        reminders = len(self.reminder_manager.get_active_reminders()) if self.reminder_manager else 0
        snoozed = self.reminder_manager.get_snoozed_count() if self.reminder_manager else 0
        return {
            "service": self.name,
            "version": self.version,
            "uptime_seconds": round(uptime, 1),
            "scheduled_items": item_count,
            "active_reminders": reminders,
            "snoozed_reminders": snoozed,
            "metrics": self._metrics.snapshot(),
        }
