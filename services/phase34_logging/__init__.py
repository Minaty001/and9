"""
Phase 34 — Logging System
==========================

Centralized logging with structured JSON output, multiple sinks,
log levels, async buffering, and query interface.

Components:
    - StructuredFormatter: JSON log entry formatting
    - ConsoleSink: Console output sink
    - FileSink: Rotating file output sink
    - LogBuffer: Async buffering with auto-flush
    - LoggingService: ServiceBase wrapper
"""

from .config import LoggingConfig
from .models import LogEntry, LogQuery, LogQueryResult
from .formatter import StructuredFormatter
from .sinks import ConsoleSink, FileSink, TelemetrySink, AuditSink
from .buffer import LogBuffer
from .export_manager import LogExportManager
from .service import LoggingService

__all__ = [
    "LoggingConfig",
    "LogEntry",
    "LogQuery",
    "LogQueryResult",
    "StructuredFormatter",
    "ConsoleSink",
    "FileSink",
    "TelemetrySink",
    "AuditSink",
    "LogBuffer",
    "LogExportManager",
    "LoggingService",
]
