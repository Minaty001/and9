"""
Phase 35 — Analytics Models.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Event(BaseModel):
    """A tracked usage event."""

    event_type: str = Field(..., description="Event type identifier")
    session_id: str = Field(default="", description="Session identifier")
    user_id: str = Field(default="", description="User identifier")
    category: str = Field(default="", description="Event category")
    action: str = Field(default="", description="Event action")
    label: str = Field(default="", description="Event label")
    value: float = Field(default=0.0, description="Numeric event value")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    duration_ms: float = Field(default=0.0, description="Event duration in ms")


class UsageMetric(BaseModel):
    """A recorded usage or performance metric."""

    metric_name: str = Field(..., description="Metric name")
    category: str = Field(default="", description="Metric category")
    value: float = Field(default=0.0, description="Metric value")
    unit: str = Field(default="count", description="Metric unit")
    tags: dict = Field(default_factory=dict, description="Metric tags")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TimeSeriesPoint(BaseModel):
    """A single point in a time series."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    value: float = Field(default=0.0, description="Data point value")
    label: str = Field(default="", description="Data point label")
    tags: dict = Field(default_factory=dict, description="Data point tags")


class AnalyticsReport(BaseModel):
    """A generated analytics report."""

    report_id: str = Field(..., description="Unique report identifier")
    report_type: str = Field(..., description="daily/weekly/monthly/custom")
    period_start: datetime = Field(..., description="Report period start")
    period_end: datetime = Field(..., description="Report period end")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metrics: dict = Field(default_factory=dict, description="Aggregated metrics")
    charts: dict = Field(default_factory=dict, description="Chart data (label:values)")
    insights: list = Field(default_factory=list, description="Generated insights")
    top_events: list = Field(default_factory=list, description="Top events in period")
    anomalies: list = Field(default_factory=list, description="Detected anomalies")
    dashboard_html: Optional[str] = Field(default=None, description="Generated dashboard HTML")
    performance_summary: dict = Field(default_factory=dict, description="Performance summary statistics")
