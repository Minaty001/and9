"""
Phase 35 — Analytics Service.

ServiceBase wrapper for the Analytics system.
"""

from __future__ import annotations

import time
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from services.base.service_base import ServiceBase
from .config import AnalyticsConfig
from .models import Event, UsageMetric, TimeSeriesPoint, AnalyticsReport
from .usage_tracker import UsageTracker
from .performance_tracker import PerformanceTracker
from .report_generator import ReportGenerator
from .dashboard_generator import DashboardGenerator

logger = logging.getLogger(__name__)


class AnalyticsService(ServiceBase):
    """Analytics service for usage tracking, performance metrics, and reports.

    Usage:
        svc = AnalyticsService()
        await svc.initialize()
        await svc.track_event(Event(event_type="page_view", ...))
        await svc.record_metric("response_time", 145.2)
        report = await svc.generate_report("daily")
    """

    def __init__(self, config: Optional[AnalyticsConfig] = None):
        super().__init__(name="jarvis_analytics", version="1.0.0")
        self.config = config or AnalyticsConfig()
        self.usage_tracker: Optional[UsageTracker] = None
        self.performance_tracker: Optional[PerformanceTracker] = None
        self.report_generator: Optional[ReportGenerator] = None
        self.dashboard_generator: Optional[DashboardGenerator] = None
        self._start_time = 0.0

    async def initialize(self) -> bool:
        self._start_time = time.time()
        try:
            self.usage_tracker = UsageTracker(self.config)
            self.performance_tracker = PerformanceTracker(self.config)
            self.report_generator = ReportGenerator(
                self.usage_tracker, self.performance_tracker, self.config
            )
            self.dashboard_generator = DashboardGenerator(self.config)
            self._metrics.reset()
            self._initialized = True
            logger.info("AnalyticsService initialized")
            return True
        except Exception as e:
            logger.error("AnalyticsService init failed: %s", e)
            return False

    async def shutdown(self) -> None:
        logger.info("AnalyticsService shutting down...")
        self._initialized = False

    async def track_event(self, event_or_type, session_id="", **kwargs):
        """Track a usage event.

        Supports two calling conventions:
          1) track_event(Event(...)) — pass an Event object directly
          2) track_event(event_type, session_id, category='ui', action='click')
             — pass individual fields as positional/keyword args

        Args:
            event_or_type: Event object or event type string.
            session_id: Session identifier (used when event_or_type is a string).
            **kwargs: Additional Event fields (category, action, user_id, etc.).
        """
        if not self.usage_tracker:
            raise RuntimeError("AnalyticsService not initialized")

        if isinstance(event_or_type, Event):
            event = event_or_type
        else:
            event = Event(
                event_type=event_or_type,
                session_id=session_id,
                category=kwargs.pop("category", ""),
                action=kwargs.pop("action", ""),
                user_id=kwargs.pop("user_id", ""),
                label=kwargs.pop("label", ""),
                value=kwargs.pop("value", 0.0),
                metadata=kwargs.pop("metadata", {}),
                duration_ms=kwargs.pop("duration_ms", 0.0),
            )

        t0 = time.perf_counter()
        self.usage_tracker.track_event(event)
        elapsed = (time.perf_counter() - t0) * 1000
        self._metrics.counter("events_tracked", 1)
        self._metrics.histogram("track_event_time_ms", elapsed)

    async def record_metric(
        self, name: str, value: float, tags: Optional[Dict] = None, unit: str = "ms"
    ) -> UsageMetric:
        """Record a performance metric.

        Args:
            name: Metric name.
            value: Metric value.
            tags: Optional tags.
            unit: Unit string.

        Returns:
            The created UsageMetric.
        """
        if not self.performance_tracker:
            raise RuntimeError("AnalyticsService not initialized")
        t0 = time.perf_counter()
        metric = self.performance_tracker.record_metric(name, value, tags, unit)
        elapsed = (time.perf_counter() - t0) * 1000
        self._metrics.counter("metrics_recorded", 1)
        self._metrics.histogram("record_metric_time_ms", elapsed)
        return metric

    async def generate_dashboard(self, report: AnalyticsReport) -> str:
        """Generate an HTML dashboard from a report.

        Args:
            report: The AnalyticsReport.

        Returns:
            HTML string.
        """
        if not self.dashboard_generator:
            raise RuntimeError("AnalyticsService not initialized")
        html = self.dashboard_generator.generate_dashboard(report)
        # Store on the report
        report.dashboard_html = html
        return html

    async def export_dashboard(self, report: AnalyticsReport, path: str) -> bool:
        """Generate and export a dashboard HTML to file.

        Args:
            report: The AnalyticsReport.
            path: Output file path.

        Returns:
            True if successful.
        """
        if not self.dashboard_generator:
            raise RuntimeError("AnalyticsService not initialized")
        html = await self.generate_dashboard(report)
        report.dashboard_html = html
        return self.dashboard_generator.export_dashboard(report, path)

    async def generate_report_with_dashboard(self, report_type: str = "daily") -> AnalyticsReport:
        """Generate a report and its dashboard HTML in one call.

        Args:
            report_type: "daily", "weekly", "monthly", or "custom".

        Returns:
            AnalyticsReport with dashboard_html populated.
        """
        report = await self.generate_report(report_type)
        await self.generate_dashboard(report)
        return report

    async def generate_report(self, report_type: str = "daily") -> AnalyticsReport:
        """Generate an analytics report.

        Args:
            report_type: "daily", "weekly", "monthly", or "custom".

        Returns:
            AnalyticsReport.
        """
        if not self.report_generator:
            raise RuntimeError("AnalyticsService not initialized")
        t0 = time.perf_counter()
        report = self.report_generator.generate_report(report_type)
        elapsed = (time.perf_counter() - t0) * 1000
        self._metrics.counter("reports_generated", 1)
        self._metrics.histogram("generate_report_time_ms", elapsed)
        return report

    async def get_stats(self) -> dict:
        """Get current analytics statistics.

        Returns:
            Dict with event counts and metric summaries.
        """
        if not self.usage_tracker or not self.performance_tracker:
            raise RuntimeError("AnalyticsService not initialized")
        return {
            "total_events": len(self.usage_tracker._events),
            "total_metrics": len(self.performance_tracker._metrics),
            "top_events": self.usage_tracker.get_top_events(5),
        }

    async def get_event_count(self, event_type: str, period: str = "all") -> int:
        """Get event count for a type.

        Args:
            event_type: Event type.
            period: "today", "week", "month", "all".

        Returns:
            Event count.
        """
        if not self.usage_tracker:
            raise RuntimeError("AnalyticsService not initialized")
        return self.usage_tracker.get_event_count(event_type, period)

    async def get_top_events(self, limit: int = 10) -> List[dict]:
        """Get top events by frequency.

        Args:
            limit: Max results.

        Returns:
            List of dicts.
        """
        if not self.usage_tracker:
            raise RuntimeError("AnalyticsService not initialized")
        return self.usage_tracker.get_top_events(limit)

    async def get_metric_timeseries(self, name: str) -> List[TimeSeriesPoint]:
        """Get time series for a metric.

        Args:
            name: Metric name.

        Returns:
            List of TimeSeriesPoint.
        """
        if not self.performance_tracker:
            raise RuntimeError("AnalyticsService not initialized")
        return self.performance_tracker.get_metric_timeseries(name)

    async def get_metric_stats(self, name: str) -> dict:
        """Get metric statistics.

        Args:
            name: Metric name.

        Returns:
            Dict with stats.
        """
        if not self.performance_tracker:
            raise RuntimeError("AnalyticsService not initialized")
        return self.performance_tracker.get_metric_stats(name)

    async def export_data(self, format: str = "json") -> str:
        """Export analytics data.

        Args:
            format: "json" only.

        Returns:
            JSON string of all data.
        """
        if not self.usage_tracker or not self.performance_tracker:
            raise RuntimeError("AnalyticsService not initialized")
        data = {
            "events": [e.model_dump(mode="json") for e in self.usage_tracker._events],
            "metrics": [m.model_dump(mode="json") for m in self.performance_tracker._metrics],
        }
        return json.dumps(data, indent=2, default=str)

    async def detect_anomaly(self, event_type: str) -> List[dict]:
        """Detect anomalies for a specific event type.

        Args:
            event_type: Event type to check.

        Returns:
            List of anomaly dicts.
        """
        if not self.report_generator or not self.usage_tracker:
            raise RuntimeError("AnalyticsService not initialized")
        now = datetime.now(timezone.utc)
        events = self.usage_tracker.get_events_in_period(
            now - timedelta(days=7), now
        )
        filtered = [e for e in events if e.event_type == event_type]
        return self.report_generator._detect_anomalies(filtered)

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
            "metrics": self._metrics.snapshot(),
        }
