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
        self.logs: list[QueryLog] = []
        self.max_entries = max_entries

    def log(self, raw_query: str, normalized_query: str = "",
            intent: str = "", parameters: dict = None,
            action: str = "", payload: dict = None,
            brain: str = "", execution_time_ms: float = 0.0,
            success: bool = True, error: str = ""):
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
        return [log.to_dict() for log in self.logs[-limit:]]

    def get_stats(self) -> dict:
        total = len(self.logs)
        failed = sum(1 for log in self.logs if not log.success)
        return {
            "total_queries": total,
            "failed_queries": failed,
            "success_rate": f"{(total - failed) / total * 100:.1f}%" if total else "N/A",
            "recent": self.get_recent(10),
        }

    def clear(self):
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
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = QueryLogger()
    return _logger_instance


def is_debug_enabled() -> bool:
    return _DEBUG_ENABLED
