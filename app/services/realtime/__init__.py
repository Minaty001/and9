"""
app/services/realtime/ — Real-Time Info Engine.

Retrieve live info: weather, news, search, time. Validates freshness,
source metadata, cache.

Components:
    - RealtimeEngine: Core engine fetching from multiple sources
    - MockWeatherProvider: Mock weather data provider
    - MockNewsProvider: Mock news data provider
    - MockSearchProvider: Mock search data provider
    - TimeProvider: Real time provider
    - RealtimeInfoService: Service wrapper with initialize/shutdown/health/stats
"""

from .models import InfoSource, InfoRequest, InfoResult
from .engine import RealtimeEngine
from .providers import MockWeatherProvider, MockNewsProvider, MockSearchProvider, TimeProvider
from .service import RealtimeInfoService

__all__ = [
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
