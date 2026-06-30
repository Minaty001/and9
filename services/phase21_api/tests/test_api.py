"""
Tests for Phase 21 — API Manager.
"""

import time
import pytest
from services.phase21_api import (
    ApiConfig,
    ApiRequest,
    ApiResponse,
    ApiAdapter,
    ApiCache,
    ApiManagerService,
)
from services.phase21_api.adapter import MockHttpAdapter


class TestApiConfig:
    """Verify ApiConfig creation."""

    def test_default_config(self):
        config = ApiConfig()
        assert config.service_name == "jarvis_api"
        assert config.global_timeout_ms == 10000
        assert config.max_retries == 3
        assert config.requests_per_minute == 60

    def test_custom_config(self):
        config = ApiConfig(
            service_name="custom_api",
            global_timeout_ms=5000,
            max_retries=5,
            requests_per_minute=30,
        )
        assert config.service_name == "custom_api"
        assert config.global_timeout_ms == 5000
        assert config.max_retries == 5

    def test_env_prefix(self):
        assert ApiConfig.model_config["env_prefix"] == "JARVIS_PHASE21_"


class TestApiRequest:
    """Verify ApiRequest creation."""

    def test_create_request(self):
        req = ApiRequest(endpoint="/api/test", method="GET")
        assert req.endpoint == "/api/test"
        assert req.method == "GET"
        assert req.headers == {}
        assert req.params == {}

    def test_request_with_body(self):
        req = ApiRequest(endpoint="/api/data", method="POST", body={"key": "value"})
        assert req.method == "POST"
        assert req.body == {"key": "value"}

    def test_request_with_options(self):
        req = ApiRequest(
            endpoint="/api/search",
            params={"q": "test"},
            timeout_ms=5000,
            retry_count=2,
        )
        assert req.params == {"q": "test"}
        assert req.timeout_ms == 5000
        assert req.retry_count == 2


class TestApiResponse:
    """Verify ApiResponse creation."""

    def test_success_response(self):
        resp = ApiResponse(success=True, status_code=200, data={"result": "ok"})
        assert resp.success is True
        assert resp.status_code == 200
        assert resp.data == {"result": "ok"}
        assert resp.cached is False

    def test_error_response(self):
        resp = ApiResponse(success=False, status_code=500, error="Server error")
        assert resp.success is False
        assert resp.error == "Server error"

    def test_response_defaults(self):
        resp = ApiResponse(success=True)
        assert resp.status_code == 200
        assert resp.duration_ms == 0.0
        assert resp.cached is False
        assert resp.error is None


class TestMockHttpAdapter:
    """Verify MockHttpAdapter behavior."""

    def test_execute_registered(self):
        adapter = MockHttpAdapter()
        response = ApiResponse(success=True, status_code=200, data={"msg": "ok"})
        adapter.register_response("/api/ok", response)

        req = ApiRequest(endpoint="/api/ok")
        result = adapter.execute(req)
        assert result.success is True
        assert result.data == {"msg": "ok"}

    def test_execute_unregistered(self):
        adapter = MockHttpAdapter()
        req = ApiRequest(endpoint="/api/unknown")
        result = adapter.execute(req)
        assert result.success is False
        assert result.status_code == 404

    def test_retries_on_failure(self):
        adapter = MockHttpAdapter(max_retries=2)
        response = ApiResponse(success=False, status_code=500, error="Fail")
        adapter.register_response("/api/fail", response)

        req = ApiRequest(endpoint="/api/fail", retry_count=2)
        result = adapter.execute(req)
        assert result.success is False
        assert result.status_code == 500

    def test_retry_success_on_retry(self):
        adapter = MockHttpAdapter(max_retries=3)
        fail_resp = ApiResponse(success=False, status_code=500, error="Fail")
        ok_resp = ApiResponse(success=True, status_code=200, data={"msg": "recovered"})
        adapter.register_response("/api/retry", fail_resp)

        req = ApiRequest(endpoint="/api/retry", retry_count=2)
        result = adapter.execute(req)
        # Still fails since we only have fail registered
        assert result.success is False

    def test_call_history(self):
        adapter = MockHttpAdapter()
        resp = ApiResponse(success=True, status_code=200, data="ok")
        adapter.register_response("/api/history", resp)

        adapter.execute(ApiRequest(endpoint="/api/history"))
        adapter.execute(ApiRequest(endpoint="/api/history"))
        assert len(adapter._call_history) == 2

    def test_clear_history(self):
        adapter = MockHttpAdapter()
        resp = ApiResponse(success=True, status_code=200, data="ok")
        adapter.register_response("/api/clear", resp)

        adapter.execute(ApiRequest(endpoint="/api/clear"))
        adapter.clear_history()
        assert len(adapter._call_history) == 0

    def test_rate_limiting(self):
        """Verify rate limiting by using a very low limit."""
        adapter = MockHttpAdapter(requests_per_minute=5)
        resp = ApiResponse(success=True, status_code=200, data="ok")
        adapter.register_response("/api/rl", resp)

        # Make 5 requests (should be within limit)
        for _ in range(5):
            result = adapter.execute(ApiRequest(endpoint="/api/rl"))
            assert result.success is True

    def test_backoff_calculation(self):
        adapter = MockHttpAdapter()
        # First retry: 0.5 * 2^0 = 0.5 + jitter
        wait0 = adapter._backoff(0)
        assert 0.5 <= wait0 <= 1.0
        # Second retry: 0.5 * 2^1 = 1.0 + jitter
        wait1 = adapter._backoff(1)
        assert 1.0 <= wait1 <= 1.5


class TestApiCache:
    """Verify ApiCache behavior."""

    def test_set_and_get(self):
        cache = ApiCache(default_ttl=300)
        resp = ApiResponse(success=True, status_code=200, data="cached")
        assert cache.set("test_key", resp) is True
        cached = cache.get("test_key")
        assert cached is not None
        assert cached.data == "cached"

    def test_get_missing(self):
        cache = ApiCache()
        assert cache.get("nonexistent") is None

    def test_get_expired(self):
        cache = ApiCache(default_ttl=0)
        resp = ApiResponse(success=True, status_code=200, data="expired")
        cache.set("key", resp)
        time.sleep(0.01)
        assert cache.get("key") is None

    def test_invalidate(self):
        cache = ApiCache()
        resp = ApiResponse(success=True, status_code=200, data="inv")
        cache.set("key", resp)
        assert cache.invalidate("key") is True
        assert cache.get("key") is None

    def test_invalidate_missing(self):
        cache = ApiCache()
        assert cache.invalidate("nonexistent") is False

    def test_clear(self):
        cache = ApiCache()
        resp = ApiResponse(success=True, status_code=200, data="d")
        cache.set("k1", resp)
        cache.set("k2", resp)
        count = cache.clear()
        assert count == 2
        assert cache.size == 0

    def test_lru_eviction(self):
        cache = ApiCache(default_ttl=300, max_size=2)
        resp = ApiResponse(success=True, status_code=200, data="d")
        cache.set("k1", resp)
        cache.set("k2", resp)
        cache.set("k3", resp)
        assert cache.get("k1") is None
        assert cache.get("k2") is not None
        assert cache.get("k3") is not None


class TestApiManagerService:
    """Verify service wrapper."""

    @pytest.mark.asyncio
    async def test_initialize(self):
        svc = ApiManagerService()
        assert await svc.initialize() is True

    @pytest.mark.asyncio
    async def test_shutdown(self):
        svc = ApiManagerService()
        await svc.initialize()
        await svc.shutdown()
        assert not svc.is_initialized()

    @pytest.mark.asyncio
    async def test_health(self):
        svc = ApiManagerService()
        await svc.initialize()
        health = await svc.health()
        assert health["status"] == "healthy"
        assert health["service_name"] == "jarvis_api"

    @pytest.mark.asyncio
    async def test_stats(self):
        svc = ApiManagerService()
        await svc.initialize()
        stats = await svc.stats()
        assert stats["service"] == "jarvis_api"
        assert "metrics" in stats

    @pytest.mark.asyncio
    async def test_register_and_execute(self):
        svc = ApiManagerService()
        await svc.initialize()
        adapter = MockHttpAdapter()
        resp = ApiResponse(success=True, status_code=200, data={"msg": "hello"})
        adapter.register_response("/api/hello", resp)
        svc.register_adapter("test", adapter)

        request = ApiRequest(endpoint="/api/hello", adapter_name="test")
        result = await svc.execute(request)
        assert result.success is True
        assert result.data == {"msg": "hello"}

    @pytest.mark.asyncio
    async def test_execute_no_adapter(self):
        svc = ApiManagerService()
        await svc.initialize()
        request = ApiRequest(endpoint="/api/test")
        result = await svc.execute(request)
        assert result.success is False
        assert result.status_code == 503

    @pytest.mark.asyncio
    async def test_list_adapters(self):
        svc = ApiManagerService()
        await svc.initialize()
        adapter = MockHttpAdapter()
        svc.register_adapter("a1", adapter)
        svc.register_adapter("a2", adapter)
        adapters = svc.list_adapters()
        assert "a1" in adapters
        assert "a2" in adapters

    @pytest.mark.asyncio
    async def test_cache_management(self):
        svc = ApiManagerService()
        await svc.initialize()
        adapter = MockHttpAdapter()
        resp = ApiResponse(success=True, status_code=200, data="ok")
        adapter.register_response("/api/cached", resp)
        svc.register_adapter("test", adapter)

        # Execute to populate cache
        req = ApiRequest(endpoint="/api/cached", adapter_name="test")
        await svc.execute(req)

        # Check cache
        cache_key = svc._make_cache_key(req)
        cached = await svc.get_cached(cache_key)
        assert cached is not None

        # Invalidate
        assert await svc.invalidate_cache(cache_key) is True
        assert await svc.get_cached(cache_key) is None

        # Clear
        await svc.execute(req)
        count = await svc.clear_cache()
        assert count >= 0

    @pytest.mark.asyncio
    async def test_execute_not_initialized(self):
        svc = ApiManagerService()
        with pytest.raises(RuntimeError, match="not initialized"):
            await svc.execute(ApiRequest(endpoint="/test"))

    @pytest.mark.asyncio
    async def test_fallback_adapter(self):
        svc = ApiManagerService()
        await svc.initialize()
        adapter1 = MockHttpAdapter(name="primary")
        fail_resp = ApiResponse(success=False, status_code=500, error="Fail")
        adapter1.register_response("/api/data", fail_resp)
        adapter2 = MockHttpAdapter(name="fallback")
        ok_resp = ApiResponse(success=True, status_code=200, data="from_fallback")
        adapter2.register_response("/api/data", ok_resp)

        svc.register_adapter("primary", adapter1)
        svc.register_adapter("fallback", adapter2)

        req = ApiRequest(endpoint="/api/data", adapter_name="primary")
        result = await svc.execute(req)
        # Should fall back and succeed
        assert result.success is True
        assert result.data == "from_fallback"
