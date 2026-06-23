"""
╔══════════════════════════════════════════════════╗
║           MICRO NEURAL BRAIN - LOGGER            ║
║   Lightweight logging with memory awareness      ║
╚══════════════════════════════════════════════════╝
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from config import LOG_CONFIG


class MemoryAwareLogger:
    """Logger with RAM usage awareness - stays under budget."""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._setup_logger()

    def _setup_logger(self):
        self.logger = logging.getLogger("MicroBrain")
        self.logger.setLevel(getattr(logging, LOG_CONFIG["level"].upper(), logging.INFO))

        formatter = logging.Formatter(LOG_CONFIG["format"])

        # Console handler (always)
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)

        # File handler (rotating, size-limited)
        try:
            fh = RotatingFileHandler(
                LOG_CONFIG["file"],
                maxBytes=LOG_CONFIG["max_size_mb"] * 1024 * 1024,
                backupCount=LOG_CONFIG["backup_count"],
            )
            fh.setFormatter(formatter)
            self.logger.addHandler(fh)
        except (IOError, OSError):
            pass  # No file logging if we can't write

        # Disable propagation to avoid duplicate logs
        self.logger.propagate = False

    def debug(self, msg, *args, **kwargs):
        self.logger.debug(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self.logger.info(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.logger.warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.logger.error(msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        self.logger.critical(msg, *args, **kwargs)

    def get_logger(self):
        return self.logger


# Singleton instance
brain_logger = MemoryAwareLogger()

def get_logger():
    """Get the global brain logger instance."""
    return brain_logger
