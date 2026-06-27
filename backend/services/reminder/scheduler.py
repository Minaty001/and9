"""
AND9 — Reminder Scheduler (Priority 3).

Public interface for adding and managing reminders.
Delegates persistence to storage.py and fires reminders via worker.py.

Usage:
    from backend.services.reminder.scheduler import ReminderEngine

    engine = ReminderEngine()
    engine.add("Take medicine", datetime.now() + timedelta(minutes=5))
    upcoming = engine.get_upcoming()
"""
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from backend.services.reminder import storage

logger = logging.getLogger(__name__)


class ReminderEngine:
    """High-level reminder scheduler.

    Thread-safe. All persistence goes through storage.py.
    Background firing is done by worker.py.
    """

    def add(self, title: str, trigger_time: datetime) -> int:
        """Schedule a new reminder.

        Args:
            title:        Human-readable reminder text.
            trigger_time: When the reminder should fire.

        Returns:
            Reminder ID (SQLite row id).
        """
        rid = storage.add(title, trigger_time)
        logger.info("Reminder added: #%d '%s' at %s", rid, title, trigger_time.isoformat())
        return rid

    def cancel(self, reminder_id: int) -> bool:
        """Cancel a pending reminder by ID."""
        ok = storage.cancel(reminder_id)
        if ok:
            logger.info("Reminder #%d cancelled.", reminder_id)
        else:
            logger.warning("Reminder #%d not found or already fired.", reminder_id)
        return ok

    def get_upcoming(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Return upcoming (not yet due) reminders."""
        return storage.get_upcoming(limit)

    def get_due(self) -> List[Dict[str, Any]]:
        """Return reminders that have passed their trigger time."""
        return storage.get_due()

    def mark_fired(self, reminder_id: int) -> None:
        """Mark a reminder as fired (called by worker)."""
        storage.mark_fired(reminder_id)

    def list_all(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all reminders (optionally filtered by status)."""
        return storage.list_all(status)


# Module-level singleton
_engine: Optional[ReminderEngine] = None


def get_engine() -> ReminderEngine:
    """Get or create the shared ReminderEngine singleton."""
    global _engine
    if _engine is None:
        _engine = ReminderEngine()
    return _engine
