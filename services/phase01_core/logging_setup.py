"""
Phase 1 — Structured Logging Setup.

Provides JSON and text log formatters with rotation support.

Usage:
    from services.phase01_core.logging_setup import setup_logging
    logger = setup_logging("my_service", level="INFO", log_format="json")
    logger.info("Hello world", extra={"key": "value"})
"""

import os
import sys
import json
import logging
import logging.handlers
from typing import Optional
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """Emit log records as JSON lines.

    Each line is a JSON object with timestamp, level, logger, message,
    and any extra fields passed via the `extra` dict.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        # Include exception info if present
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Include any extra fields passed to logger
        for key, value in record.__dict__.items():
            if key not in ("args", "asctime", "created", "exc_info", "exc_text",
                           "filename", "funcName", "id", "levelname", "levelno",
                           "lineno", "module", "msecs", "message", "msg",
                           "name", "pathname", "process", "processName",
                           "relativeCreated", "stack_info", "thread", "threadName"):
                log_entry[key] = value

        return json.dumps(log_entry, default=str)


def setup_logging(
    service_name: str = "jarvis",
    level: str = "INFO",
    log_format: str = "json",
    log_file: Optional[str] = None,
    max_size_mb: int = 5,
    backup_count: int = 2,
) -> logging.Logger:
    """Configure and return a structured logger.

    Args:
        service_name: Name for the logger instance.
        level: Log level (DEBUG, INFO, WARNING, ERROR).
        log_format: "json" for JSON lines, "text" for human-readable.
        log_file: Optional file path. If None, logs to stderr.
        max_size_mb: Max log file size before rotation.
        backup_count: Number of rotated backups to keep.

    Returns:
        Configured logger instance.
    """
    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.handlers.clear()

    # Choose formatter
    if log_format == "json":
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
        )

    # Handler: file (with rotation) or stderr
    if log_file:
        os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)
        handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_size_mb * 1024 * 1024,
            backupCount=backup_count,
        )
    else:
        handler = logging.StreamHandler(sys.stderr)

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Silence noisy third-party loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    return logger
