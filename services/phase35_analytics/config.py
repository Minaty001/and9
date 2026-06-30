"""
Phase 35 — Analytics Configuration.
"""

from pydantic import Field
from services.base.config_base import BaseConfig


class AnalyticsConfig(BaseConfig):
    """Configuration for the analytics system."""

    service_name: str = Field(default="jarvis_analytics", description="Analytics service name")
    enable_usage_tracking: bool = Field(default=True, description="Enable usage tracking")
    enable_performance_tracking: bool = Field(default=True, description="Enable performance tracking")
    enable_engagement_tracking: bool = Field(default=True, description="Enable engagement tracking")
    enable_report_generation: bool = Field(default=True, description="Enable report generation")
    retention_days: int = Field(default=90, ge=1, le=365, description="Data retention in days")
    aggregation_interval_minutes: int = Field(default=15, ge=1, le=1440, description="Aggregation interval")
    max_data_points: int = Field(default=10000, ge=100, le=1000000, description="Max data points")
    enable_anomaly_detection: bool = Field(default=True, description="Enable anomaly detection")

    model_config = {"env_prefix": "JARVIS_PHASE35_"}
