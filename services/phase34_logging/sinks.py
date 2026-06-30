"""
Phase 34 — Log Sinks (Console, File, Telemetry, Audit).

Output destinations for log entries with file rotation support,
including time-based rotation and gzip compression.
"""

from __future__ import annotations

import os
import sys
import gzip
import shutil
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from .config import LoggingConfig
from .models import LogEntry
from .formatter import StructuredFormatter

logger = logging.getLogger(__name__)


class ConsoleSink:
    """Writes formatted log entries to console (stdout/stderr).

    Usage:
        sink = ConsoleSink(config)
        sink.write(entry)
    """

    def __init__(self, config: Optional[LoggingConfig] = None):
        self.config = config or LoggingConfig()
        self.formatter = StructuredFormatter(self.config)
        self._entries_written = 0

    def write(self, entry: LogEntry) -> None:
        """Write a log entry to console.

        Args:
            entry: The LogEntry to write.
        """
        formatted = self.formatter.format(entry)
        stream = sys.stderr if entry.level in ("ERROR", "FATAL", "CRITICAL") else sys.stdout
        stream.write(formatted + "\n")
        stream.flush()
        self._entries_written += 1

    def get_count(self) -> int:
        """Get number of entries written."""
        return self._entries_written


class FileSink:
    """Writes formatted log entries to file with rotation.

    Supports size-based rotation and time-based rotation (configurable
    interval). Optionally compresses rotated files with gzip.

    Usage:
        sink = FileSink(config)
        sink.write(entry)
    """

    def __init__(
        self,
        config: Optional[LoggingConfig] = None,
        file_path: Optional[str] = None,
        rotation_interval_hours: Optional[int] = None,
    ):
        self.config = config or LoggingConfig()
        self.formatter = StructuredFormatter(self.config)
        self.file_path = file_path or self.config.sinks.get("file", {}).get("path", "logs/jarvis.log")
        self._entries_written = 0
        self._rotation_interval = rotation_interval_hours or self.config.rotation_interval_hours
        self._last_rotation_time: Optional[datetime] = None

        # Ensure directory exists
        log_dir = os.path.dirname(self.file_path)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

        # Record last rotation time from existing file
        if os.path.exists(self.file_path):
            self._last_rotation_time = datetime.fromtimestamp(
                os.path.getmtime(self.file_path), tz=timezone.utc,
            )

    def write(self, entry: LogEntry) -> None:
        """Write a log entry to file.

        Args:
            entry: The LogEntry to write.
        """
        self._check_rotation(entry.timestamp)
        formatted = self.formatter.format(entry)
        try:
            with open(self.file_path, "a") as f:
                f.write(formatted + "\n")
            self._entries_written += 1
        except IOError as e:
            logger.error("Failed to write log to file %s: %s", self.file_path, e)

    def _check_rotation(self, entry_time: Optional[datetime] = None) -> None:
        """Check if file rotation is needed (size or time-based).

        Args:
            entry_time: Timestamp of the current log entry.
        """
        if not os.path.exists(self.file_path):
            return

        # Size-based rotation
        try:
            size_mb = os.path.getsize(self.file_path) / (1024 * 1024)
            if size_mb >= self.config.max_file_size_mb:
                self._rotate()
                return
        except OSError:
            pass

        # Time-based rotation
        if self._rotation_interval and self._last_rotation_time:
            now = entry_time or datetime.now(timezone.utc)
            elapsed = (now - self._last_rotation_time).total_seconds()
            if elapsed >= self._rotation_interval * 3600:
                self._rotate()

    def _rotate(self) -> None:
        """Rotate the log file."""
        if not os.path.exists(self.file_path):
            return
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rotated_path = f"{self.file_path}.{timestamp}"
        try:
            os.rename(self.file_path, rotated_path)
            logger.debug("Rotated log file to %s", rotated_path)

            # Compress if enabled
            if self.config.enable_rotation_compression:
                self._compress(rotated_path)

            self._last_rotation_time = datetime.now(timezone.utc)
        except OSError as e:
            logger.error("Failed to rotate log file: %s", e)

        # Clean up old rotated files
        self._cleanup_old()

    def _compress(self, file_path: str) -> None:
        """Compress a rotated log file with gzip.

        Args:
            file_path: Path to the file to compress.
        """
        gz_path = file_path + ".gz"
        try:
            with open(file_path, "rb") as f_in:
                with gzip.open(gz_path, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
            os.remove(file_path)
            logger.debug("Compressed rotated log to %s", gz_path)
        except OSError as e:
            logger.error("Failed to compress rotated log %s: %s", file_path, e)

    def _cleanup_old(self) -> None:
        """Remove rotated log files older than retention period."""
        log_dir = os.path.dirname(self.file_path)
        base_name = os.path.basename(self.file_path)
        cutoff = datetime.now() - timedelta(days=self.config.file_retention_days)

        if not log_dir:
            log_dir = "."
        try:
            for fname in os.listdir(log_dir):
                if fname.startswith(base_name + "."):
                    fpath = os.path.join(log_dir, fname)
                    mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
                    if mtime < cutoff:
                        os.remove(fpath)
                        logger.debug("Removed old log file: %s", fpath)
        except OSError:
            pass

    def get_count(self) -> int:
        """Get number of entries written."""
        return self._entries_written


class TelemetrySink:
    """Sink for telemetry log entries (info level with telemetry tag).

    Wraps a FileSink configured to write to the telemetry log path.

    Usage:
        sink = TelemetrySink(config)
        sink.write(entry)
    """

    def __init__(self, config: Optional[LoggingConfig] = None, file_path: Optional[str] = None):
        self.config = config or LoggingConfig()
        path = file_path or self.config.telemetry_log_path
        self._file_sink = FileSink(self.config, file_path=path)

    def write(self, entry: LogEntry) -> None:
        """Write a telemetry log entry.

        Only writes entries at INFO level or above that have a
        'telemetry' tag.

        Args:
            entry: The LogEntry to write.
        """
        if entry.level in ("INFO", "WARN", "ERROR", "FATAL", "CRITICAL") and "telemetry" in entry.tags:
            self._file_sink.write(entry)

    def get_count(self) -> int:
        """Get number of entries written."""
        return self._file_sink.get_count()


class AuditSink:
    """Sink for audit log entries (audit category events).

    Wraps a FileSink configured to write to the audit log path.

    Usage:
        sink = AuditSink(config)
        sink.write(entry)
    """

    def __init__(self, config: Optional[LoggingConfig] = None, file_path: Optional[str] = None):
        self.config = config or LoggingConfig()
        path = file_path or self.config.audit_log_path
        self._file_sink = FileSink(self.config, file_path=path)

    def write(self, entry: LogEntry) -> None:
        """Write an audit log entry.

        Only writes entries with 'audit' category or tag.

        Args:
            entry: The LogEntry to write.
        """
        if "audit" in entry.tags:
            self._file_sink.write(entry)

    def get_count(self) -> int:
        """Get number of entries written."""
        return self._file_sink.get_count()
