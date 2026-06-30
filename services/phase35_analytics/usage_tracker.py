"""
Phase 35 — Usage Tracker.

Tracks user events and provides aggregate counts, trends, and top events.
"""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

from .config import AnalyticsConfig
from .models import Event

logger = logging.getLogger(__name__)


class UsageTracker:
    """Tracks usage events with aggregation and trend analysis.

    Usage:
        tracker = UsageTracker(config)
        tracker.track_event(Event(event_type="page_view", ...))
        count = tracker.get_event_count("page_view", period="today")
        top = tracker.get_top_events(limit=10)
    """

    def __init__(self, config: Optional[AnalyticsConfig] = None):
        self.config = config or AnalyticsConfig()
        self._events: List[Event] = []

    def track_event(self, event: Event) -> None:
        """Track a usage event.

        Args:
            event: The Event to track.
        """
        self._events.append(event)
        logger.debug("Tracked event: %s", event.event_type)

        # Prune old events
        self._prune_old()

    def _prune_old(self) -> None:
        """Remove events older than retention period."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.config.retention_days)
        self._events = [e for e in self._events if e.timestamp >= cutoff]

        # Also enforce max data points
        if len(self._events) > self.config.max_data_points:
            self._events = self._events[-self.config.max_data_points:]

    def get_event_count(self, event_type: str, period: str = "all") -> int:
        """Get count of events of a specific type.

        Args:
            event_type: The event type to count.
            period: "today", "week", "month", or "all".

        Returns:
            Event count.
        """
        now = datetime.now(timezone.utc)
        if period == "today":
            cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "week":
            cutoff = now - timedelta(days=7)
        elif period == "month":
            cutoff = now - timedelta(days=30)
        else:
            cutoff = datetime.min.replace(tzinfo=timezone.utc)

        return sum(1 for e in self._events if e.event_type == event_type and e.timestamp >= cutoff)

    def get_top_events(self, limit: int = 10) -> List[dict]:
        """Get the most frequent event types.

        Args:
            limit: Max results.

        Returns:
            List of dicts with event_type and count.
        """
        counter: Counter = Counter()
        for e in self._events:
            counter[e.event_type] += 1
        result = [{"event_type": k, "count": v} for k, v in counter.most_common(limit)]
        return result

    def get_event_trend(self, event_type: str) -> List[dict]:
        """Get event count by day for a specific event type.

        Args:
            event_type: The event type.

        Returns:
            List of dicts with date and count.
        """
        daily: Dict[str, int] = defaultdict(int)
        for e in self._events:
            if e.event_type == event_type:
                day_key = e.timestamp.strftime("%Y-%m-%d")
                daily[day_key] += 1

        return sorted(
            [{"date": k, "count": v} for k, v in daily.items()],
            key=lambda x: x["date"],
        )

    def get_events_in_period(self, start: datetime, end: datetime) -> List[Event]:
        """Get events within a time period.

        Args:
            start: Start datetime.
            end: End datetime.

        Returns:
            List of Event objects.
        """
        return [
            e for e in self._events
            if start <= e.timestamp <= end
        ]

    def get_event_type_counts(self, start: datetime, end: datetime) -> Dict[str, int]:
        """Get counts by event type for a period.

        Args:
            start: Start datetime.
            end: End datetime.

        Returns:
            Dict of event_type -> count.
        """
        counter: Counter = Counter()
        for e in self._events:
            if start <= e.timestamp <= end:
                counter[e.event_type] += 1
        return dict(counter)

    def clear(self) -> None:
        """Clear all events (for testing)."""
        self._events.clear()
