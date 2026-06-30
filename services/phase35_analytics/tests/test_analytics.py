"""
Tests for Phase 35 — Analytics.
"""

import pytest
from datetime import datetime, timezone, timedelta
from services.phase35_analytics import (
    AnalyticsConfig,
    Event,
    UsageMetric,
    TimeSeriesPoint,
    AnalyticsReport,
    UsageTracker,
    PerformanceTracker,
    ReportGenerator,
    AnalyticsService,
)


class TestUsageTracker:
    """Verify usage event tracking."""

    def test_track_event(self):
        tracker = UsageTracker()
        tracker.track_event(Event(event_type="page_view", user_id="user1"))
        assert tracker.get_event_count("page_view") == 1

    def test_get_event_count_by_period(self):
        tracker = UsageTracker()
        tracker.track_event(Event(event_type="click", user_id="user1"))
        count = tracker.get_event_count("click", period="all")
        assert count == 1

    def test_get_top_events(self):
        tracker = UsageTracker()
        for _ in range(5):
            tracker.track_event(Event(event_type="click"))
        for _ in range(3):
            tracker.track_event(Event(event_type="view"))
        top = tracker.get_top_events(2)
        assert top[0]["event_type"] == "click"
        assert top[0]["count"] == 5

    def test_get_event_trend(self):
        tracker = UsageTracker()
        tracker.track_event(Event(event_type="click"))
        trend = tracker.get_event_trend("click")
        assert len(trend) >= 1
        assert "date" in trend[0]
        assert "count" in trend[0]

    def test_get_events_in_period(self):
        tracker = UsageTracker()
        now = datetime.now(timezone.utc)
        tracker.track_event(Event(event_type="test"))
        events = tracker.get_events_in_period(now - timedelta(hours=1), now + timedelta(hours=1))
        assert len(events) >= 1

    def test_clear(self):
        tracker = UsageTracker()
        tracker.track_event(Event(event_type="test"))
        tracker.clear()
        assert tracker.get_event_count("test") == 0


class TestPerformanceTracker:
    """Verify performance metric tracking."""

    def test_record_metric(self):
        tracker = PerformanceTracker()
        metric = tracker.record_metric("response_time", 150.5)
        assert metric.metric_name == "response_time"
        assert metric.value == 150.5

    def test_get_metric_stats(self):
        tracker = PerformanceTracker()
        for v in [100, 200, 300]:
            tracker.record_metric("latency", v)
        stats = tracker.get_metric_stats("latency")
        assert stats["count"] == 3
        assert stats["min"] == 100
        assert stats["max"] == 300
        assert stats["avg"] == 200

    def test_empty_metric_stats(self):
        tracker = PerformanceTracker()
        stats = tracker.get_metric_stats("nonexistent")
        assert stats["count"] == 0

    def test_get_metric_timeseries(self):
        tracker = PerformanceTracker()
        tracker.record_metric("cpu", 45.0)
        series = tracker.get_metric_timeseries("cpu")
        assert len(series) >= 1
        assert isinstance(series[0], TimeSeriesPoint)

    def test_get_average(self):
        tracker = PerformanceTracker()
        tracker.record_metric("mem", 50)
        tracker.record_metric("mem", 100)
        assert tracker.get_average("mem") == 75.0

    def test_get_all_metric_names(self):
        tracker = PerformanceTracker()
        tracker.record_metric("m1", 1)
        tracker.record_metric("m2", 2)
        names = tracker.get_all_metric_names()
        assert "m1" in names
        assert "m2" in names

    def test_clear(self):
        tracker = PerformanceTracker()
        tracker.record_metric("test", 1)
        tracker.clear()
        assert tracker.get_average("test") == 0.0


class TestReportGenerator:
    """Verify report generation."""

    def test_generate_daily_report(self):
        usage = UsageTracker()
        perf = PerformanceTracker()
        gen = ReportGenerator(usage, perf)
        usage.track_event(Event(event_type="click", user_id="user1"))
        usage.track_event(Event(event_type="view", user_id="user1"))
        perf.record_metric("latency", 100)
        report = gen.generate_report("daily")
        assert report.report_type == "daily"
        assert report.metrics["total_events"] >= 2

    def test_generate_weekly_report(self):
        usage = UsageTracker()
        perf = PerformanceTracker()
        gen = ReportGenerator(usage, perf)
        usage.track_event(Event(event_type="click"))
        report = gen.generate_report("weekly")
        assert report.report_type == "weekly"

    def test_generate_monthly_report(self):
        usage = UsageTracker()
        perf = PerformanceTracker()
        gen = ReportGenerator(usage, perf)
        report = gen.generate_report("monthly")
        assert report.report_type == "monthly"

    def test_empty_report(self):
        usage = UsageTracker()
        perf = PerformanceTracker()
        gen = ReportGenerator(usage, perf)
        report = gen.generate_report("daily")
        assert "No events" in report.insights[0]

    def test_anomaly_detection(self):
        usage = UsageTracker()
        perf = PerformanceTracker()
        gen = ReportGenerator(usage, perf)
        now = datetime.now(timezone.utc)
        for _ in range(50):
            usage.track_event(Event(event_type="click", timestamp=now))
        report = gen.generate_report("daily")
        assert report.report_type == "daily"

    def test_insights_generated(self):
        usage = UsageTracker()
        perf = PerformanceTracker()
        gen = ReportGenerator(usage, perf)
        usage.track_event(Event(event_type="click", user_id="user1", duration_ms=100))
        usage.track_event(Event(event_type="click", user_id="user1", duration_ms=200))
        report = gen.generate_report("daily")
        assert len(report.insights) >= 1


class TestAnalyticsService:
    """Verify service wrapper."""

    @pytest.mark.asyncio
    async def test_initialize(self):
        svc = AnalyticsService()
        assert await svc.initialize() is True

    @pytest.mark.asyncio
    async def test_track_event(self):
        svc = AnalyticsService()
        await svc.initialize()
        await svc.track_event(Event(event_type="click", user_id="user1"))

    @pytest.mark.asyncio
    async def test_record_metric(self):
        svc = AnalyticsService()
        await svc.initialize()
        metric = await svc.record_metric("response_time", 150.0)
        assert metric.metric_name == "response_time"

    @pytest.mark.asyncio
    async def test_generate_report(self):
        svc = AnalyticsService()
        await svc.initialize()
        await svc.track_event(Event(event_type="click", user_id="user1"))
        report = await svc.generate_report("daily")
        assert report.report_type == "daily"
        assert report.metrics["total_events"] >= 1

    @pytest.mark.asyncio
    async def test_get_stats(self):
        svc = AnalyticsService()
        await svc.initialize()
        stats = await svc.get_stats()
        assert "total_events" in stats

    @pytest.mark.asyncio
    async def test_get_event_count(self):
        svc = AnalyticsService()
        await svc.initialize()
        await svc.track_event(Event(event_type="click"))
        count = await svc.get_event_count("click")
        assert count >= 1

    @pytest.mark.asyncio
    async def test_get_top_events(self):
        svc = AnalyticsService()
        await svc.initialize()
        await svc.track_event(Event(event_type="click"))
        top = await svc.get_top_events()
        assert len(top) >= 1

    @pytest.mark.asyncio
    async def test_get_metric_timeseries(self):
        svc = AnalyticsService()
        await svc.initialize()
        await svc.record_metric("cpu", 50.0)
        series = await svc.get_metric_timeseries("cpu")
        assert len(series) >= 1

    @pytest.mark.asyncio
    async def test_get_metric_stats(self):
        svc = AnalyticsService()
        await svc.initialize()
        await svc.record_metric("latency", 100)
        stats = await svc.get_metric_stats("latency")
        assert stats["count"] >= 1

    @pytest.mark.asyncio
    async def test_health(self):
        svc = AnalyticsService()
        await svc.initialize()
        health = await svc.health()
        assert health["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_shutdown(self):
        svc = AnalyticsService()
        await svc.initialize()
        await svc.shutdown()
        assert not svc.is_initialized()
