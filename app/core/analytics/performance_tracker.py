"""
Performance Tracker.

Records and queries performance metrics with statistical analysis.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class UsageMetric:
    """A recorded usage or performance metric."""

    def __init__(self, metric_name: str, category: str = "", value: float = 0.0,
                 unit: str = "count", tags: Optional[Dict] = None,
                 timestamp: Optional[datetime] = None):
        self.metric_name = metric_name
        self.category = category
        self.value = value
        self.unit = unit
        self.tags = tags or {}
        self.timestamp = timestamp or datetime.now(timezone.utc)


class TimeSeriesPoint:
    """A single point in a time series."""

    def __init__(self, timestamp: Optional[datetime] = None, value: float = 0.0,
                 label: str = "", tags: Optional[Dict] = None):
        self.timestamp = timestamp or datetime.now(timezone.utc)
        self.value = value
        self.label = label
        self.tags = tags or {}


class PerformanceTracker:
    """Tracks performance metrics with statistical summaries and time series.

    Usage:
        tracker = PerformanceTracker()
        tracker.record_metric("response_time", 145.2, tags={"endpoint": "/api"})
        stats = tracker.get_metric_stats("response_time")
        series = tracker.get_metric_timeseries("response_time")
    """

    def __init__(self, retention_days: int = 90, max_data_points: int = 10000):
        self._retention_days = retention_days
        self._max_data_points = max_data_points
        self._metrics: List[UsageMetric] = []

    def record_metric(self, name: str, value: float, tags: Optional[Dict] = None, unit: str = "ms") -> UsageMetric:
        metric = UsageMetric(metric_name=name, category="performance", value=value, unit=unit, tags=tags or {})
        self._metrics.append(metric)
        logger.debug("Recorded metric: %s = %s %s", name, value, unit)
        self._prune_old()
        return metric

    def _prune_old(self) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=self._retention_days)
        self._metrics = [m for m in self._metrics if m.timestamp >= cutoff]
        if len(self._metrics) > self._max_data_points:
            self._metrics = self._metrics[-self._max_data_points:]

    def get_metric_stats(self, name: str) -> dict:
        values = [m.value for m in self._metrics if m.metric_name == name]
        if not values:
            return {"count": 0, "min": 0, "max": 0, "avg": 0, "median": 0, "p95": 0, "p99": 0}

        sorted_values = sorted(values)
        n = len(sorted_values)
        return {
            "count": n,
            "min": sorted_values[0],
            "max": sorted_values[-1],
            "avg": round(sum(values) / n, 2),
            "median": sorted_values[n // 2],
            "p95": sorted_values[int(n * 0.95)],
            "p99": sorted_values[int(n * 0.99)],
        }

    def get_metric_timeseries(self, name: str) -> List[TimeSeriesPoint]:
        points = [TimeSeriesPoint(timestamp=m.timestamp, value=m.value, label=m.metric_name, tags=m.tags)
                  for m in self._metrics if m.metric_name == name]
        return sorted(points, key=lambda p: p.timestamp)

    def get_average(self, name: str) -> float:
        values = [m.value for m in self._metrics if m.metric_name == name]
        if not values:
            return 0.0
        return round(sum(values) / len(values), 2)

    def get_metrics_by_category(self, category: str) -> List[UsageMetric]:
        return [m for m in self._metrics if m.category == category]

    def get_all_metric_names(self) -> List[str]:
        return list(set(m.metric_name for m in self._metrics))

    def clear(self) -> None:
        self._metrics.clear()
