"""
Phase 35 — Analytics
======================

Usage tracking, performance metrics, user engagement,
report generation, and anomaly detection.

Components:
    - UsageTracker: Track events and usage patterns
    - PerformanceTracker: Record and query performance metrics
    - ReportGenerator: Generate daily/weekly/monthly reports with insights
    - AnalyticsService: ServiceBase wrapper
"""

from .config import AnalyticsConfig
from .models import Event, UsageMetric, TimeSeriesPoint, AnalyticsReport
from .usage_tracker import UsageTracker
from .performance_tracker import PerformanceTracker
from .report_generator import ReportGenerator
from .dashboard_generator import DashboardGenerator
from .service import AnalyticsService

__all__ = [
    "AnalyticsConfig",
    "Event",
    "UsageMetric",
    "TimeSeriesPoint",
    "AnalyticsReport",
    "UsageTracker",
    "PerformanceTracker",
    "ReportGenerator",
    "DashboardGenerator",
    "AnalyticsService",
]
