"""
Phase 28 — Scheduler Engine.

Core scheduling logic with conflict detection, item lifecycle,
and recurrence management.
"""

from __future__ import annotations

import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from .config import SchedulerConfig
from .models import ScheduledItem, ConflictInfo

logger = logging.getLogger(__name__)


class SchedulerEngine:
    """Core scheduling engine.

    Usage:
        engine = SchedulerEngine()
        item_id = engine.schedule(ScheduledItem(...))
        upcoming = engine.get_upcoming(limit=5)
    """

    def __init__(self, config: Optional[SchedulerConfig] = None):
        self.config = config or SchedulerConfig()
        self._items: Dict[str, ScheduledItem] = {}

    def schedule(self, item: ScheduledItem) -> str:
        """Schedule an item.

        Args:
            item: ScheduledItem to add.

        Returns:
            The item ID.
        """
        if len(self._items) >= self.config.max_scheduled_items:
            # Remove oldest inactive item
            inactive = [i for i in self._items.values() if not i.is_active]
            if inactive:
                oldest = min(inactive, key=lambda i: i.created_at)
                del self._items[oldest.id]
            else:
                oldest = min(self._items.values(), key=lambda i: i.created_at)
                del self._items[oldest.id]

        # Set initial next_trigger_time
        item.next_trigger_time = item.trigger_time
        self._items[item.id] = item
        return item.id

    def cancel(self, item_id: str) -> bool:
        """Cancel (deactivate) a scheduled item.

        Args:
            item_id: Item identifier.

        Returns:
            True if cancelled, False otherwise.
        """
        item = self._items.get(item_id)
        if not item:
            return False
        item.is_active = False
        return True

    def get_scheduled(self, item_id: str) -> Optional[ScheduledItem]:
        """Get a scheduled item by ID."""
        return self._items.get(item_id)

    def get_upcoming(self, limit: int = 10, filter_types: Optional[List[str]] = None) -> List[ScheduledItem]:
        """Get upcoming active items sorted by trigger time.

        Args:
            limit: Max items to return.
            filter_types: Optional type filter.

        Returns:
            List of ScheduledItem.
        """
        now = datetime.now(timezone.utc)
        upcoming = []
        for item in self._items.values():
            if not item.is_active:
                continue
            if filter_types and item.type not in filter_types:
                continue
            if item.trigger_time >= now or (item.next_trigger_time and item.next_trigger_time >= now):
                upcoming.append(item)

        upcoming.sort(key=lambda i: i.next_trigger_time or i.trigger_time)
        return upcoming[:limit]

    def get_overdue(self) -> List[ScheduledItem]:
        """Get items that are past their trigger time and still active.

        Returns:
            List of overdue ScheduledItem.
        """
        now = datetime.now(timezone.utc)
        overdue = []
        for item in self._items.values():
            if not item.is_active:
                continue
            trigger = item.next_trigger_time or item.trigger_time
            if trigger <= now:
                overdue.append(item)

        overdue.sort(key=lambda i: i.next_trigger_time or i.trigger_time)
        return overdue

    def detect_conflicts(self, item: ScheduledItem) -> ConflictInfo:
        """Detect scheduling conflicts for an item.

        Args:
            item: Item to check for conflicts.

        Returns:
            ConflictInfo with details.
        """
        if not self.config.enable_conflict_detection:
            return ConflictInfo(has_conflict=False)

        conflicts = []
        for existing in self._items.values():
            if existing.id == item.id:
                continue
            if not existing.is_active:
                continue

            # Time overlap conflict
            if item.trigger_time == existing.trigger_time:
                conflicts.append(existing.id)
            elif item.end_time and existing.trigger_time < item.end_time:
                if existing.end_time:
                    if existing.trigger_time < item.end_time and existing.end_time > item.trigger_time:
                        conflicts.append(existing.id)
                else:
                    conflicts.append(existing.id)

        if conflicts:
            return ConflictInfo(
                has_conflict=True,
                conflicting_items=conflicts,
                conflict_type="time",
                suggestion=f"Consider rescheduling to avoid conflict with {len(conflicts)} existing item(s).",
            )

        return ConflictInfo(has_conflict=False)

    def get_by_tag(self, tag: str) -> List[ScheduledItem]:
        """Get items by tag."""
        return [i for i in self._items.values() if tag in i.tags]

    def list_all(self) -> List[ScheduledItem]:
        """List all items."""
        return list(self._items.values())

    def mark_triggered(self, item_id: str) -> bool:
        """Mark an item as triggered and compute next occurrence.

        Args:
            item_id: Item identifier.

        Returns:
            True if updated, False otherwise.
        """
        item = self._items.get(item_id)
        if not item:
            return False

        now = datetime.now(timezone.utc)
        item.last_triggered = now

        # Compute next trigger for recurring items
        if item.recurrence_rule:
            next_time = self._compute_next_recurrence(item)
            if next_time:
                item.next_trigger_time = next_time
            else:
                item.is_active = False
                item.next_trigger_time = None
        else:
            item.is_active = False
            item.next_trigger_time = None

        return True

    def get_item_count(self) -> int:
        """Return total item count."""
        return len(self._items)

    def clear(self) -> None:
        """Clear all items."""
        self._items.clear()

    def _compute_next_recurrence(self, item: ScheduledItem) -> Optional[datetime]:
        """Compute next trigger time for a recurring item.

        Args:
            item: The recurring item.

        Returns:
            Next datetime or None if recurrence cannot be computed.
        """
        base = item.last_triggered or item.trigger_time
        interval = item.recurrence_interval

        if item.recurrence_rule == "daily":
            return base + timedelta(days=interval)
        elif item.recurrence_rule == "weekly":
            return base + timedelta(weeks=interval)
        elif item.recurrence_rule == "monthly":
            # Approximate monthly
            month = base.month + interval
            year = base.year
            if month > 12:
                month -= 12
                year += 1
            try:
                return base.replace(year=year, month=month)
            except (ValueError, OverflowError):
                return base + timedelta(days=30 * interval)
        elif item.recurrence_rule == "weekdays":
            next_time = base + timedelta(days=1)
            while next_time.weekday() >= 5:  # Saturday or Sunday
                next_time += timedelta(days=1)
            return next_time
        elif item.recurrence_rule == "weekends":
            next_time = base + timedelta(days=1)
            while next_time.weekday() < 5:  # Weekday
                next_time += timedelta(days=1)
            return next_time
        return None
