"""
AND9 — Query Logger & Debug Mode.

Logs every request through the AND9 pipeline with full context:
raw query, normalized query, detected intent, structured parameters,
execution action, payload, timing, and errors.

Debug mode (AND9_DEBUG=1) prints a formatted debug panel for every
request, showing the full processing pipeline step by step.
"""
import logging
import os
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

_DEBUG_ENABLED = os.environ.get("AND9_DEBUG", "0") == "1"


class QueryLog:
    """A single logged query with full processing context."""
    def __init__(self, raw_query: str, normalized_query: str = "",
                 intent: str = "", parameters: dict = None,
                 action: str = "", payload: dict = None,
                 brain: str = "", execution_time_ms: float = 0.0,
                 success: bool = True, error: str = ""):
        """Initialize a query log entry with full pipeline context.

        Automatically generates an ISO-format timestamp at creation time.

        Args:
            raw_query: Original user input.
            normalized_query: Query after normalization pass.
            intent: Detected intent name.
            parameters: Structured parameters extracted from the query.
            action: Action type dispatched.
            payload: Additional payload data for the action.
            brain: Name of the brain module that processed the query.
            execution_time_ms: Execution duration in milliseconds.
            success: Whether the query was processed successfully.
            error: Error message if processing failed.
        """
        self.timestamp = datetime.now().isoformat()
        self.raw_query = raw_query
        self.normalized_query = normalized_query
        self.intent = intent
        self.parameters = parameters or {}
        self.action = action
        self.payload = payload or {}
        self.brain = brain
        self.execution_time_ms = execution_time_ms
        self.success = success
        self.error = error

    def to_dict(self) -> dict:
        """Serialize the log entry to a dictionary.

        Returns:
            dict: All log fields keyed by name, ready for JSON
            serialisation or analysis.
        """
        return {
            "timestamp": self.timestamp,
            "raw_query": self.raw_query,
            "normalized_query": self.normalized_query,
            "intent": self.intent,
            "parameters": self.parameters,
            "action": self.action,
            "payload": self.payload,
            "brain": self.brain,
            "time_ms": self.execution_time_ms,
            "success": self.success,
            "error": self.error,
        }


class QueryLogger:
    """In-memory query logger with debug output support.

    Stores the last N queries (default 1000) in memory and
    provides debug-format printing when enabled.
    """
    def __init__(self, max_entries: int = 1000):
        """Initialize an in-memory query logger.

        Args:
            max_entries: Maximum number of log entries to retain.
                Older entries are discarded when this limit is exceeded.
        """
        self.logs: list[QueryLog] = []
        self.max_entries = max_entries

    def log(self, raw_query: str, normalized_query: str = "",
            intent: str = "", parameters: dict = None,
            action: str = "", payload: dict = None,
            brain: str = "", execution_time_ms: float = 0.0,
            success: bool = True, error: str = ""):
        """Record a new query with full pipeline context.

        Wraps the provided data in a :class:`QueryLog`, appends it to
        the in-memory ring buffer, and prints a formatted debug panel
        when debug mode is enabled via ``AND9_DEBUG=1``.

        Args:
            raw_query: Original user input.
            normalized_query: Query after normalisation.
            intent: Detected intent name.
            parameters: Structured parameters extracted from the query.
            action: Action type dispatched.
            payload: Additional payload data for the action.
            brain: Name of the brain module that handled the query.
            execution_time_ms: Execution duration in milliseconds.
            success: Whether processing succeeded.
            error: Error message on failure.

        Returns:
            QueryLog: The newly created log entry.
        """
        entry = QueryLog(
            raw_query=raw_query,
            normalized_query=normalized_query,
            intent=intent,
            parameters=parameters or {},
            action=action,
            payload=payload or {},
            brain=brain,
            execution_time_ms=execution_time_ms,
            success=success,
            error=error,
        )
        self.logs.append(entry)
        if len(self.logs) > self.max_entries:
            self.logs = self.logs[-self.max_entries:]

        if _DEBUG_ENABLED:
            _print_debug(entry)

        return entry

    def get_recent(self, limit: int = 50) -> list[dict]:
        """Return the most recent log entries as dictionaries.

        Args:
            limit: Maximum number of entries to return (default 50).

        Returns:
            list[dict]: The last *limit* log entries, each serialised
            via :meth:`QueryLog.to_dict`.
        """
        return [log.to_dict() for log in self.logs[-limit:]]

    def get_stats(self) -> dict:
        """Compute aggregate statistics over all stored log entries.

        Returns:
            dict: Contains ``total_queries``, ``failed_queries``,
            ``success_rate`` (formatted percentage string or ``"N/A"``),
            and ``recent`` (the last 10 log entries as dicts).
        """
        total = len(self.logs)
        failed = sum(1 for log in self.logs if not log.success)
        return {
            "total_queries": total,
            "failed_queries": failed,
            "success_rate": f"{(total - failed) / total * 100:.1f}%" if total else "N/A",
            "recent": self.get_recent(10),
        }

    def clear(self):
        """Remove all stored log entries from memory."""
        self.logs.clear()


def _print_debug(log: QueryLog):
    """Print a formatted debug panel for a query log entry."""
    status = "✅" if log.success else "❌"
    print(
        f"┌─ AND9 DEBUG ──────────────────────\n"
        f"│ QUERY:    {log.raw_query}\n"
        f"│ NORMALIZED: {log.normalized_query}\n"
        f"│ INTENT:   {log.intent}\n"
        f"│ PARAMS:   {log.parameters}\n"
        f"│ ACTION:   {log.action}\n"
        f"│ PAYLOAD:  {log.payload}\n"
        f"│ BRAIN:    {log.brain}\n"
        f"│ TIME:     {log.execution_time_ms:.1f}ms\n"
        f"│ RESULT:   {status}"
        + (f"\n│ ERROR:    {log.error}" if log.error else "")
        + "\n└────────────────────────────────────"
    )


# Singleton for app-wide use
_logger_instance: Optional[QueryLogger] = None


def get_logger() -> QueryLogger:
    """Return the singleton QueryLogger instance.

    Creates the instance on first call and reuses it thereafter for
    app-wide access to query logs.

    Returns:
        QueryLogger: The single shared logger instance.
    """
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = QueryLogger()
    return _logger_instance


def is_debug_enabled() -> bool:
    """Check whether debug mode is enabled.

    Reads the ``AND9_DEBUG`` environment variable at import time.
    When enabled, :meth:`QueryLogger.log` prints a formatted debug
    panel for every query.

    Returns:
        bool: True if ``AND9_DEBUG`` is set to ``"1"``.
    """
    return _DEBUG_ENABLED
