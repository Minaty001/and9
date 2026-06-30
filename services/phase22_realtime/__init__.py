"""
Phase 22 — Real-Time Info Engine.

Retrieve live info: weather, news, search, time. Validate freshness,
source metadata, cache.

Components:
    - RealtimeConfig: Configuration for real-time engine
    - InfoSource: Data model for an information source
    - InfoRequest: Data model for an info request
    - InfoResult: Data model for an info result
    - RealtimeEngine: Core engine fetching from multiple sources
    - MockWeatherProvider: Mock weather data provider
    - MockNewsProvider: Mock news data provider
    - MockSearchProvider: Mock search data provider
    - TimeProvider: Real time provider
    - RealtimeInfoService: ServiceBase wrapper
"""

from .config import RealtimeConfig
from .models import InfoSource, InfoRequest, InfoResult
from .engine import RealtimeEngine
from .providers import MockWeatherProvider, MockNewsProvider, MockSearchProvider, TimeProvider
from .service import RealtimeInfoService

__all__ = [
    "RealtimeConfig",
    "InfoSource",
    "InfoRequest",
    "InfoResult",
    "RealtimeEngine",
    "MockWeatherProvider",
    "MockNewsProvider",
    "MockSearchProvider",
    "TimeProvider",
    "RealtimeInfoService",
]
