"""
app/reminders — Standalone reminder engine with SQLite persistence.

Background worker that fires due reminders, with an in-process scheduler
engine for managing reminder lifecycle.
"""

from app.reminders.scheduler import ReminderEngine, get_engine
from app.reminders.worker import start_worker, stop_worker, register_callback
from app.reminders.storage import (
    init_storage, add, get_due, get_upcoming,
    mark_fired, cancel, list_all,
)

__all__ = [
    "ReminderEngine", "get_engine",
    "start_worker", "stop_worker", "register_callback",
    "init_storage", "add", "get_due", "get_upcoming",
    "mark_fired", "cancel", "list_all",
]
