"""
Tests for Phase 34 — Logging System.
"""

import pytest
from services.phase34_logging import (
    LoggingConfig,
    LogEntry,
    LogQuery,
    LogQueryResult,
    StructuredFormatter,
    ConsoleSink,
    FileSink,
    LogBuffer,
    LoggingService,
)


class TestStructuredFormatter:
    """Verify log formatting."""

    def test_format_json(self):
        formatter = StructuredFormatter()
        entry = LogEntry(level="INFO", message="test", service_name="test_svc")
        output = formatter.format(entry)
        assert '"level": "INFO"' in output
        assert '"message": "test"' in output

    def test_format_text(self):
        config = LoggingConfig(log_format="text")
        formatter = StructuredFormatter(config)
        entry = LogEntry(level="INFO", message="test")
        output = formatter.format(entry)
        assert "INFO" in output
        assert "test" in output

    def test_includes_trace_id(self):
        formatter = StructuredFormatter()
        entry = LogEntry(level="INFO", message="test", trace_id="abc123")
        output = formatter.format(entry)
        assert "abc123" in output


class TestConsoleSink:
    """Verify console sink (capture stdout)."""

    def test_write(self, capsys):
        sink = ConsoleSink()
        entry = LogEntry(level="INFO", message="test console")
        sink.write(entry)
        captured = capsys.readouterr()
        assert "test console" in captured.out or captured.err

    def test_get_count(self):
        sink = ConsoleSink()
        assert sink.get_count() == 0
        sink.write(LogEntry(level="INFO", message="test"))
        assert sink.get_count() == 1


class TestFileSink:
    """Verify file sink."""

    def test_write(self, tmp_path):
        log_file = str(tmp_path / "test.log")
        config = LoggingConfig()
        sink = FileSink(config, file_path=log_file)
        entry = LogEntry(level="INFO", message="test file")
        sink.write(entry)
        content = open(log_file).read()
        assert "test file" in content

    def test_get_count(self):
        sink = FileSink(LoggingConfig(), file_path="/tmp/test_get_count.log")
        sink.write(LogEntry(level="INFO", message="test"))
        assert sink.get_count() >= 1


class TestLogBuffer:
    """Verify async buffer."""

    def test_add_and_size(self):
        buffer = LogBuffer()
        assert buffer.size() == 0
        buffer.add(LogEntry(level="INFO", message="test"))
        assert buffer.size() == 1

    def test_flush(self):
        buffer = LogBuffer()
        buffer.add(LogEntry(level="INFO", message="test1"))
        buffer.add(LogEntry(level="INFO", message="test2"))
        entries = buffer.flush()
        assert len(entries) == 2
        assert buffer.size() == 0

    def test_auto_flush(self):
        config = LoggingConfig(enable_batch_logging=True, batch_size=2)
        buffer = LogBuffer(config)
        result = buffer.add(LogEntry(level="INFO", message="test1"))
        assert result is None  # not flushed yet
        result = buffer.add(LogEntry(level="INFO", message="test2"))
        assert result is not None  # auto-flushed
        assert len(result) >= 1

    def test_get_stats(self):
        buffer = LogBuffer()
        buffer.add(LogEntry(level="INFO", message="test"))
        stats = buffer.get_stats()
        assert stats["current_size"] == 1

    def test_clear(self):
        buffer = LogBuffer()
        buffer.add(LogEntry(level="INFO", message="test"))
        buffer.clear()
        assert buffer.size() == 0


class TestLoggingService:
    """Verify service wrapper."""

    @pytest.mark.asyncio
    async def test_initialize(self):
        svc = LoggingService()
        assert await svc.initialize() is True

    @pytest.mark.asyncio
    async def test_log_info(self):
        svc = LoggingService()
        await svc.initialize()
        entry = await svc.info("test message", module="tests")
        assert entry.level == "INFO"
        assert entry.message == "test message"

    @pytest.mark.asyncio
    async def test_log_all_levels(self):
        svc = LoggingService()
        await svc.initialize()
        e1 = await svc.debug("debug msg")
        e2 = await svc.info("info msg")
        e3 = await svc.warn("warn msg")
        e4 = await svc.error("error msg")
        e5 = await svc.fatal("fatal msg")
        assert e1.level == "DEBUG"
        assert e2.level == "INFO"
        assert e3.level == "WARN"
        assert e4.level == "ERROR"
        assert e5.level == "FATAL"

    @pytest.mark.asyncio
    async def test_query(self):
        svc = LoggingService()
        await svc.initialize()
        await svc.info("test query", module="tests")
        result = await svc.query(LogQuery(levels=["INFO"]))
        assert result.total_found >= 1
        assert len(result.entries) >= 1

    @pytest.mark.asyncio
    async def test_query_with_search(self):
        svc = LoggingService()
        await svc.initialize()
        await svc.info("special search term")
        result = await svc.query(LogQuery(search="special"))
        assert result.total_found >= 1

    @pytest.mark.asyncio
    async def test_set_level(self):
        svc = LoggingService()
        await svc.initialize()
        assert await svc.set_level("DEBUG") is True
        assert await svc.set_level("INVALID") is False

    @pytest.mark.asyncio
    async def test_add_remove_sink(self):
        svc = LoggingService()
        await svc.initialize()
        assert await svc.add_sink("console") is True
        assert await svc.remove_sink("console") is True

    @pytest.mark.asyncio
    async def test_flush(self):
        svc = LoggingService()
        await svc.initialize()
        count = await svc.flush()
        assert count >= 0

    @pytest.mark.asyncio
    async def test_health(self):
        svc = LoggingService()
        await svc.initialize()
        health = await svc.health()
        assert health["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_shutdown(self):
        svc = LoggingService()
        await svc.initialize()
        await svc.shutdown()
        assert not svc.is_initialized()
