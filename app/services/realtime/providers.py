"""
app/services/realtime/providers.py — Real-Time Info Providers.

Mock providers for weather, news, search, and a real time provider.
"""

import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .models import InfoRequest, InfoResult


class MockWeatherProvider:
    """Mock weather data provider."""

    def __init__(self):
        self._mock_data = {
            "location": "Mumbai, IN",
            "temperature": 32,
            "unit": "celsius",
            "condition": "Partly Cloudy",
            "humidity": 65,
            "wind_speed": 12,
            "forecast": [
                {"day": "Today", "high": 34, "low": 26, "condition": "Partly Cloudy"},
                {"day": "Tomorrow", "high": 33, "low": 25, "condition": "Sunny"},
            ],
        }

    def get_data(self, request: InfoRequest) -> InfoResult:
        """Return mock weather data."""
        return InfoResult(
            source="weather",
            query=request.query,
            data=self._mock_data,
            freshness_score=1.0,
        )

    def refresh(self) -> None:
        """Refresh (no-op for mock)."""
        pass


class MockNewsProvider:
    """Mock news data provider."""

    def __init__(self):
        self._mock_data = {
            "articles": [
                {
                    "title": "AI Research Breakthrough Announced",
                    "source": "Tech News",
                    "published_at": "2026-06-29T10:00:00Z",
                    "summary": "New breakthroughs in AI research...",
                },
                {
                    "title": "Weather Alert: Heavy Rainfall Expected",
                    "source": "Weather Channel",
                    "published_at": "2026-06-29T08:30:00Z",
                    "summary": "Heavy rainfall expected in coastal regions...",
                },
                {
                    "title": "Stock Market Update: Tech Stocks Rally",
                    "source": "Finance Daily",
                    "published_at": "2026-06-29T09:15:00Z",
                    "summary": "Technology stocks rallied today...",
                },
            ]
        }

    def get_data(self, request: InfoRequest) -> InfoResult:
        """Return mock news data."""
        return InfoResult(
            source="news",
            query=request.query,
            data=self._mock_data,
            freshness_score=0.9,
        )

    def refresh(self) -> None:
        """Refresh (no-op for mock)."""
        pass


class MockSearchProvider:
    """Mock search data provider."""

    def __init__(self):
        self._mock_data = {
            "results": [
                {
                    "title": "Python Programming Guide",
                    "url": "https://example.com/python",
                    "snippet": "Comprehensive guide to Python programming...",
                },
                {
                    "title": "JARVIS AI Assistant Documentation",
                    "url": "https://example.com/jarvis",
                    "snippet": "Documentation for the JARVIS AI assistant...",
                },
            ]
        }

    def get_data(self, request: InfoRequest) -> InfoResult:
        """Return mock search data."""
        return InfoResult(
            source="search",
            query=request.query,
            data=self._mock_data,
            freshness_score=0.8,
        )

    def refresh(self) -> None:
        """Refresh (no-op for mock)."""
        pass


class TimeProvider:
    """Real time provider that returns current date/time info."""

    def get_data(self, request: InfoRequest) -> InfoResult:
        """Return current time data."""
        now = datetime.now(timezone.utc)
        local_time = time.localtime()
        data = {
            "utc_time": now.isoformat(),
            "unix_timestamp": int(time.time()),
            "local_time": time.strftime("%Y-%m-%d %H:%M:%S", local_time),
            "timezone": "UTC",
            "date": time.strftime("%Y-%m-%d", local_time),
            "day_of_week": time.strftime("%A", local_time),
        }
        return InfoResult(
            source="time",
            query=request.query,
            data=data,
            freshness_score=1.0,
        )

    def refresh(self) -> None:
        """Refresh (no-op for time provider)."""
        pass
