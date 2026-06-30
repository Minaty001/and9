"""
Phase 28 — Reminder Manager.

Creates and manages reminders with snooze and dismiss functionality.
"""

from __future__ import annotations

import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from .config import SchedulerConfig
from .models import ScheduledItem
from .scheduler_engine import SchedulerEngine
from .time_parser import TimeParser

logger = logging.getLogger(__name__)


class ReminderManager:
    """Manages reminders with snooze and dismiss capabilities.

    Usage:
        manager = ReminderManager(engine, parser)
        rid = manager.create_reminder("Meeting", datetime.now() + timedelta(minutes=5))
        manager.snooze(rid, 10)
        manager.dismiss(rid)
    """

    def __init__(
        self,
        engine: SchedulerEngine,
        parser: TimeParser,
        config: Optional[SchedulerConfig] = None,
    ):
        self.engine = engine
        self.parser = parser
        self.config = config or SchedulerConfig()
        self._snoozed: Dict[str, datetime] = {}

    def create_reminder(
        self,
        title: str,
        trigger_time: datetime,
        description: str = "",
        tags: Optional[List[str]] = None,
        recurrence_rule: Optional[str] = None,
    ) -> str:
        """Create a new reminder.

        Args:
            title: Reminder title.
            trigger_time: When to trigger.
            description: Optional description.
            tags: Optional tags.
            recurrence_rule: Optional recurrence rule.

        Returns:
            Reminder item ID.
        """
        item = ScheduledItem(
            id=uuid.uuid4().hex[:12],
            type="reminder",
            title=title,
            description=description,
            trigger_time=trigger_time,
            tags=tags or [],
            recurrence_rule=recurrence_rule,
        )
        return self.engine.schedule(item)

    def snooze(self, item_id: str, minutes: int = 5) -> bool:
        """Snooze a reminder.

        Args:
            item_id: Reminder item ID.
            minutes: Minutes to snooze.

        Returns:
            True if snoozed, False otherwise.
        """
        item = self.engine.get_scheduled(item_id)
        if not item or not item.is_active:
            return False

        new_time = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        item.trigger_time = new_time
        item.next_trigger_time = new_time
        self._snoozed[item_id] = new_time
        return True

    def dismiss(self, item_id: str) -> bool:
        """Dismiss (cancel) a reminder.

        Args:
            item_id: Reminder item ID.

        Returns:
            True if dismissed, False otherwise.
        """
        result = self.engine.cancel(item_id)
        if result and item_id in self._snoozed:
            del self._snoozed[item_id]
        return result

    def get_active_reminders(self) -> List[ScheduledItem]:
        """Get all active (non-dismissed) reminders.

        Returns:
            List of active ScheduledItem with type 'reminder'.
        """
        return self.engine.get_upcoming(filter_types=["reminder"])

    def get_snoozed_count(self) -> int:
        """Return number of snoozed reminders."""
        return len(self._snoozed)

    def get_snoozed(self) -> List[tuple[str, datetime]]:
        """Get list of (item_id, snoozed_until) pairs."""
        return list(self._snoozed.items())
