"""
Base shared components for all JARVIS services.

Provides:
    - ServiceBase: Abstract base class for service lifecycle
    - MetricsTracker: Metrics collection and reporting
    - BaseConfig: Shared Pydantic configuration fields
"""

from .service_base import ServiceBase
from .metrics_base import MetricsTracker
from .config_base import BaseConfig

__all__ = ["ServiceBase", "MetricsTracker", "BaseConfig"]
