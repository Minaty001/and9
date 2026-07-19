"""
AND9 — Reminder Storage (Priority 3).

Standalone SQLite persistence layer for the reminder engine.
Independent of the and9/reminders/db.py (which is AND9-brain-specific).
This module is used by scheduler.py and worker.py.

Schema:
    reminders(
        id           INTEGER PRIMARY KEY,
        title        TEXT    NOT NULL,
        trigger_time TEXT    NOT NULL,   -- ISO 8601 datetime string
        status       TEXT    NOT NULL DEFAULT 'pending'
                             CHECK(status IN ('pending', 'fired', 'cancelled'))
    )
"""
import sqlite3
import logging
import os
import time
from datetime import datetime
from contextlib import contextmanager
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DB_PATH = os.environ.get(
    "AND9_REMINDERS_STORAGE_DB",
    os.path.join(project_root, ".jarvis_data", "reminders_engine.db"),
)

try:
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
except PermissionError:
    _DB_PATH = os.path.join(os.getcwd(), ".jarvis_data", "reminders_engine.db")
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)

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
"""


@contextmanager
def _conn():
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
        con.commit()
    logger.info("Reminder storage DB initialised: %s", _DB_PATH)


def add(title: str, trigger_time: datetime) -> int:
    """Insert a reminder and return its row id."""
    iso = trigger_time.isoformat()
    with _conn() as con:
        cur = con.execute(
            "INSERT INTO reminders (title, trigger_time) VALUES (?, ?)",
            (title, iso),
        )
        con.commit()
    logger.info("Reminder stored: '%s' at %s", title, iso)
    return cur.lastrowid


def get_due() -> List[Dict[str, Any]]:
    """Return all pending reminders whose trigger_time has passed."""
    now_iso = datetime.now().isoformat()
    with _conn() as con:
        rows = con.execute(
            "SELECT id, title, trigger_time, status, created_at "
            "FROM reminders "
            "WHERE status = 'pending' AND trigger_time <= ? "
            "ORDER BY trigger_time ASC",
            (now_iso,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_upcoming(limit: int = 10) -> List[Dict[str, Any]]:
    """Return pending reminders not yet due."""
    now_iso = datetime.now().isoformat()
    with _conn() as con:
        rows = con.execute(
            "SELECT id, title, trigger_time, status, created_at "
            "FROM reminders "
            "WHERE status = 'pending' AND trigger_time > ? "
            "ORDER BY trigger_time ASC LIMIT ?",
            (now_iso, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def mark_fired(reminder_id: int) -> None:
    """Mark a reminder as fired."""
    with _conn() as con:
        con.execute(
            "UPDATE reminders SET status = 'fired' WHERE id = ?",
            (reminder_id,),
        )
        con.commit()


def cancel(reminder_id: int) -> bool:
    """Cancel a pending reminder. Returns True if cancelled."""
    with _conn() as con:
        cur = con.execute(
            "UPDATE reminders SET status = 'cancelled' "
            "WHERE id = ? AND status = 'pending'",
            (reminder_id,),
        )
        con.commit()
    return cur.rowcount > 0


def list_all(status: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all reminders, optionally filtered by status."""
    with _conn() as con:
        if status:
            rows = con.execute(
                "SELECT * FROM reminders WHERE status = ? ORDER BY trigger_time DESC",
                (status,),
            ).fetchall()
        else:
            rows = con.execute(
                "SELECT * FROM reminders ORDER BY trigger_time DESC"
            ).fetchall()
    return [dict(r) for r in rows]


# Auto-init on import
try:
    init_storage()
except Exception as _e:
    logger.warning("Could not init reminder storage: %s", _e)
