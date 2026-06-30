"""
Report Generator.

Generates daily, weekly, and monthly analytics reports with
insights and anomaly detection.
"""

from __future__ import annotations

import uuid
import logging
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

from .usage_tracker import UsageTracker, Event
from .performance_tracker import PerformanceTracker

logger = logging.getLogger(__name__)


class AnalyticsReport:
    """A generated analytics report."""

    def __init__(self, report_id: str, report_type: str, period_start: datetime, period_end: datetime,
                 generated_at: Optional[datetime] = None, metrics: Optional[Dict] = None,
                 charts: Optional[Dict] = None, insights: Optional[List] = None,
                 top_events: Optional[List] = None, anomalies: Optional[List] = None,
                 dashboard_html: Optional[str] = None,
                 performance_summary: Optional[Dict] = None):
        self.report_id = report_id
        self.report_type = report_type
        self.period_start = period_start
        self.period_end = period_end
        self.generated_at = generated_at or datetime.now(timezone.utc)
        self.metrics = metrics or {}
        self.charts = charts or {}
        self.insights = insights or []
        self.top_events = top_events or []
        self.anomalies = anomalies or []
        self.dashboard_html = dashboard_html
        self.performance_summary = performance_summary or {}


class ReportGenerator:
    """Generates analytics reports with insights and anomaly detection.

    Usage:
        gen = ReportGenerator(usage_tracker, performance_tracker)
        report = gen.generate_report("daily")
        print(report.insights)
    """

    def __init__(self, usage_tracker: UsageTracker, performance_tracker: PerformanceTracker,
                 enable_anomaly_detection: bool = True):
        self.usage_tracker = usage_tracker
        self.performance_tracker = performance_tracker
        self._enable_anomaly_detection = enable_anomaly_detection

    def generate_report(self, report_type: str = "daily") -> AnalyticsReport:
        now = datetime.now(timezone.utc)

        if report_type == "daily":
            period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            period_end = now
        elif report_type == "weekly":
            period_start = now - timedelta(days=7)
            period_end = now
        elif report_type == "monthly":
            period_start = now - timedelta(days=30)
            period_end = now
        else:
            period_start = now - timedelta(days=1)
            period_end = now

        events = self.usage_tracker.get_events_in_period(period_start, period_end)
        if not events:
            return self._empty_report(report_type, period_start, period_end)

        metrics = self._compute_metrics(events)
        charts = self._compute_charts(events, period_start, period_end)
        insights = self._compute_insights(events, metrics)
        top_events = self._get_top_events(events)
        performance_summary = self._compute_performance_summary(events)
        anomalies = self._detect_anomalies(events) if self._enable_anomaly_detection else []

        return AnalyticsReport(
            report_id=uuid.uuid4().hex[:12],
            report_type=report_type,
            period_start=period_start,
            period_end=period_end,
            metrics=metrics,
            charts=charts,
            insights=insights,
            top_events=top_events,
            anomalies=anomalies,
            performance_summary=performance_summary,
        )

    def _empty_report(self, report_type: str, start: datetime, end: datetime) -> AnalyticsReport:
        return AnalyticsReport(
            report_id=uuid.uuid4().hex[:12],
            report_type=report_type,
            period_start=start,
            period_end=end,
            metrics={"total_events": 0, "unique_users": 0},
            insights=["No events recorded in this period."],
        )

    def _compute_metrics(self, events: List[Event]) -> dict:
        total_events = len(events)
        unique_users = len(set(e.user_id for e in events if e.user_id))
        unique_sessions = len(set(e.session_id for e in events if e.session_id))
        total_duration = sum(e.duration_ms for e in events)
        event_types = len(set(e.event_type for e in events))
        avg_duration = round(total_duration / total_events, 2) if total_events > 0 else 0
        hourly_dist = Counter(e.timestamp.hour for e in events)
        peak_hour = hourly_dist.most_common(1)[0][0] if hourly_dist else 0

        return {
            "total_events": total_events,
            "unique_users": unique_users,
            "unique_sessions": unique_sessions,
            "event_types": event_types,
            "total_duration_ms": round(total_duration, 2),
            "avg_duration_ms": avg_duration,
            "peak_hour": peak_hour,
        }

    def _compute_charts(self, events: List[Event], start: datetime, end: datetime) -> dict:
        daily_counts = defaultdict(int)
        for e in events:
            day_key = e.timestamp.strftime("%Y-%m-%d")
            daily_counts[day_key] += 1
        type_dist = Counter(e.event_type for e in events)
        hourly_dist = Counter(e.timestamp.hour for e in events)
        hourly_data = {str(h): hourly_dist.get(h, 0) for h in range(24)}
        return {
            "daily_events": dict(sorted(daily_counts.items())),
            "event_type_distribution": dict(type_dist.most_common(10)),
            "hourly_distribution": hourly_data,
        }

    def _compute_insights(self, events: List[Event], metrics: dict) -> list:
        insights = []
        total = metrics["total_events"]
        if total > 0:
            insights.append(f"Total events: {total} in this period.")
        if metrics["unique_users"] > 0:
            insights.append(f"Active users: {metrics['unique_users']} unique users.")
        if metrics["peak_hour"] is not None:
            hour = metrics["peak_hour"]
            period = "AM" if hour < 12 else "PM"
            display_hour = hour if hour <= 12 else hour - 12
            if display_hour == 0:
                display_hour = 12
            insights.append(f"Peak usage hour: {display_hour}:00 {period}.")
        if metrics["avg_duration_ms"] > 0:
            insights.append(f"Average event duration: {metrics['avg_duration_ms']} ms.")
        type_counter = Counter(e.event_type for e in events)
        if type_counter:
            most_common = type_counter.most_common(1)[0]
            insights.append(f"Most used feature: '{most_common[0]}' ({most_common[1]} times).")
        return insights

    def _get_top_events(self, events: List[Event], limit: int = 10) -> list:
        counter = Counter(e.event_type for e in events)
        return [{"event_type": k, "count": v} for k, v in counter.most_common(limit)]

    def _compute_performance_summary(self, events: List[Event]) -> dict:
        if not events:
            return {"avg_latency": 0.0, "p50_latency": 0.0, "p95_latency": 0.0, "p99_latency": 0.0,
                    "error_rate": 0.0, "success_rate": 100.0, "total_operations": 0,
                    "slowest_endpoint": "", "busiest_hour": ""}

        durations = sorted([e.duration_ms for e in events if e.duration_ms > 0])
        n = len(durations)
        error_events = [e for e in events if "error" in e.event_type.lower() or "error" in e.action.lower()]
        error_rate = round(len(error_events) / len(events) * 100, 2)
        success_rate = round(100.0 - error_rate, 2)
        avg_latency = round(sum(durations) / n, 2) if n > 0 else 0.0
        p50 = round(durations[n // 2], 2) if n > 0 else 0.0
        p95 = round(durations[int(n * 0.95)], 2) if n > 0 else 0.0
        p99 = round(durations[int(n * 0.99)], 2) if n > 0 else 0.0

        endpoint_durations = {}
        for e in events:
            endpoint = e.metadata.get("endpoint", "") or e.label
            if endpoint:
                if endpoint not in endpoint_durations:
                    endpoint_durations[endpoint] = []
                endpoint_durations[endpoint].append(e.duration_ms)
        slowest_endpoint = max(endpoint_durations, key=lambda ep: sum(endpoint_durations[ep]) / len(endpoint_durations[ep])) if endpoint_durations else ""

        hourly = Counter(e.timestamp.hour for e in events)
        busiest_hour = f"{hourly.most_common(1)[0][0]}:00" if hourly else ""

        return {
            "avg_latency": avg_latency, "p50_latency": p50, "p95_latency": p95, "p99_latency": p99,
            "error_rate": error_rate, "success_rate": success_rate, "total_operations": len(events),
            "slowest_endpoint": slowest_endpoint, "busiest_hour": busiest_hour,
        }

    def _detect_anomalies(self, events: List[Event]) -> list:
        anomalies = []
        if len(events) < 10:
            return anomalies

        hourly_counts = Counter(e.timestamp.hour for e in events)
        max_count = max(hourly_counts.values()) if hourly_counts else 0
        min_count = min(hourly_counts.values()) if len(hourly_counts) == 24 else 0

        if max_count > 0 and min_count >= 0:
            avg = sum(hourly_counts.values()) / max(len(hourly_counts), 1)
            for hour, count in hourly_counts.items():
                if count > avg * 3 and count > 10:
                    anomalies.append({
                        "type": "spike", "hour": hour, "count": count, "average": round(avg, 1),
                        "description": f"Spike detected at hour {hour}: {count} events (avg: {avg:.1f})",
                    })

        daily_counts = Counter(e.timestamp.strftime("%Y-%m-%d") for e in events)
        if len(daily_counts) > 1:
            counts = list(daily_counts.values())
            overall_avg = sum(counts) / len(counts)
            for day, count in daily_counts.items():
                if count < overall_avg * 0.3 and overall_avg > 5:
                    anomalies.append({
                        "type": "drop", "date": day, "count": count, "average": round(overall_avg, 1),
                        "description": f"Drop detected on {day}: {count} events (avg: {overall_avg:.1f})",
                    })

        return anomalies
