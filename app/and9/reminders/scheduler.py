"""
AND9 — Reminder Scheduler (Phase 8 Rebuild).

Manages reminder scheduling with SQLite persistence.
Background thread fires notifications when trigger_at is reached.

Reminders are stored in the DB (reminders/db.py) and survive restarts.

Supported commands:
    remind me / set reminder / reminder lagao
    5 minute baad yaad dilana / 10 second baad yaad dilana
    1 hour baad yaad dilana
    remind me after 5 seconds / after 10 minutes / after 2 hours
"""
import logging
import time
from datetime import datetime
from typing import Optional, Any

from app.reminders.scheduler import get_engine
from app.and9.utils.time_parser import format_duration, format_time

logger = logging.getLogger(__name__)

class ReminderScheduler:
    """Legacy Adapter: Schedule and manage reminders.

    Delegates to the new standalone `app.reminders` engine.
    """

    @staticmethod
    def schedule(trigger_at: dict, label: str,
                 events_sys: Optional[Any] = None) -> dict:
        """Schedule a new reminder via the reminders engine.

        Parses the trigger_at dict (supports 'relative' and 'absolute' types),
        persists the reminder, and returns a response dict.

        Args:
            trigger_at: Dict with 'type' ('relative'/'absolute'),
                'seconds' (for relative), or 'hour'/'minute'/'timestamp' (for absolute).
            label: Reminder description/title string.
            events_sys: Optional EventSystem reference for event integration.

        Returns:
            Response dict with 'response' text, 'action', 'payload', and 'persisted' flag.
        """
        t_type = trigger_at.get("type", "unknown")

        if t_type == "relative":
            seconds = trigger_at.get("seconds", 0)
            trigger_ts = time.time() + seconds
            display = format_duration(seconds) + " baad"
        elif t_type == "absolute":
            trigger_ts = trigger_at.get("timestamp")
            if trigger_ts is None:
                now = datetime.now()
                hour = trigger_at.get("hour", 0)
                minute = trigger_at.get("minute", 0)
                from datetime import timedelta
                t = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if t <= now:
                    t += timedelta(days=1)
                trigger_ts = t.timestamp()
            display = format_time(trigger_at.get("hour", 0), trigger_at.get("minute", 0))
        else:
            return {
                "response": "Reminder ka time samajh nahi aaya. Jaise: '5 minute baad' ya '7 PM'. ⏰",
                "action": "SET_REMINDER",
                "payload": {},
                "persisted": False,
            }

        try:
            trigger_dt = datetime.fromtimestamp(trigger_ts)
            engine = get_engine()
            rid = engine.add(label, trigger_dt)
            persisted = True
        except Exception as e:
            logger.error("Failed to persist reminder: %s", e)
            rid = None
            persisted = False

        return {
            "response": f"Reminder {display} ke liye set kar diya! '{label}' ⏰",
            "action": "SET_REMINDER",
            "payload": {
                "id": rid,
                "title": label,
                "trigger_at": trigger_ts,
                "trigger_datetime": trigger_dt.isoformat() if persisted else None,
                "type": t_type,
            },
            "persisted": persisted,
        }

    @staticmethod
    def list_upcoming() -> dict:
        """List upcoming reminders from the engine.

        Retrieves up to 10 upcoming reminders and formats them for display.

        Returns:
            Response dict with a human-readable list of reminders in 'response'
            and the raw reminder list in 'payload'.
        """
        reminders = get_engine().get_upcoming(limit=10)
        if not reminders:
            return {
                "response": "Koi upcoming reminder nahi hai. ✅",
                "action": "SET_REMINDER",
                "payload": {"reminders": []},
            }

        items = []
        for r in reminders:
            try:
                dt = datetime.fromisoformat(r["trigger_time"])
                items.append(f"• {r['title']} ({dt.strftime('%d %b %I:%M %p')})")
            except Exception:
                items.append(f"• {r['title']}")

        return {
            "response": "Aapke upcoming reminders:\n" + "\n".join(items),
            "action": "SET_REMINDER",
            "payload": {"reminders": reminders},
        }

    @staticmethod
    def cancel(reminder_id: int) -> dict:
        """Cancel a reminder by its ID.

        Args:
            reminder_id: Integer ID of the reminder to cancel.

        Returns:
            Response dict indicating whether the cancellation succeeded
            and the reminder ID.
        """
        success = get_engine().cancel(reminder_id)
        return {
            "response": f"Reminder #{reminder_id} cancel kar diya! ✅" if success
                       else f"Reminder #{reminder_id} nahi mila ya already fired ho gaya.",
            "action": "SET_REMINDER",
            "payload": {"cancelled": success, "id": reminder_id},
        }

def start_scheduler() -> None:
    """No-op legacy starter (replaced by app.reminders.worker).

    Logs a debug message indicating the legacy entry point is deprecated.
    """
    # No-op: main.py now calls start_worker() from app.reminders.worker
    logger.debug("Legacy start_scheduler() called — ignoring (replaced by worker).")

def stop_scheduler() -> None:
    """No-op legacy stopper (no cleanup needed).

    Provided for API compatibility with the old scheduler interface.
    """
    pass
