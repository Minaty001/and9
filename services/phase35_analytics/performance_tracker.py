"""
Phase 35 — Performance Tracker.

Records and queries performance metrics with statistical analysis.
"""

from __future__ import annotations

import logging
import statistics
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

from .config import AnalyticsConfig
from .models import UsageMetric, TimeSeriesPoint

logger = logging.getLogger(__name__)


class PerformanceTracker:
    """Tracks performance metrics with statistical summaries and time series.

    Usage:
        tracker = PerformanceTracker(config)
        tracker.record_metric("response_time", 145.2, tags={"endpoint": "/api"})
        stats = tracker.get_metric_stats("response_time")
        series = tracker.get_metric_timeseries("response_time")
    """

    def __init__(self, config: Optional[AnalyticsConfig] = None):
        self.config = config or AnalyticsConfig()
        self._metrics: List[UsageMetric] = []

    def record_metric(
        self, name: str, value: float, tags: Optional[Dict] = None, unit: str = "ms"
    ) -> UsageMetric:
        """Record a performance metric.

        Args:
            name: Metric name.
            value: Metric value.
            tags: Optional tags dict.
            unit: Unit string.

        Returns:
            The created UsageMetric.
        """
        metric = UsageMetric(
            metric_name=name,
            category="performance",
            value=value,
            unit=unit,
            tags=tags or {},
        )
        self._metrics.append(metric)
        logger.debug("Recorded metric: %s = %s %s", name, value, unit)

        # Prune old
        self._prune_old()
        return metric

    def _prune_old(self) -> None:
        """Remove metrics older than retention period."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.config.retention_days)
        self._metrics = [m for m in self._metrics if m.timestamp >= cutoff]
        if len(self._metrics) > self.config.max_data_points:
            self._metrics = self._metrics[-self.config.max_data_points:]

    def get_metric_stats(self, name: str) -> dict:
        """Get statistical summary for a metric.

        Args:
            name: Metric name.

        Returns:
            Dict with min, max, avg, median, p95, p99, count.
        """
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
        """Get time series data for a metric.

        Args:
            name: Metric name.

        Returns:
            List of TimeSeriesPoint objects.
        """
        points = [
            TimeSeriesPoint(
                timestamp=m.timestamp,
                value=m.value,
                label=m.metric_name,
                tags=m.tags,
            )
            for m in self._metrics
            if m.metric_name == name
        ]
        return sorted(points, key=lambda p: p.timestamp)

    def get_average(self, name: str) -> float:
        """Get the average value for a metric.

        Args:
            name: Metric name.

        Returns:
            Average value or 0.0.
        """
        values = [m.value for m in self._metrics if m.metric_name == name]
        if not values:
            return 0.0
        return round(sum(values) / len(values), 2)

    def get_metrics_by_category(self, category: str) -> List[UsageMetric]:
        """Get all metrics in a category.

        Args:
            category: Category string.

        Returns:
            List of UsageMetric objects.
        """
        return [m for m in self._metrics if m.category == category]

    def get_all_metric_names(self) -> List[str]:
        """Get all unique metric names.

        Returns:
            List of metric names.
        """
        return list(set(m.metric_name for m in self._metrics))

    def clear(self) -> None:
        """Clear all metrics (for testing)."""
        self._metrics.clear()
