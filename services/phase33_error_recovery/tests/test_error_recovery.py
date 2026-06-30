"""
Tests for Phase 33 — Error Recovery.
"""

import pytest
from services.phase33_error_recovery import (
    ErrorRecoveryConfig,
    ErrorContext,
    RecoveryStrategy,
    CircuitBreaker,
    RetryHandler,
    FallbackHandler,
    ErrorAnalyzer,
    ErrorRecoveryService,
)


class TestCircuitBreaker:
    """Verify circuit breaker state machine."""

    def test_initial_state_closed(self):
        cb = CircuitBreaker()
        assert cb.state == "closed"

    def test_open_after_threshold(self):
        cb = CircuitBreaker("test", ErrorRecoveryConfig(circuit_breaker_threshold=3))
        failing_op = lambda: (_ for _ in ()).throw(Exception("fail"))
        for _ in range(3):
            with pytest.raises(Exception):
                cb.call(failing_op)
        assert cb.state == "open"

    def test_fallback_on_open(self):
        cb = CircuitBreaker("test", ErrorRecoveryConfig(circuit_breaker_threshold=1))
        failing_op = lambda: (_ for _ in ()).throw(Exception("fail"))
        with pytest.raises(Exception):
            cb.call(failing_op)
        result = cb.call(failing_op, fallback=lambda: "fallback_value")
        assert result == "fallback_value"

    def test_success_closes_circuit(self):
        cb = CircuitBreaker("test", ErrorRecoveryConfig(circuit_breaker_threshold=1))
        failing_op = lambda: (_ for _ in ()).throw(Exception("fail"))
        with pytest.raises(Exception):
            cb.call(failing_op)
        cb.state = "half-open"  # simulate half-open
        result = cb.call(lambda: "success")
        assert result == "success"
        assert cb.state == "closed"

    def test_reset(self):
        cb = CircuitBreaker("test", ErrorRecoveryConfig(circuit_breaker_threshold=1))
        failing_op = lambda: (_ for _ in ()).throw(Exception("fail"))
        with pytest.raises(Exception):
            cb.call(failing_op)
        cb.reset()
        assert cb.state == "closed"
        assert cb.failure_count == 0

    def test_is_available(self):
        cb = CircuitBreaker()
        assert cb.is_available() is True
        cb.state = "open"
        assert cb.is_available() is False

    def test_get_status(self):
        cb = CircuitBreaker("test")
        status = cb.get_status()
        assert status["name"] == "test"
        assert status["state"] == "closed"


class TestRetryHandler:
    """Verify retry logic."""

    def test_retry_success(self):
        handler = RetryHandler()
        op = lambda: "success"
        success, result, attempts = handler.execute_with_retry(op, max_retries=2)
        assert success is True
        assert result == "success"
        assert attempts == 1

    def test_retry_failure(self):
        handler = RetryHandler()
        op = lambda: (_ for _ in ()).throw(Exception("fail"))
        success, result, attempts = handler.execute_with_retry(op, max_retries=1)
        assert success is False
        assert attempts == 2

    def test_retry_stats(self):
        handler = RetryHandler(ErrorRecoveryConfig(max_retries=1))
        op = lambda: (_ for _ in ()).throw(Exception("fail"))
        handler.execute_with_retry(op, max_retries=1)
        stats = handler.get_stats()
        assert stats["total_attempts"] >= 1

    def test_reset_stats(self):
        handler = RetryHandler()
        handler.execute_with_retry(lambda: "ok")
        handler.reset_stats()
        stats = handler.get_stats()
        assert stats["total_attempts"] == 0


class TestFallbackHandler:
    """Verify fallback chain."""

    def test_primary_succeeds(self):
        handler = FallbackHandler()
        result = handler.execute_with_fallback(lambda: "primary", [lambda: "fallback"])
        assert result == "primary"

    def test_fallback_used(self):
        handler = FallbackHandler()
        result = handler.execute_with_fallback(
            lambda: (_ for _ in ()).throw(Exception("fail")),
            [lambda: "fallback1", lambda: "fallback2"],
        )
        assert result == "fallback1"

    def test_all_fail(self):
        handler = FallbackHandler(ErrorRecoveryConfig(max_fallback_depth=1))
        with pytest.raises(Exception):
            handler.execute_with_fallback(
                lambda: (_ for _ in ()).throw(Exception("fail")),
                [lambda: (_ for _ in ()).throw(Exception("also fail"))],
            )

    def test_register_fallback(self):
        handler = FallbackHandler()
        handler.register_fallback("my_op", lambda: "fallback")
        fb = handler.find_fallback("my_op")
        assert fb is not None
        assert fb() == "fallback"


class TestErrorAnalyzer:
    """Verify error classification and remedy suggestion."""

    def test_classify_timeout(self):
        analyzer = ErrorAnalyzer()
        error_type = analyzer.classify(TimeoutError("Connection timed out"))
        assert error_type == "timeout"

    def test_classify_validation(self):
        analyzer = ErrorAnalyzer()
        error_type = analyzer.classify(ValueError("Invalid input"))
        assert error_type == "validation"

    def test_classify_auth(self):
        analyzer = ErrorAnalyzer()
        error_type = analyzer.classify(PermissionError("Access denied"))
        assert error_type == "auth"

    def test_classify_unknown(self):
        analyzer = ErrorAnalyzer()
        error_type = analyzer.classify(Exception("Something weird happened"))
        assert error_type == "unknown"

    def test_suggest_remedy(self):
        analyzer = ErrorAnalyzer()
        ctx = ErrorContext(error="timeout", error_type="timeout")
        remedy = analyzer.suggest_remedy(ctx)
        assert len(remedy) > 0

    def test_severity(self):
        analyzer = ErrorAnalyzer()
        ctx = ErrorContext(error="crash", error_type="system")
        assert analyzer.severity(ctx) in ("high", "critical")

    def test_analyze(self):
        analyzer = ErrorAnalyzer()
        ctx = analyzer.analyze(ValueError("bad value"), "parse_input")
        assert ctx.error_type == "validation"
        assert len(ctx.suggested_remedy) > 0


class TestErrorRecoveryService:
    """Verify service wrapper."""

    @pytest.mark.asyncio
    async def test_initialize(self):
        svc = ErrorRecoveryService()
        assert await svc.initialize() is True

    @pytest.mark.asyncio
    async def test_execute_with_recovery_success(self):
        svc = ErrorRecoveryService()
        await svc.initialize()
        success, result, ctx = await svc.execute_with_recovery(
            "test_op", lambda: "ok"
        )
        assert success is True
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_execute_with_fallback(self):
        svc = ErrorRecoveryService()
        await svc.initialize()
        success, result, ctx = await svc.execute_with_recovery(
            "test_op",
            lambda: (_ for _ in ()).throw(Exception("fail")),
            fallback_operations=[lambda: "fallback_ok"],
            max_retries=0,
        )
        assert success is True
        assert result == "fallback_ok"

    @pytest.mark.asyncio
    async def test_analyze_error(self):
        svc = ErrorRecoveryService()
        await svc.initialize()
        ctx = await svc.analyze_error(ValueError("bad"), "test")
        assert ctx.error_type == "validation"

    @pytest.mark.asyncio
    async def test_get_circuit_breaker_status(self):
        svc = ErrorRecoveryService()
        await svc.initialize()
        status = await svc.get_circuit_breaker_status("default")
        assert status["state"] == "closed"

    @pytest.mark.asyncio
    async def test_reset_circuit_breaker(self):
        svc = ErrorRecoveryService()
        await svc.initialize()
        assert await svc.reset_circuit_breaker("default") is True

    @pytest.mark.asyncio
    async def test_get_retry_stats(self):
        svc = ErrorRecoveryService()
        await svc.initialize()
        stats = await svc.get_retry_stats()
        assert "total_attempts" in stats

    @pytest.mark.asyncio
    async def test_health(self):
        svc = ErrorRecoveryService()
        await svc.initialize()
        health = await svc.health()
        assert health["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_shutdown(self):
        svc = ErrorRecoveryService()
        await svc.initialize()
        await svc.shutdown()
        assert not svc.is_initialized()
