"""
AND9 — Reminder Database (Phase 8).

SQLite persistence layer for reminders.
Uses stdlib sqlite3 — no additional dependencies.

Schema:
    reminders(
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        title       TEXT    NOT NULL,
        created_at  REAL    NOT NULL,   -- epoch seconds
        trigger_at  REAL    NOT NULL,   -- epoch seconds
        status      TEXT    DEFAULT 'pending'
                            CHECK(status IN ('pending', 'fired', 'cancelled'))
    )

Status lifecycle:
    pending → fired     (background scheduler fires the notification)
    pending → cancelled (user cancels)
"""
import sqlite3
import logging
import os
import time
from contextlib import contextmanager
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# Database path (configurable via environment)
_DB_PATH = os.environ.get(
    "AND9_REMINDERS_DB",
    "/app/.jarvis_data/reminders.db"
)

# Ensure the directory exists
os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS reminders (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT    NOT NULL,
    created_at  REAL    NOT NULL,
    trigger_at  REAL    NOT NULL,
    status      TEXT    NOT NULL DEFAULT 'pending'
                        CHECK(status IN ('pending', 'fired', 'cancelled'))
);

CREATE INDEX IF NOT EXISTS idx_reminders_trigger
    ON reminders(trigger_at)
    WHERE status = 'pending';
"""


@contextmanager
def _conn():
    """Thread-safe SQLite connection context manager."""
    con = sqlite3.connect(_DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    try:
        yield con
    finally:
        con.close()


def init_db() -> None:
    """Initialize the reminders database schema.

    Safe to call multiple times (idempotent).
    Called automatically on first import.
    """
    with _conn() as con:
        con.executescript(_SCHEMA)
        con.commit()
    logger.info("Reminders DB initialized: %s", _DB_PATH)


def add_reminder(title: str, trigger_at: float) -> int:
    """Insert a new reminder into the database.

    Args:
        title:      Human-readable reminder text.
        trigger_at: Unix timestamp when the reminder should fire.

    Returns:
        The new reminder's row ID.

    Example:
        >>> import time
        >>> rid = add_reminder("Buy milk", time.time() + 300)
        >>> print(rid)  # → 1
    """
    now = time.time()
    with _conn() as con:
        cur = con.execute(
            "INSERT INTO reminders (title, created_at, trigger_at, status) "
            "VALUES (?, ?, ?, 'pending')",
            (title, now, trigger_at)
        )
        con.commit()
        row_id = cur.lastrowid
    logger.info("Reminder #%d added: '%s' at %.0f", row_id, title, trigger_at)
    return row_id


def get_pending() -> List[Dict[str, Any]]:
    """Return all pending reminders whose trigger time has passed.

    Used by the background scheduler to fire notifications.

    Returns:
        List of reminder dicts: {id, title, created_at, trigger_at, status}
    """
    now = time.time()
    with _conn() as con:
        rows = con.execute(
            "SELECT id, title, created_at, trigger_at, status "
            "FROM reminders "
            "WHERE status = 'pending' AND trigger_at <= ? "
            "ORDER BY trigger_at ASC",
            (now,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_upcoming(limit: int = 10) -> List[Dict[str, Any]]:
    """Return upcoming pending reminders (not yet due).

    Args:
        limit: Maximum number of reminders to return.

    Returns:
        List of reminder dicts sorted by trigger_at.
    """
    now = time.time()
    with _conn() as con:
        rows = con.execute(
            "SELECT id, title, created_at, trigger_at, status "
            "FROM reminders "
            "WHERE status = 'pending' AND trigger_at > ? "
            "ORDER BY trigger_at ASC "
            "LIMIT ?",
            (now, limit)
        ).fetchall()
    return [dict(r) for r in rows]


def mark_fired(reminder_id: int) -> None:
    """Mark a reminder as fired.

    Args:
        reminder_id: The reminder's row ID.
    """
    with _conn() as con:
        con.execute(
            "UPDATE reminders SET status = 'fired' WHERE id = ?",
            (reminder_id,)
        )
        con.commit()
    logger.debug("Reminder #%d marked fired.", reminder_id)


def cancel_reminder(reminder_id: int) -> bool:
    """Cancel a pending reminder.

    Args:
        reminder_id: The reminder's row ID.

    Returns:
        True if cancelled, False if not found or already fired.
    """
    with _conn() as con:
        cur = con.execute(
            "UPDATE reminders SET status = 'cancelled' "
            "WHERE id = ? AND status = 'pending'",
            (reminder_id,)
        )
        con.commit()
        return cur.rowcount > 0


def list_all(status: Optional[str] = None) -> List[Dict[str, Any]]:
    """List reminders, optionally filtered by status.

    Args:
        status: 'pending', 'fired', 'cancelled', or None for all.

    Returns:
        List of reminder dicts.
    """
    with _conn() as con:
        if status:
            rows = con.execute(
                "SELECT * FROM reminders WHERE status = ? ORDER BY trigger_at DESC",
                (status,)
            ).fetchall()
        else:
            rows = con.execute(
                "SELECT * FROM reminders ORDER BY trigger_at DESC"
            ).fetchall()
    return [dict(r) for r in rows]


# Auto-initialize on import
try:
    init_db()
except Exception as _e:
    logger.warning("Could not initialize reminders DB: %s", _e)
