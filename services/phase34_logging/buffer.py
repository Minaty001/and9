"""
Phase 34 — Log Buffer.

Buffer for asynchronous log batching with auto-flush.
"""

from __future__ import annotations

import threading
import logging
from typing import List, Optional

from .config import LoggingConfig
from .models import LogEntry

logger = logging.getLogger(__name__)


class LogBuffer:
    """Thread-safe buffer for async log batching.

    Accumulates log entries and flushes when batch_size is reached
    or on demand.

    Usage:
        buffer = LogBuffer(config)
        buffer.add(entry)
        buffer.add(entry)
        entries = buffer.flush()  # get all buffered entries
    """

    def __init__(self, config: Optional[LoggingConfig] = None):
        self.config = config or LoggingConfig()
        self._lock = threading.RLock()
        self._entries: List[LogEntry] = []
        self._total_buffered = 0
        self._total_flushed = 0

    def add(self, entry: LogEntry) -> Optional[List[LogEntry]]:
        """Add an entry to the buffer.

        If batch logging is enabled and buffer reaches batch_size,
        auto-flush returns the batch. Otherwise returns None.

        Args:
            entry: The LogEntry to buffer.

        Returns:
            List of entries if auto-flushed, None otherwise.
        """
        with self._lock:
            self._entries.append(entry)
            self._total_buffered += 1

            if self.config.enable_batch_logging and len(self._entries) >= self.config.batch_size:
                return self._flush_internal()
            return None

    def flush(self) -> List[LogEntry]:
        """Flush all buffered entries.

        Returns:
            List of all buffered LogEntry objects.
        """
        with self._lock:
            return self._flush_internal()

    def _flush_internal(self) -> List[LogEntry]:
        """Internal flush without lock."""
        entries = list(self._entries)
        self._entries.clear()
        self._total_flushed += len(entries)
        return entries

    def size(self) -> int:
        """Get the current buffer size.

        Returns:
            Number of entries in the buffer.
        """
        with self._lock:
            return len(self._entries)

    def get_stats(self) -> dict:
        """Get buffer statistics.

        Returns:
            Dict with stats.
        """
        with self._lock:
            return {
                "current_size": len(self._entries),
                "total_buffered": self._total_buffered,
                "total_flushed": self._total_flushed,
            }

    def clear(self) -> None:
        """Clear all buffered entries without flushing."""
        with self._lock:
            self._entries.clear()
