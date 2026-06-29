"""
AND9 — Reminder Storage (Priority 3).

Standalone SQLite persistence layer for the reminder engine.
Independent of the and9/reminders/db.py (which is AND9-brain-specific).
This module is used by scheduler.py and worker.py.

Schema v1 (legacy):
    reminders(id, title, trigger_time, status, created_at)

Schema v2 (current):
    reminders_v2(id, user_id, session_id, title, trigger_time,
                 repeat_rule, repeat_end, status, created_at,
                 fired_at, execution_time, retry_count,
                 failure_reason, created_by)
"""
import sqlite3
import logging
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from contextlib import contextmanager
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

IST = ZoneInfo("Asia/Kolkata")

_DB_PATH = os.environ.get(
    "AND9_REMINDERS_STORAGE_DB",
    "/app/.jarvis_data/reminders_engine.db",
)

try:
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
except (OSError, PermissionError):
    logger.warning("Cannot create reminders engine DB directory at %s; using in-memory fallback", _DB_PATH)
    _USE_MEMORY_FALLBACK = True
else:
    _USE_MEMORY_FALLBACK = False

_SCHEMA = """
CREATE TABLE IF NOT EXISTS reminders (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    title        TEXT    NOT NULL,
    trigger_time TEXT    NOT NULL,
    status       TEXT    NOT NULL DEFAULT 'pending'
                         CHECK(status IN ('pending', 'fired', 'cancelled')),
    created_at   TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_rem_trigger
    ON reminders(trigger_time)
    WHERE status = 'pending';

-- v2 schema with full feature support
CREATE TABLE IF NOT EXISTS reminders_v2 (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        TEXT    NOT NULL DEFAULT 'default',
    session_id     TEXT,
    title          TEXT    NOT NULL,
    trigger_time   TEXT    NOT NULL,
    repeat_rule    TEXT    NOT NULL DEFAULT '',
    repeat_days    TEXT,
    repeat_end     TEXT,
    status         TEXT    NOT NULL DEFAULT 'pending'
                     CHECK(status IN ('pending','fired','cancelled','paused','snoozed')),
    created_at     TEXT    NOT NULL DEFAULT (datetime('now')),
    fired_at       TEXT,
    execution_time TEXT,
    retry_count    INTEGER NOT NULL DEFAULT 0,
    failure_reason TEXT,
    created_by     TEXT    DEFAULT 'user'
);

CREATE INDEX IF NOT EXISTS idx_rem_v2_trigger
    ON reminders_v2(trigger_time)
    WHERE status IN ('pending', 'snoozed');

CREATE INDEX IF NOT EXISTS idx_rem_v2_user
    ON reminders_v2(user_id, status);
"""

_PENDING_STATUSES = ('pending', 'snoozed')


_MEM_CONN = None

@contextmanager
def _conn():
    """Context manager providing a SQLite connection (file or thread-safe shared in-memory fallback)."""
    global _MEM_CONN
    if _USE_MEMORY_FALLBACK:
        if _MEM_CONN is None:
            _MEM_CONN = sqlite3.connect(":memory:", check_same_thread=False)
            _MEM_CONN.row_factory = sqlite3.Row
        yield _MEM_CONN
    else:
        con = sqlite3.connect(_DB_PATH, check_same_thread=False)
        con.row_factory = sqlite3.Row
        try:
            yield con
        finally:
            con.close()


def init_storage() -> None:
    """Initialise the storage DB schema (idempotent)."""
    with _conn() as con:
        con.executescript(_SCHEMA)
        _ensure_column(con, "reminders_v2", "repeat_days", "TEXT")
        if not _USE_MEMORY_FALLBACK:
            con.commit()
    logger.info("Reminder storage DB initialised: %s", _DB_PATH)


def _ensure_column(con: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
    """Add a missing column to an existing table if needed."""
    cols = [row[1] for row in con.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in cols:
        con.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


# ── CRUD ─────────────────────────────────────────────────────────────


def add(title: str, trigger_time: datetime,
        repeat_rule: str = "",
        repeat_days: Optional[str] = None,
        user_id: str = "default",
        session_id: Optional[str] = None,
        repeat_end: Optional[str] = None) -> int:
    """Insert a reminder into v2 table (only).

    Args:
        title: Reminder label/text.
        trigger_time: When the reminder should fire.
        repeat_rule: '' (once), 'daily', 'weekly', 'weekdays', 'monthly', 'yearly'.
        user_id: User identifier.
        session_id: Optional session identifier.
        repeat_end: ISO string for when to stop repeating.

    Returns:
        Row id from v2 table.
    """
    # Ensure trigger_time is timezone-aware and in IST
    if trigger_time.tzinfo is None:
        trigger_time = trigger_time.replace(tzinfo=IST)
    else:
        trigger_time = trigger_time.astimezone(IST)

    iso = trigger_time.isoformat()
    with _conn() as con:
        # v2 table only to prevent duplication
        cur = con.execute(
            "INSERT INTO reminders_v2 "
            "(title, trigger_time, repeat_rule, repeat_days, user_id, session_id, repeat_end) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (title, iso, repeat_rule, repeat_days, user_id, session_id, repeat_end or None),
        )
        con.commit()
    rid = cur.lastrowid
    logger.info("Reminder stored: #%d '%s' at %s (repeat=%s)", rid, title, iso, repeat_rule or "once")
    return rid


def get_due() -> List[Dict[str, Any]]:
    """Return all pending/snoozed reminders whose trigger_time has passed.

    Checks both legacy and v2 tables for backward compatibility.
    """
    now_iso = datetime.now(IST).isoformat()
    results = []
    with _conn() as con:
        # v2 table
        rows = con.execute(
            "SELECT id, user_id, session_id, title, trigger_time, "
            "repeat_rule, repeat_end, status, created_at, fired_at, "
            "retry_count, failure_reason, created_by "
            "FROM reminders_v2 "
            "WHERE status IN ('pending', 'snoozed') AND trigger_time <= ? "
            "ORDER BY trigger_time ASC",
            (now_iso,),
        ).fetchall()
        results = [dict(r) for r in rows]

        # Legacy table (only if v2 returns nothing, for migration)
        if not results:
            rows = con.execute(
                "SELECT id, title, trigger_time, status, created_at "
                "FROM reminders "
                "WHERE status = 'pending' AND trigger_time <= ? "
                "ORDER BY trigger_time ASC",
                (now_iso,),
            ).fetchall()
            results = [dict(r) for r in rows]
    return results


def get_upcoming(limit: int = 10, user_id: str = "default") -> List[Dict[str, Any]]:
    """Return upcoming reminders still in the future."""
    now_iso = datetime.now(IST).isoformat()
    with _conn() as con:
        rows = con.execute(
            "SELECT id, user_id, session_id, title, trigger_time, "
            "repeat_rule, repeat_days, repeat_end, status, created_at "
            "FROM reminders_v2 "
            "WHERE user_id = ? AND status IN ('pending', 'snoozed') AND trigger_time > ? "
            "ORDER BY trigger_time ASC LIMIT ?",
            (user_id, now_iso, limit),
        ).fetchall()
    return [dict(r) for r in rows]


# ── Status Management ────────────────────────────────────────────────


def mark_fired(reminder_id: int, from_v2: bool = True) -> None:
    """Mark a reminder as fired and record the fired timestamp.

    Args:
        reminder_id: ID of the reminder to mark fired.
        from_v2: True if this is a v2 reminder, False for legacy.
    """
    now_iso = datetime.now(IST).isoformat()
    with _conn() as con:
        if from_v2:
            con.execute(
                "UPDATE reminders_v2 SET status = 'fired', fired_at = ? WHERE id = ?",
                (now_iso, reminder_id),
            )
        else:
            con.execute(
                "UPDATE reminders SET status = 'fired' WHERE id = ?",
                (reminder_id,),
            )
        con.commit()


def cancel(reminder_id: int, from_v2: bool = True) -> bool:
    """Cancel a pending/snoozed reminder. Returns True if cancelled."""
    table = "reminders_v2" if from_v2 else "reminders"
    with _conn() as con:
        cur = con.execute(
            f"UPDATE {table} SET status = 'cancelled' "
            "WHERE id = ? AND status IN ('pending', 'snoozed')",
            (reminder_id,),
        )
        con.commit()
    return cur.rowcount > 0


def pause(reminder_id: int) -> bool:
    """Pause a pending reminder. Returns True if paused."""
    with _conn() as con:
        cur = con.execute(
            "UPDATE reminders_v2 SET status = 'paused' "
            "WHERE id = ? AND status = 'pending'",
            (reminder_id,),
        )
        con.commit()
    return cur.rowcount > 0


def resume(reminder_id: int) -> bool:
    """Resume a paused reminder. Returns True if resumed."""
    with _conn() as con:
        cur = con.execute(
            "UPDATE reminders_v2 SET status = 'pending' "
            "WHERE id = ? AND status = 'paused'",
            (reminder_id,),
        )
        con.commit()
    return cur.rowcount > 0


def snooze(reminder_id: int, minutes: int = 5) -> bool:
    """Snooze a fired/pending reminder by adding minutes to trigger_time."""
    now = datetime.now(IST)
    new_time = now + timedelta(minutes=minutes)
    new_iso = new_time.isoformat()
    with _conn() as con:
        cur = con.execute(
            "UPDATE reminders_v2 SET status = 'pending', trigger_time = ? "
            "WHERE id = ? AND status IN ('pending', 'fired', 'snoozed')",
            (new_iso, reminder_id),
        )
        con.commit()
    if cur.rowcount > 0:
        logger.info("Reminder #%d snoozed for %d min → %s", reminder_id, minutes, new_iso)
    return cur.rowcount > 0


# ── Queries ──────────────────────────────────────────────────────────


def get_active(user_id: str = "default") -> List[Dict[str, Any]]:
    """Return all non-terminal reminders for a user."""
    with _conn() as con:
        rows = con.execute(
            "SELECT id, user_id, session_id, title, trigger_time, "
            "repeat_rule, repeat_days, repeat_end, status, created_at, "
            "retry_count, created_by "
            "FROM reminders_v2 "
            "WHERE user_id = ? AND status IN ('pending', 'paused', 'snoozed') "
            "ORDER BY trigger_time ASC",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_completed(user_id: str = "default", limit: int = 20) -> List[Dict[str, Any]]:
    """Return recently fired reminders for a user."""
    with _conn() as con:
        rows = con.execute(
            "SELECT id, user_id, title, trigger_time, repeat_rule, repeat_days, "
            "status, created_at, fired_at "
            "FROM reminders_v2 "
            "WHERE user_id = ? AND status = 'fired' "
            "ORDER BY fired_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def get_by_id(reminder_id: int) -> Optional[Dict[str, Any]]:
    """Look up a single reminder by ID (checks v2 first, then legacy)."""
    with _conn() as con:
        row = con.execute(
            "SELECT * FROM reminders_v2 WHERE id = ?", (reminder_id,)
        ).fetchone()
        if row:
            return dict(row)
        row = con.execute(
            "SELECT * FROM reminders WHERE id = ?", (reminder_id,)
        ).fetchone()
        return dict(row) if row else None


def clear_all(user_id: str = "default") -> int:
    """Cancel all pending/snoozed reminders for a user. Returns count."""
    with _conn() as con:
        cur = con.execute(
            "UPDATE reminders_v2 SET status = 'cancelled' "
            "WHERE user_id = ? AND status IN ('pending', 'snoozed')",
            (user_id,),
        )
        con.commit()
    count = cur.rowcount
    if count:
        logger.info("Cleared %d reminders for user '%s'", count, user_id)
    return count


def list_all(status: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all reminders (v2 table), optionally filtered by status."""
    with _conn() as con:
        if status:
            rows = con.execute(
            "SELECT * FROM reminders_v2 WHERE status = ? ORDER BY trigger_time DESC",
                (status,),
            ).fetchall()
        else:
            rows = con.execute(
                "SELECT * FROM reminders_v2 ORDER BY trigger_time DESC"
            ).fetchall()
    return [dict(r) for r in rows]


# ── Recurring Helper ─────────────────────────────────────────────────


def reschedule_recurring(reminder_id: int, next_trigger: datetime) -> int:
    """Create a new reminder entry for the next occurrence in a recurring series.

    Args:
        reminder_id: ID of the original (fired) reminder.
        next_trigger: The next trigger time.

    Returns:
        ID of the newly created reminder.
    """
    original = get_by_id(reminder_id)
    if not original:
        raise ValueError(f"Reminder #{reminder_id} not found for reschedule")

    return add(
        title=original.get("title", "Recurring Reminder"),
        trigger_time=next_trigger,
        repeat_rule=original.get("repeat_rule", ""),
        repeat_days=original.get("repeat_days"),
        user_id=original.get("user_id", "default"),
        session_id=original.get("session_id"),
        repeat_end=original.get("repeat_end"),
    )


# Auto-init on import
try:
    init_storage()
except Exception as _e:
    logger.warning("Could not init reminder storage: %s", _e)
