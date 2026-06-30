"""
Phase 34 — Logging Service.

ServiceBase wrapper for the centralized logging system.
"""

from __future__ import annotations

import time
import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from services.base.service_base import ServiceBase
from .config import LoggingConfig
from .models import LogEntry, LogQuery, LogQueryResult
from .formatter import StructuredFormatter
from .sinks import ConsoleSink, FileSink, TelemetrySink, AuditSink
from .buffer import LogBuffer
from .export_manager import LogExportManager

logger = logging.getLogger(__name__)

LOG_LEVELS = {
    "DEBUG": 10,
    "INFO": 20,
    "WARN": 30,
    "WARNING": 30,
    "ERROR": 40,
    "FATAL": 50,
    "CRITICAL": 50,
}


class LoggingService(ServiceBase):
    """Centralized logging service with structured output and multiple sinks.

    Usage:
        svc = LoggingService()
        await svc.initialize()
        await svc.info("System started", module="main")
        await svc.error("Something failed", error=e)
        results = await svc.query(LogQuery(levels=["ERROR"]))
    """

    def __init__(self, config: Optional[LoggingConfig] = None):
        super().__init__(name="jarvis_logging", version="1.0.0")
        self.config = config or LoggingConfig()
        self.formatter: Optional[StructuredFormatter] = None
        self.console_sink: Optional[ConsoleSink] = None
        self.file_sink: Optional[FileSink] = None
        self.telemetry_sink: Optional[TelemetrySink] = None
        self.audit_sink: Optional[AuditSink] = None
        self.buffer: Optional[LogBuffer] = None
        self.export_manager: Optional[LogExportManager] = None
        self._entries: List[LogEntry] = []
        self._max_entries = 10000
        self._start_time = 0.0

    async def initialize(self) -> bool:
        self._start_time = time.time()
        try:
            self.formatter = StructuredFormatter(self.config)
            self.console_sink = ConsoleSink(self.config)
            file_path = self.config.sinks.get("file", {}).get("path", "logs/jarvis.log")
            self.file_sink = FileSink(self.config, file_path)
            self.telemetry_sink = TelemetrySink(self.config)
            self.audit_sink = AuditSink(self.config)
            self.buffer = LogBuffer(self.config)
            self.export_manager = LogExportManager(self.config)
            self._metrics.reset()
            self._initialized = True
            logger.info("LoggingService initialized")
            return True
        except Exception as e:
            logger.error("LoggingService init failed: %s", e)
            return False

    async def shutdown(self) -> None:
        logger.info("LoggingService shutting down...")
        await self.flush()
        self._initialized = False

    async def log(
        self,
        level: str,
        message: str,
        module: str = "",
        function: str = "",
        line: int = 0,
        metadata: Optional[Dict] = None,
        tags: Optional[List[str]] = None,
        category: str = "general",
        correlation_id: str = "",
        user_id: str = "",
        duration_ms: float = 0.0,
        trace_id: str = "",
    ) -> LogEntry:
        """Log an entry at the specified level.

        Args:
            level: Log level (DEBUG/INFO/WARN/ERROR/FATAL).
            message: Log message.
            module: Source module name.
            function: Source function name.
            line: Source line number.
            metadata: Additional metadata dict.
            tags: List of tags.
            correlation_id: Correlation ID.
            user_id: User ID.
            duration_ms: Duration in milliseconds.
            trace_id: Trace ID (auto-generated if empty).

        Returns:
            The created LogEntry.
        """
        if not self.formatter:
            raise RuntimeError("LoggingService not initialized")

        resolved_tags = tags or []
        # If category is audit, automatically add audit tag for routing
        if category == "audit" and "audit" not in resolved_tags:
            resolved_tags = list(resolved_tags) + ["audit"]

        entry = LogEntry(
            level=level.upper(),
            service_name=self.name,
            message=message,
            trace_id=trace_id or (uuid.uuid4().hex[:12] if self.config.enable_trace_ids else ""),
            module=module,
            function=function,
            line=line,
            metadata=metadata or {},
            tags=resolved_tags,
            category=category,
            correlation_id=correlation_id,
            user_id=user_id,
            duration_ms=duration_ms,
        )

        # Store in memory
        self._entries.append(entry)
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-5000:]

        # Write to sinks (routed by category/tag)
        if self.console_sink:
            self.console_sink.write(entry)
        if self.file_sink:
            self.file_sink.write(entry)
        if self.telemetry_sink:
            self.telemetry_sink.write(entry)
        if self.audit_sink:
            self.audit_sink.write(entry)

        # Buffer for async
        if self.buffer:
            if self.config.enable_async_logging:
                self.buffer.add(entry)

        self._metrics.counter(f"log_{level.lower()}", 1)
        self._metrics.counter("log_total", 1)

        return entry

    async def debug(
        self, *args, module: str = "", function: str = "", line: int = 0, **kwargs
    ) -> LogEntry:
        """Log at DEBUG level. Supports (message) or (module, message) call patterns."""
        message, module = self._resolve_log_args(args, module)
        return await self.log("DEBUG", message, module=module, function=function, line=line, **kwargs)

    async def info(
        self, *args, module: str = "", function: str = "", line: int = 0, **kwargs
    ) -> LogEntry:
        """Log at INFO level. Supports (message) or (module, message) call patterns."""
        message, module = self._resolve_log_args(args, module)
        return await self.log("INFO", message, module=module, function=function, line=line, **kwargs)

    async def warn(
        self, *args, module: str = "", function: str = "", line: int = 0, **kwargs
    ) -> LogEntry:
        """Log at WARN level. Supports (message) or (module, message) call patterns."""
        message, module = self._resolve_log_args(args, module)
        return await self.log("WARN", message, module=module, function=function, line=line, **kwargs)

    async def error(
        self, *args, module: str = "", function: str = "", line: int = 0, **kwargs
    ) -> LogEntry:
        """Log at ERROR level. Supports (message) or (module, message) call patterns."""
        message, module = self._resolve_log_args(args, module)
        return await self.log("ERROR", message, module=module, function=function, line=line, **kwargs)

    async def fatal(
        self, *args, module: str = "", function: str = "", line: int = 0, **kwargs
    ) -> LogEntry:
        """Log at FATAL level. Supports (message) or (module, message) call patterns."""
        message, module = self._resolve_log_args(args, module)
        return await self.log("FATAL", message, module=module, function=function, line=line, **kwargs)

    @staticmethod
    def _resolve_log_args(args, module: str) -> tuple:
        """Resolve message and module from flexible arg patterns."""
        if len(args) == 2:
            # Pattern: (module, message)
            return args[1], args[0]
        elif len(args) == 1:
            # Pattern: (message,)
            return args[0], module
        return "", module

    async def query_logs(self, level: str = "") -> LogQueryResult:
        """Query log entries by level.

        Args:
            level: Log level to filter by (e.g. 'INFO', 'ERROR').

        Returns:
            LogQueryResult with matching entries.
        """
        query = LogQuery(levels=[level] if level else [])
        return await self.query(query)

    async def query(self, query: LogQuery) -> LogQueryResult:
        """Query log entries.

        Args:
            query: LogQuery with filter parameters.

        Returns:
            LogQueryResult with matching entries.
        """
        t0 = time.perf_counter()
        results = list(self._entries)

        # Apply filters
        if query.levels:
            results = [e for e in results if e.level in query.levels]
        if query.start_time:
            results = [e for e in results if e.timestamp >= query.start_time]
        if query.end_time:
            results = [e for e in results if e.timestamp <= query.end_time]
        if query.service_name:
            results = [e for e in results if e.service_name == query.service_name]
        if query.trace_id:
            results = [e for e in results if e.trace_id == query.trace_id]
        if query.correlation_id:
            results = [e for e in results if e.correlation_id == query.correlation_id]
        if query.user_id:
            results = [e for e in results if e.user_id == query.user_id]
        if query.tags:
            results = [e for e in results if any(t in e.tags for t in query.tags)]
        if query.search:
            results = [e for e in results if query.search.lower() in e.message.lower()]

        total = len(results)
        truncated = total > (query.limit + query.offset)

        # Apply pagination
        results = results[query.offset: query.offset + query.limit]

        elapsed = (time.perf_counter() - t0) * 1000
        self._metrics.counter("log_queries", 1)

        return LogQueryResult(
            entries=results,
            total_found=total,
            query_time_ms=round(elapsed, 2),
            truncated=truncated,
        )

    async def set_level(self, level: str) -> bool:
        """Set the default log level.

        Args:
            level: Log level string.

        Returns:
            True if set.
        """
        if level.upper() not in LOG_LEVELS:
            return False
        self.config.default_level = level.upper()
        return True

    async def add_sink(self, sink_type: str, config: Optional[Dict] = None) -> bool:
        """Add a log sink.

        Args:
            sink_type: "console" or "file".
            config: Sink configuration.

        Returns:
            True if added.
        """
        if sink_type == "console":
            self.console_sink = ConsoleSink(self.config)
            return True
        elif sink_type == "file":
            path = config.get("path") if config else None
            self.file_sink = FileSink(self.config, path)
            return True
        return False

    async def remove_sink(self, sink_type: str) -> bool:
        """Remove a log sink.

        Args:
            sink_type: "console" or "file".

        Returns:
            True if removed.
        """
        if sink_type == "console":
            self.console_sink = None
            return True
        elif sink_type == "file":
            self.file_sink = None
            return True
        return False

    # ── Log Export ─────────────────────────────────────────────────

    async def export_logs_csv(self, query_result: LogQueryResult) -> str:
        """Export log entries as CSV.

        Args:
            query_result: LogQueryResult to export.

        Returns:
            CSV string.
        """
        if not self.export_manager:
            raise RuntimeError("LoggingService not initialized")
        return self.export_manager.export_csv(query_result)

    async def export_logs_json(self, query_result: LogQueryResult) -> str:
        """Export log entries as JSON.

        Args:
            query_result: LogQueryResult to export.

        Returns:
            JSON string.
        """
        if not self.export_manager:
            raise RuntimeError("LoggingService not initialized")
        return self.export_manager.export_json(query_result)

    async def export_logs_to_file(
        self,
        query_result: LogQueryResult,
        export_format: str = "json",
        path: str = "",
    ) -> bool:
        """Export log entries to a file.

        Args:
            query_result: LogQueryResult to export.
            export_format: "csv" or "json".
            path: Output file path.

        Returns:
            True if successful.
        """
        if not self.export_manager:
            raise RuntimeError("LoggingService not initialized")
        return self.export_manager.export_to_file(query_result, export_format, path)

    async def flush(self) -> int:
        """Flush buffered log entries.

        Returns:
            Number of entries flushed.
        """
        if not self.buffer:
            return 0
        entries = self.buffer.flush()
        for entry in entries:
            if self.console_sink:
                self.console_sink.write(entry)
            if self.file_sink:
                self.file_sink.write(entry)
        self._metrics.counter("buffer_flushes", 1)
        return len(entries)

    async def health(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "service_name": self.name,
            "version": self.version,
            "initialized": self._initialized,
            "uptime_seconds": round(uptime, 1),
            "total_entries": len(self._entries),
            "buffer_size": self.buffer.size() if self.buffer else 0,
        }

    async def stats(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        return {
            "service": self.name,
            "version": self.version,
            "uptime_seconds": round(uptime, 1),
            "total_entries": len(self._entries),
            "buffer_stats": self.buffer.get_stats() if self.buffer else {},
            "console_count": self.console_sink.get_count() if self.console_sink else 0,
            "file_count": self.file_sink.get_count() if self.file_sink else 0,
            "metrics": self._metrics.snapshot(),
        }
