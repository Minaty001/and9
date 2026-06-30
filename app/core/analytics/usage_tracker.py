"""
Usage Tracker.

Tracks user events and provides aggregate counts, trends, and top events.
"""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class Event:
    """A tracked usage event."""

    def __init__(self, event_type: str, session_id: str = "", user_id: str = "",
                 category: str = "", action: str = "", label: str = "",
                 value: float = 0.0, metadata: Optional[Dict] = None,
                 timestamp: Optional[datetime] = None, duration_ms: float = 0.0):
        self.event_type = event_type
        self.session_id = session_id
        self.user_id = user_id
        self.category = category
        self.action = action
        self.label = label
        self.value = value
        self.metadata = metadata or {}
        self.timestamp = timestamp or datetime.now(timezone.utc)
        self.duration_ms = duration_ms


class UsageTracker:
    """Tracks usage events with aggregation and trend analysis.

    Usage:
        tracker = UsageTracker()
        tracker.track_event(Event(event_type="page_view", ...))
        count = tracker.get_event_count("page_view", period="today")
        top = tracker.get_top_events(limit=10)
    """

    def __init__(self, retention_days: int = 90, max_data_points: int = 10000):
        self._retention_days = retention_days
        self._max_data_points = max_data_points
        self._events: List[Event] = []

    def track_event(self, event: Event) -> None:
        self._events.append(event)
        logger.debug("Tracked event: %s", event.event_type)
        self._prune_old()

    def _prune_old(self) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=self._retention_days)
        self._events = [e for e in self._events if e.timestamp >= cutoff]
        if len(self._events) > self._max_data_points:
            self._events = self._events[-self._max_data_points:]

    def get_event_count(self, event_type: str, period: str = "all") -> int:
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
        counter: Counter = Counter()
        for e in self._events:
            counter[e.event_type] += 1
        return [{"event_type": k, "count": v} for k, v in counter.most_common(limit)]

    def get_event_trend(self, event_type: str) -> List[dict]:
        daily: Dict[str, int] = defaultdict(int)
        for e in self._events:
            if e.event_type == event_type:
                day_key = e.timestamp.strftime("%Y-%m-%d")
                daily[day_key] += 1
        return sorted([{"date": k, "count": v} for k, v in daily.items()], key=lambda x: x["date"])

    def get_events_in_period(self, start: datetime, end: datetime) -> List[Event]:
        return [e for e in self._events if start <= e.timestamp <= end]

    def get_event_type_counts(self, start: datetime, end: datetime) -> Dict[str, int]:
        counter: Counter = Counter()
        for e in self._events:
            if start <= e.timestamp <= end:
                counter[e.event_type] += 1
        return dict(counter)

    def clear(self) -> None:
        self._events.clear()
