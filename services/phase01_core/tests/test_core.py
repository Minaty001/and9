"""
Unit tests for Phase 1 — Core Service.

Tests cover:
    - Error hierarchy (all exception types)
    - Core models (BrainResult, ProcessingResult)
    - CoreService lifecycle (init, health, shutdown)
    - CoreService process method
    - Logging setup
"""

import pytest
import json
import time
from datetime import datetime

from services.phase01_core import (
    CoreService,
    BrainResult,
    ProcessingResult,
    ServiceStatus,
    BrainType,
    IntentType,
    JarvisError,
    ServiceError,
    ProcessingError,
    ValidationError,
    ConfigError,
    CoreConfig,
)
from services.phase01_core.errors import (
    InitializationError,
    ShutdownError,
    HealthCheckError,
    TimeoutError,
    PipelineError,
    InvalidQueryError,
    InvalidParameterError,
    MissingConfigError,
    InvalidConfigError,
)
from services.phase01_core.models import ProcessingStage, PipelineStageResult
from services.phase01_core.logging_setup import setup_logging, JSONFormatter


# ═════════════════════════════════════════════════════════════════
# Error Hierarchy Tests
# ═════════════════════════════════════════════════════════════════


class TestErrors:
    """Verify the error hierarchy behaves correctly."""

    def test_base_error(self):
        err = JarvisError("test error", code="TEST", details={"key": "val"})
        assert err.message == "test error"
        assert err.code == "TEST"
        assert err.details == {"key": "val"}
        d = err.to_dict()
        assert d["error"] is True
        assert d["code"] == "TEST"
        assert d["message"] == "test error"

    def test_service_error_chain(self):
        assert issubclass(InitializationError, ServiceError)
        assert issubclass(ShutdownError, ServiceError)
        assert issubclass(HealthCheckError, ServiceError)
        err = InitializationError("init failed")
        assert err.code == "SERVICE_INIT_FAILED"

    def test_processing_error_chain(self):
        assert issubclass(TimeoutError, ProcessingError)
        assert issubclass(PipelineError, ProcessingError)
        err = TimeoutError("took too long")
        assert "timed out" in err.message.lower()

    def test_validation_error_chain(self):
        assert issubclass(InvalidQueryError, ValidationError)
        assert issubclass(InvalidParameterError, ValidationError)
        err = InvalidQueryError()
        assert err.code == "INVALID_QUERY"

    def test_config_error_chain(self):
        assert issubclass(MissingConfigError, ConfigError)
        assert issubclass(InvalidConfigError, ConfigError)
        err = MissingConfigError()
        assert err.code == "MISSING_CONFIG"


# ═════════════════════════════════════════════════════════════════
# Model Tests
# ═════════════════════════════════════════════════════════════════


class TestModels:
    """Verify Pydantic models validate correctly."""

    def test_brain_result_defaults(self):
        r = BrainResult()
        assert r.response == ""
        assert r.action is None
        assert r.brain == BrainType.REFLEX
        assert r.intent is None
        assert r.success is True
        assert r.execution_time_ms == 0.0

    def test_brain_result_to_dict(self):
        r = BrainResult(
            response="Hello!",
            action="open_app",
            brain=BrainType.REFLEX,
            intent=IntentType.OPEN_APP,
            execution_time_ms=12.5,
        )
        d = r.to_dict()
        assert d["response"] == "Hello!"
        assert d["action"] == "open_app"
        assert d["brain"] == "reflex"
        assert d["intent"] == "open_app"
        assert d["execution_time_ms"] == 12.5
        assert d["success"] is True

    def test_brain_result_serialization(self):
        r = BrainResult(response="test", brain=BrainType.REFLEX)
        raw = r.model_dump_json()
        assert '"response": "test"' in raw
        assert '"brain": "reflex"' in raw

    def test_processing_result_defaults(self):
        r = ProcessingResult(query="hello")
        assert r.query == "hello"
        assert r.intent == IntentType.UNKNOWN
        assert r.confidence == 0.0
        assert r.success is True
        assert r.stages == []

    def test_processing_result_with_stages(self):
        r = ProcessingResult(
            query="test",
            stages=[
                PipelineStageResult(
                    stage=ProcessingStage.RECEIVED,
                    time_ms=1.0,
                ),
                PipelineStageResult(
                    stage=ProcessingStage.COMPLETED,
                    confidence=0.95,
                    time_ms=10.0,
                ),
            ],
        )
        assert len(r.stages) == 2
        assert r.stages[0].stage == ProcessingStage.RECEIVED
        assert r.stages[1].confidence == 0.95

    def test_service_status_healthy(self):
        s = ServiceStatus(
            status="healthy",
            service_name="test",
            initialized=True,
            uptime_seconds=100.0,
        )
        assert s.status == "healthy"
        assert s.initialized is True
        assert s.error is None

    def test_enum_values(self):
        assert BrainType.REFLEX.value == "reflex"
        assert BrainType.CONSCIOUS.value == "conscious"
        assert IntentType.OPEN_APP.value == "open_app"
        assert IntentType.UNKNOWN.value == "unknown"


# ═════════════════════════════════════════════════════════════════
# Service Tests
# ═════════════════════════════════════════════════════════════════


class TestCoreService:
    """Verify CoreService lifecycle and processing."""

    @pytest.mark.asyncio
    async def test_initialize(self):
        svc = CoreService()
        result = await svc.initialize()
        assert result is True
        assert svc.is_initialized() is True

    @pytest.mark.asyncio
    async def test_health_after_init(self):
        svc = CoreService()
        await svc.initialize()
        health = await svc.health()
        assert health["status"] == "healthy"
        assert health["initialized"] is True
        assert health["service_name"] == "jarvis_core"
        assert health["uptime_seconds"] >= 0

    @pytest.mark.asyncio
    async def test_stats(self):
        svc = CoreService()
        await svc.initialize()
        stats = await svc.stats()
        assert stats["service"] == "jarvis_core"
        assert stats["initialized"] is True

    @pytest.mark.asyncio
    async def test_process_valid_query(self):
        svc = CoreService()
        await svc.initialize()
        result = await svc.process("hello jarvis")
        assert result.query == "hello jarvis"
        assert result.normalized_query == "hello jarvis"
        assert result.intent == IntentType.UNKNOWN  # default before routing
        assert len(result.stages) >= 1

    @pytest.mark.asyncio
    async def test_process_empty_query(self):
        svc = CoreService()
        await svc.initialize()
        with pytest.raises(InvalidQueryError):
            await svc.process("")
        with pytest.raises(InvalidQueryError):
            await svc.process("   ")

    @pytest.mark.asyncio
    async def test_shutdown(self):
        svc = CoreService()
        await svc.initialize()
        await svc.shutdown()
        assert svc.is_initialized() is False

    @pytest.mark.asyncio
    async def test_register_sub_service(self):
        svc = CoreService()
        await svc.initialize()

        # Create a minimal sub-service
        from services.base import ServiceBase

        class MockService(ServiceBase):
            async def initialize(self): return True
            async def shutdown(self): pass
            async def health(self): return {"status": "healthy"}
            async def stats(self): return {"mock": True}

        mock = MockService(name="mock")
        await mock.initialize()
        svc.register_service("mock", mock)
        assert "mock" in svc.sub_services
        assert svc.get_service("mock") is mock

    @pytest.mark.asyncio
    async def test_register_duplicate_service(self):
        svc = CoreService()
        await svc.initialize()
        from services.base import ServiceBase
        class M(ServiceBase):
            async def initialize(self): return True
            async def shutdown(self): pass
            async def health(self): return {"status": "healthy"}
            async def stats(self): return {}

        m = M(name="dup")
        svc.register_service("dup", m)
        with pytest.raises(ValueError):
            svc.register_service("dup", m)

    @pytest.mark.asyncio
    async def test_health_with_sub_services(self):
        svc = CoreService()
        await svc.initialize()
        from services.base import ServiceBase
        class H(ServiceBase):
            async def initialize(self): return True
            async def shutdown(self): pass
            async def health(self): return {"status": "healthy"}
            async def stats(self): return {}

        h = H(name="healthy_sub")
        await h.initialize()
        svc.register_service("healthy_sub", h)
        health = await svc.health()
        assert health["status"] == "healthy"
        assert "healthy_sub" in health["sub_services"]


# ═════════════════════════════════════════════════════════════════
# Config Tests
# ═════════════════════════════════════════════════════════════════


class TestConfig:
    """Verify CoreConfig defaults and validation."""

    def test_default_config(self):
        cfg = CoreConfig()
        assert cfg.service_name == "jarvis_core"
        assert cfg.log_level == "INFO"
        assert cfg.log_format == "json"
        assert cfg.deterministic_execution is True
        assert cfg.local_first is True
        assert cfg.max_response_length == 2000

    def test_config_override(self):
        cfg = CoreConfig(service_name="custom", log_level="DEBUG", local_first=False)
        assert cfg.service_name == "custom"
        assert cfg.log_level == "DEBUG"
        assert cfg.local_first is False


# ═════════════════════════════════════════════════════════════════
# Logging Tests
# ═════════════════════════════════════════════════════════════════


class TestLogging:
    """Verify logging setup and JSON formatting."""

    def test_json_formatter(self):
        formatter = JSONFormatter()
        import logging as log_mod
        record = log_mod.LogRecord(
            name="test",
            level=log_mod.INFO,
            pathname=__file__,
            lineno=42,
            msg="test message",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "test"
        assert parsed["message"] == "test message"
        assert "timestamp" in parsed

    def test_json_formatter_with_extra(self):
        formatter = JSONFormatter()
        import logging as log_mod
        record = log_mod.LogRecord(
            name="test",
            level=log_mod.INFO,
            pathname=__file__,
            lineno=99,
            msg="extra test",
            args=(),
            exc_info=None,
        )
        record.user_id = "123"
        record.query = "hello"
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["user_id"] == "123"
        assert parsed["query"] == "hello"

    def test_setup_logging_defaults(self):
        logger = setup_logging("test_logger")
        assert logger.name == "test_logger"
        assert logger.level == 20  # INFO

    def test_setup_logging_debug(self):
        logger = setup_logging("debug_logger", level="DEBUG")
        assert logger.level == 10  # DEBUG

    def test_setup_logging_text(self):
        logger = setup_logging("text_logger", log_format="text")
        assert logger.name == "text_logger"
        # Smoke test: logging should not crash
        logger.info("This is a text log message")
