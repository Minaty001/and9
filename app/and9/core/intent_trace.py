"""
AND9 — Intent Trace Logger (Phase 15).

Stores per-query execution traces for debugging, analytics, and memory.

Every query processed by AND9 produces one trace record:

    {
        raw_query:          str,    # Original user input
        normalized_query:   str,    # After QueryNormalizer
        detected_intent:    str,    # e.g., "CALL", "SET_ALARM"
        extracted_entities: dict,   # Contact name, app name, time, etc.
        action:             str,    # ActionType value dispatched
        execution_result:   str,    # "success" | "failure" | "pending"
        execution_time_ms:  float,  # Wall-clock duration in milliseconds
        failure_reason:     str,    # Set if execution_result == "failure"
        timestamp:          float,  # Unix epoch of the query
    }

Storage:
    SQLite table: intent_traces (persistent)
    In-memory ring buffer: last N traces (fast access for context)

Short-term memory:
    The last MAX_SHORT_TERM_TRACES traces are kept in memory.
    The orchestrator/conscious brain can read these for context.
"""
import logging
import sqlite3
import time
import os
import json
from collections import deque
from contextlib import contextmanager
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

_DB_PATH = os.environ.get(
    "AND9_TRACES_DB",
    "/app/.jarvis_data/intent_traces.db"
)
try:
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
except OSError:
    _DB_PATH = os.path.join(os.getcwd(), ".jarvis_data", "intent_traces.db")
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)

# Short-term memory buffer size
MAX_SHORT_TERM_TRACES = int(os.environ.get("AND9_SHORT_TERM_SIZE", "50"))

# In-memory ring buffer for recent traces
_short_term_memory: deque = deque(maxlen=MAX_SHORT_TERM_TRACES)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS intent_traces (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp           REAL    NOT NULL,
    raw_query           TEXT    NOT NULL,
    normalized_query    TEXT,
    detected_intent     TEXT,
    extracted_entities  TEXT,   -- JSON
    action              TEXT,
    execution_result    TEXT    DEFAULT 'pending',
    execution_time_ms   REAL,
    failure_reason      TEXT
);

CREATE INDEX IF NOT EXISTS idx_traces_timestamp
    ON intent_traces(timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_traces_intent
    ON intent_traces(detected_intent);
"""


@contextmanager
def _conn():
    con = sqlite3.connect(_DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    try:
        yield con
    finally:
        con.close()


def init_trace_db() -> None:
    """Initialize the intent traces database schema. Idempotent."""
    with _conn() as con:
        con.executescript(_SCHEMA)
        con.commit()
    logger.info("Intent traces DB initialized: %s", _DB_PATH)


def log_trace(
    raw_query: str,
    normalized_query: str = "",
    detected_intent: str = "",
    extracted_entities: Optional[dict] = None,
    action: str = "",
    execution_result: str = "success",
    execution_time_ms: float = 0.0,
    failure_reason: Optional[str] = None,
) -> int:
    """Log a complete intent execution trace.

    Args:
        raw_query:           Original user input.
        normalized_query:    After normalization pass.
        detected_intent:     Intent name (e.g., "call", "set_alarm").
        extracted_entities:  Dict of entities extracted.
        action:              ActionType dispatched.
        execution_result:    "success" | "failure" | "pending".
        execution_time_ms:   Execution duration in milliseconds.
        failure_reason:      Error message if execution failed.

    Returns:
        Row ID of the inserted trace.

    Example:
        >>> log_trace(
        ...     raw_query="call mummy",
        ...     normalized_query="call mummy",
        ...     detected_intent="call",
        ...     extracted_entities={"contact_name": "mummy"},
        ...     action="call",
        ...     execution_result="success",
        ...     execution_time_ms=12.5,
        ... )
        1
    """
    now = time.time()
    entities_json = json.dumps(extracted_entities or {}, ensure_ascii=False)

    trace = {
        "timestamp": now,
        "raw_query": raw_query,
        "normalized_query": normalized_query,
        "detected_intent": detected_intent,
        "extracted_entities": extracted_entities or {},
        "action": action,
        "execution_result": execution_result,
        "execution_time_ms": execution_time_ms,
        "failure_reason": failure_reason,
    }

    # Add to short-term memory (in-process, fast)
    _short_term_memory.append(trace)

    # Persist to SQLite (durable, survives restarts)
    row_id = 0
    try:
        with _conn() as con:
            cur = con.execute(
                """INSERT INTO intent_traces
                   (timestamp, raw_query, normalized_query, detected_intent,
                    extracted_entities, action, execution_result,
                    execution_time_ms, failure_reason)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    now, raw_query, normalized_query, detected_intent,
                    entities_json, action, execution_result,
                    execution_time_ms, failure_reason,
                )
            )
            con.commit()
            row_id = cur.lastrowid
    except Exception as e:
        logger.warning("Failed to persist trace: %s", e)

    if failure_reason:
        logger.debug(
            "TRACE [%s] intent=%s action=%s result=FAILURE reason=%s (%.1fms)",
            raw_query[:40], detected_intent, action, failure_reason, execution_time_ms
        )
    else:
        logger.debug(
            "TRACE [%s] intent=%s action=%s result=%s (%.1fms)",
            raw_query[:40], detected_intent, action, execution_result, execution_time_ms
        )

    return row_id


def get_short_term_memory() -> List[Dict[str, Any]]:
    """Return the last N traces from in-memory buffer.

    Used by the Conscious Brain for context-aware responses.

    Returns:
        List of trace dicts, most recent last.
    """
    return list(_short_term_memory)


def get_recent_traces(limit: int = 20) -> List[Dict[str, Any]]:
    """Fetch recent traces from SQLite.

    Args:
        limit: Number of traces to return.

    Returns:
        List of trace dicts, most recent first.
    """
    try:
        with _conn() as con:
            rows = con.execute(
                "SELECT * FROM intent_traces ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            ).fetchall()
        result = []
        for row in rows:
            d = dict(row)
            try:
                d["extracted_entities"] = json.loads(d.get("extracted_entities") or "{}")
            except Exception:
                d["extracted_entities"] = {}
            result.append(d)
        return result
    except Exception as e:
        logger.warning("Failed to fetch traces: %s", e)
        return []


def get_intent_stats() -> Dict[str, int]:
    """Return count of each intent type from all traces.

    Useful for analytics and subconscious brain pattern learning.

    Returns:
        Dict mapping intent → count.
    """
    try:
        with _conn() as con:
            rows = con.execute(
                "SELECT detected_intent, COUNT(*) as cnt "
                "FROM intent_traces "
                "GROUP BY detected_intent "
                "ORDER BY cnt DESC"
            ).fetchall()
        return {row["detected_intent"]: row["cnt"] for row in rows if row["detected_intent"]}
    except Exception as e:
        logger.warning("Failed to fetch intent stats: %s", e)
        return {}


# ── Context Manager for timing ────────────────────────────────────

class TraceContext:
    """Context manager that automatically times and logs a trace.

    Usage:
        with TraceContext("call mummy") as ctx:
            ctx.set_normalized("call mummy")
            ctx.set_intent("call", {"contact_name": "mummy"})
            ctx.set_action("call")
            result = execute_call(...)
            ctx.set_result("success")
    """

    def __init__(self, raw_query: str):
        self.raw_query = raw_query
        self.normalized_query = ""
        self.detected_intent = ""
        self.extracted_entities: dict = {}
        self.action = ""
        self.execution_result = "pending"
        self.failure_reason: Optional[str] = None
        self._start: float = 0.0

    def __enter__(self):
        self._start = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed_ms = (time.time() - self._start) * 1000
        if exc_type is not None:
            self.execution_result = "failure"
            self.failure_reason = str(exc_val)
        log_trace(
            raw_query=self.raw_query,
            normalized_query=self.normalized_query,
            detected_intent=self.detected_intent,
            extracted_entities=self.extracted_entities,
            action=self.action,
            execution_result=self.execution_result,
            execution_time_ms=elapsed_ms,
            failure_reason=self.failure_reason,
        )
        return False  # Don't suppress exceptions

    def set_normalized(self, normalized: str):
        self.normalized_query = normalized

    def set_intent(self, intent: str, entities: dict = None):
        self.detected_intent = intent
        self.extracted_entities = entities or {}

    def set_action(self, action: str):
        self.action = action

    def set_result(self, result: str, failure_reason: str = None):
        self.execution_result = result
        self.failure_reason = failure_reason


# Auto-initialize on import
try:
    init_trace_db()
except Exception as _e:
    logger.warning("Could not initialize traces DB: %s", _e)
