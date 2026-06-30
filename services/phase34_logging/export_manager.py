"""
Phase 34 — Log Export Manager.

Exports log query results in CSV, JSON, or custom file formats.
"""

from __future__ import annotations

import os
import csv
import json
import logging
from io import StringIO
from typing import Any, Dict, List, Optional

from .config import LoggingConfig
from .models import LogEntry, LogQueryResult

logger = logging.getLogger(__name__)


class LogExportManager:
    """Exports log query results in various formats.

    Usage:
        mgr = LogExportManager(config)
        csv_str = mgr.export_csv(query_results)
        json_str = mgr.export_json(query_results)
        mgr.export_to_file(query_results, 'csv', '/path/to/export.csv')
    """

    def __init__(self, config: Optional[LoggingConfig] = None):
        self.config = config or LoggingConfig()

    def export_csv(self, query_results: LogQueryResult) -> str:
        """Export log entries as CSV string.

        Args:
            query_results: LogQueryResult with entries to export.

        Returns:
            CSV-formatted string.
        """
        output = StringIO()
        fieldnames = [
            "timestamp", "level", "service_name", "message",
            "trace_id", "correlation_id", "module", "function",
            "line", "duration_ms", "user_id", "tags",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()

        for entry in query_results.entries:
            row = entry.model_dump(mode="json")
            row["tags"] = ",".join(entry.tags) if entry.tags else ""
            writer.writerow(row)

        return output.getvalue()

    def export_json(self, query_results: LogQueryResult) -> str:
        """Export log entries as JSON string.

        Args:
            query_results: LogQueryResult with entries to export.

        Returns:
            JSON-formatted string.
        """
        data = {
            "total_found": query_results.total_found,
            "query_time_ms": query_results.query_time_ms,
            "truncated": query_results.truncated,
            "entries": [
                entry.model_dump(mode="json") for entry in query_results.entries
            ],
        }
        return json.dumps(data, indent=2, default=str)

    def export_to_file(
        self,
        query_results: LogQueryResult,
        export_format: str = "json",
        path: str = "",
    ) -> bool:
        """Export log entries to a file.

        Args:
            query_results: LogQueryResult with entries to export.
            export_format: "csv" or "json".
            path: Output file path.

        Returns:
            True if export succeeded.
        """
        if export_format == "csv":
            content = self.export_csv(query_results)
        else:
            content = self.export_json(query_results)

        try:
            dir_path = os.path.dirname(path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)
            with open(path, "w") as f:
                f.write(content)
            logger.info("Exported %d log entries to %s", len(query_results.entries), path)
            return True
        except OSError as e:
            logger.error("Failed to export logs to %s: %s", path, e)
            return False
