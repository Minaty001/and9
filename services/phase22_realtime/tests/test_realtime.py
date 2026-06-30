"""
Tests for Phase 22 — Real-Time Info Engine.
"""

import pytest
from services.phase22_realtime import (
    RealtimeConfig,
    InfoSource,
    InfoRequest,
    InfoResult,
    RealtimeEngine,
    MockWeatherProvider,
    MockNewsProvider,
    MockSearchProvider,
    TimeProvider,
    RealtimeInfoService,
)


class TestRealtimeConfig:
    """Verify RealtimeConfig creation."""

    def test_default_config(self):
        config = RealtimeConfig()
        assert config.service_name == "jarvis_realtime"
        assert config.default_cache_ttl_seconds == 120
        assert config.freshness_timeout_ms == 3000

    def test_custom_config(self):
        config = RealtimeConfig(
            enable_live_fetch=False,
            max_concurrent_requests=10,
        )
        assert config.enable_live_fetch is False
        assert config.max_concurrent_requests == 10

    def test_env_prefix(self):
        assert RealtimeConfig.model_config["env_prefix"] == "JARVIS_PHASE22_"


class TestInfoSource:
    """Verify InfoSource creation."""

    def test_create_source(self):
        src = InfoSource(source_type="weather", name="Weather API", priority=5)
        assert src.source_type == "weather"
        assert src.priority == 5
        assert src.enabled is True

    def test_source_defaults(self):
        src = InfoSource(source_type="news", name="News API")
        assert src.cache_ttl == 120
        assert src.enabled is True


class TestInfoRequest:
    """Verify InfoRequest creation."""

    def test_create_request(self):
        req = InfoRequest(query="weather in mumbai", source_types=["weather"])
        assert req.query == "weather in mumbai"
        assert req.source_types == ["weather"]
        assert req.max_results == 5

    def test_request_defaults(self):
        req = InfoRequest(query="test")
        assert req.source_types == []
        assert req.require_fresh is False


class TestInfoResult:
    """Verify InfoResult creation."""

    def test_create_result(self):
        result = InfoResult(source="weather", query="mumbai", data={"temp": 32})
        assert result.source == "weather"
        assert result.data == {"temp": 32}
        assert result.freshness_score == 1.0

    def test_result_defaults(self):
        result = InfoResult(source="test", query="test")
        assert result.cache_hit is False
        assert result.freshness_score == 1.0


class TestMockWeatherProvider:
    """Verify MockWeatherProvider."""

    def test_get_data(self):
        provider = MockWeatherProvider()
        request = InfoRequest(query="weather in mumbai")
        result = provider.get_data(request)
        assert result.source == "weather"
        assert "temperature" in result.data
        assert result.data["location"] == "Mumbai, IN"

    def test_refresh(self):
        provider = MockWeatherProvider()
        provider.refresh()  # Should not raise


class TestMockNewsProvider:
    """Verify MockNewsProvider."""

    def test_get_data(self):
        provider = MockNewsProvider()
        request = InfoRequest(query="latest news")
        result = provider.get_data(request)
        assert result.source == "news"
        assert "articles" in result.data
        assert len(result.data["articles"]) == 3

    def test_refresh(self):
        provider = MockNewsProvider()
        provider.refresh()  # Should not raise


class TestMockSearchProvider:
    """Verify MockSearchProvider."""

    def test_get_data(self):
        provider = MockSearchProvider()
        request = InfoRequest(query="python")
        result = provider.get_data(request)
        assert result.source == "search"
        assert "results" in result.data
        assert len(result.data["results"]) == 2


class TestTimeProvider:
    """Verify TimeProvider."""

    def test_get_data(self):
        provider = TimeProvider()
        request = InfoRequest(query="current time")
        result = provider.get_data(request)
        assert result.source == "time"
        assert "utc_time" in result.data
        assert "unix_timestamp" in result.data
        assert "local_time" in result.data

    def test_time_data_types(self):
        provider = TimeProvider()
        result = provider.get_data(InfoRequest(query="time"))
        assert isinstance(result.data["unix_timestamp"], int)
        assert result.data["unix_timestamp"] > 0


class TestRealtimeEngine:
    """Verify RealtimeEngine."""

    def test_register_and_fetch(self):
        engine = RealtimeEngine()
        engine.register_provider("weather", MockWeatherProvider())
        request = InfoRequest(query="weather", source_types=["weather"])
        results = engine.fetch(request)
        assert len(results) >= 1
        assert results[0].source == "weather"

    def test_fetch_all_sources(self):
        engine = RealtimeEngine()
        engine.register_provider("weather", MockWeatherProvider())
        engine.register_provider("news", MockNewsProvider())
        engine.register_provider("search", MockSearchProvider())
        engine.register_provider("time", TimeProvider())

        request = InfoRequest(query="info")
        results = engine.fetch(request)
        assert len(results) == 4

    def test_fetch_with_source_filter(self):
        engine = RealtimeEngine()
        engine.register_provider("weather", MockWeatherProvider())
        engine.register_provider("news", MockNewsProvider())

        request = InfoRequest(query="test", source_types=["weather"])
        results = engine.fetch(request)
        assert len(results) == 1
        assert results[0].source == "weather"

    def test_fetch_empty_source_type(self):
        engine = RealtimeEngine()
        request = InfoRequest(query="test", source_types=["nonexistent"])
        results = engine.fetch(request)
        assert len(results) == 0

    def test_freshness_sorting(self):
        engine = RealtimeEngine()
        engine.register_provider("weather", MockWeatherProvider())
        engine.register_provider("time", TimeProvider())

        request = InfoRequest(query="test")
        results = engine.fetch(request)
        # Should be sorted by freshness descending
        for i in range(len(results) - 1):
            assert results[i].freshness_score >= results[i + 1].freshness_score

    def test_get_providers(self):
        engine = RealtimeEngine()
        engine.register_provider("weather", MockWeatherProvider())
        providers = engine.get_providers()
        assert "weather" in providers

    def test_refresh(self):
        engine = RealtimeEngine()
        engine.register_provider("weather", MockWeatherProvider())
        engine.register_provider("news", MockNewsProvider())
        count = engine.refresh()
        assert count == 2


class TestRealtimeInfoService:
    """Verify service wrapper."""

    @pytest.mark.asyncio
    async def test_initialize(self):
        svc = RealtimeInfoService()
        assert await svc.initialize() is True

    @pytest.mark.asyncio
    async def test_shutdown(self):
        svc = RealtimeInfoService()
        await svc.initialize()
        await svc.shutdown()
        assert not svc.is_initialized()

    @pytest.mark.asyncio
    async def test_health(self):
        svc = RealtimeInfoService()
        await svc.initialize()
        health = await svc.health()
        assert health["status"] == "healthy"
        assert health["service_name"] == "jarvis_realtime"

    @pytest.mark.asyncio
    async def test_stats(self):
        svc = RealtimeInfoService()
        await svc.initialize()
        stats = await svc.stats()
        assert stats["service"] == "jarvis_realtime"
        assert "metrics" in stats

    @pytest.mark.asyncio
    async def test_fetch(self):
        svc = RealtimeInfoService()
        await svc.initialize()
        request = InfoRequest(query="weather in mumbai", source_types=["weather", "time"])
        results = await svc.fetch(request)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_refresh(self):
        svc = RealtimeInfoService()
        await svc.initialize()
        count = await svc.refresh()
        assert count == 4  # All 4 mock providers

    @pytest.mark.asyncio
    async def test_get_providers(self):
        svc = RealtimeInfoService()
        await svc.initialize()
        providers = svc.get_providers()
        assert "weather" in providers
        assert "news" in providers
        assert "search" in providers
        assert "time" in providers

    @pytest.mark.asyncio
    async def test_fetch_not_initialized(self):
        svc = RealtimeInfoService()
        with pytest.raises(RuntimeError, match="not initialized"):
            await svc.fetch(InfoRequest(query="test"))
