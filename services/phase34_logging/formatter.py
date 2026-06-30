"""
Phase 34 — Structured Formatter.

Formats LogEntry objects into JSON strings with trace and correlation IDs.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Optional

from .config import LoggingConfig
from .models import LogEntry

logger = logging.getLogger(__name__)


class StructuredFormatter:
    """Formats LogEntry objects into JSON strings.

    Usage:
        formatter = StructuredFormatter(config)
        json_str = formatter.format(entry)
    """

    def __init__(self, config: Optional[LoggingConfig] = None):
        self.config = config or LoggingConfig()

    def format(self, entry: LogEntry) -> str:
        """Format a LogEntry as a JSON string.

        Args:
            entry: The LogEntry to format.

        Returns:
            JSON string representation.
        """
        if self.config.log_format == "text":
            return self._format_text(entry)

        return self._format_json(entry)

    def _format_json(self, entry: LogEntry) -> str:
        """Format as structured JSON."""
        data = {
            "level": entry.level,
            "service": entry.service_name,
            "message": entry.message,
            "timestamp": entry.timestamp.isoformat(),
            "trace_id": entry.trace_id,
            "correlation_id": entry.correlation_id,
            "module": entry.module,
            "function": entry.function,
            "line": entry.line,
            "duration_ms": entry.duration_ms,
            "tags": entry.tags,
            "user_id": entry.user_id,
        }
        if entry.metadata:
            data["metadata"] = entry.metadata
        return json.dumps(data, default=str)

    def _format_text(self, entry: LogEntry) -> str:
        """Format as plain text."""
        ts = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        return (
            f"[{ts}] [{entry.level}] [{entry.service_name}] "
            f"{entry.message}"
            + (f" (trace={entry.trace_id})" if entry.trace_id else "")
        )
