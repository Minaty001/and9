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
import threading
import time
from datetime import datetime
from typing import Optional, Any

from app.and9.reminders import db as reminder_db
from app.and9.utils.time_parser import format_duration, format_time

logger = logging.getLogger(__name__)

# How often the background scheduler polls the DB (seconds)
_POLL_INTERVAL = 10

# Singleton scheduler thread
_scheduler_thread: Optional[threading.Thread] = None
_scheduler_stop = threading.Event()


class ReminderScheduler:
    """Schedule and manage reminders with SQLite persistence.

    Usage:
        scheduler = ReminderScheduler()
        result = scheduler.schedule(
            trigger_at={"type": "relative", "seconds": 300},
            label="Take medicine"
        )
    """

    @staticmethod
    def schedule(trigger_at: dict, label: str,
                 events_sys: Optional[Any] = None) -> dict:
        """Schedule a reminder and persist it to the database.

        Args:
            trigger_at: Time dict from time_parser.parse_time():
                - {"type": "relative", "seconds": N}
                - {"type": "absolute", "hour": N, "minute": N,
                   "timestamp": epoch, ...}
            label:      Reminder title.
            events_sys: Unused (kept for backwards compatibility).

        Returns:
            Dict with scheduling result.

        Examples:
            >>> ReminderScheduler.schedule(
            ...     {"type": "relative", "seconds": 300},
            ...     "Take medicine"
            ... )
            {'response': 'Reminder 5 minutes baad set ho gaya! ⏰', ...}
        """
        t_type = trigger_at.get("type", "unknown")

        # ── Calculate absolute trigger timestamp ──────────────────
        if t_type == "relative":
            seconds = trigger_at.get("seconds", 0)
            trigger_ts = time.time() + seconds
            display = format_duration(seconds) + " baad"

        elif t_type == "absolute":
            trigger_ts = trigger_at.get("timestamp")
            if trigger_ts is None:
                # Reconstruct from hour/minute
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
                "response": "Reminder ka time samajh nahi aaya. "
                            "Jaise: '5 minute baad' ya '7 PM'. ⏰",
                "action": "SET_REMINDER",
                "payload": {},
                "persisted": False,
            }

        # ── Persist to SQLite ─────────────────────────────────────
        try:
            rid = reminder_db.add_reminder(label, trigger_ts)
            persisted = True
            logger.info("Reminder #%d scheduled: '%s' at %.0f", rid, label, trigger_ts)
        except Exception as e:
            logger.error("Failed to persist reminder: %s", e)
            rid = None
            persisted = False

        trigger_dt = datetime.fromtimestamp(trigger_ts).isoformat()

        return {
            "response": f"Reminder {display} ke liye set kar diya! '{label}' ⏰",
            "action": "SET_REMINDER",
            "payload": {
                "id": rid,
                "title": label,
                "trigger_at": trigger_ts,
                "trigger_datetime": trigger_dt,
                "type": t_type,
            },
            "persisted": persisted,
        }

    @staticmethod
    def list_upcoming() -> dict:
        """List upcoming reminders from the database."""
        reminders = reminder_db.get_upcoming(limit=10)
        if not reminders:
            return {
                "response": "Koi upcoming reminder nahi hai. ✅",
                "action": "SET_REMINDER",
                "payload": {"reminders": []},
            }

        items = []
        for r in reminders:
            dt = datetime.fromtimestamp(r["trigger_at"])
            items.append(f"• {r['title']} ({dt.strftime('%d %b %I:%M %p')})")

        return {
            "response": "Aapke upcoming reminders:\n" + "\n".join(items),
            "action": "SET_REMINDER",
            "payload": {"reminders": reminders},
        }

    @staticmethod
    def cancel(reminder_id: int) -> dict:
        """Cancel a specific reminder."""
        success = reminder_db.cancel_reminder(reminder_id)
        return {
            "response": f"Reminder #{reminder_id} cancel kar diya! ✅" if success
                       else f"Reminder #{reminder_id} nahi mila ya already fired ho gaya.",
            "action": "SET_REMINDER",
            "payload": {"cancelled": success, "id": reminder_id},
        }


# ── Background Scheduler ─────────────────────────────────────────

def _scheduler_loop():
    """Background thread: polls DB every N seconds, fires due reminders."""
    logger.info("AND9 reminder scheduler started (poll every %ds).", _POLL_INTERVAL)
    while not _scheduler_stop.is_set():
        try:
            pending = reminder_db.get_pending()
            for reminder in pending:
                _fire_reminder(reminder)
        except Exception as e:
            logger.error("Scheduler error: %s", e)
        _scheduler_stop.wait(_POLL_INTERVAL)
    logger.info("AND9 reminder scheduler stopped.")


def _fire_reminder(reminder: dict) -> None:
    """Fire a single reminder notification."""
    try:
        rid = reminder["id"]
        title = reminder["title"]
        logger.info("Firing reminder #%d: '%s'", rid, title)
        # Mark as fired first to prevent double-firing
        reminder_db.mark_fired(rid)
        # TODO: Send notification to Android client via WebSocket / push
        # For now, log it. The Android client polls or uses SSE.
        logger.info("REMINDER FIRED: #%d '%s'", rid, title)
    except Exception as e:
        logger.error("Failed to fire reminder #%d: %s", reminder.get("id"), e)


def start_scheduler() -> None:
    """Start the background reminder scheduler thread.

    Idempotent — safe to call multiple times.
    """
    global _scheduler_thread
    if _scheduler_thread and _scheduler_thread.is_alive():
        return
    _scheduler_stop.clear()
    _scheduler_thread = threading.Thread(
        target=_scheduler_loop,
        name="AND9-ReminderScheduler",
        daemon=True,
    )
    _scheduler_thread.start()
    logger.info("Reminder scheduler thread started.")


def stop_scheduler() -> None:
    """Signal the scheduler to stop."""
    _scheduler_stop.set()
