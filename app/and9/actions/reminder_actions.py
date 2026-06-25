"""
AND9 — Reminder Actions (Phase 9 of Refactor).

Stores reminders with optional persistence via EventSystem.
Supports both relative (after 10 minutes) and absolute
(7 pm meeting) time formats.

The reminder is persisted to the EventSystem for cross-session
retention. Label cleanup strips time-related noise words.
"""
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional, Any

logger = logging.getLogger(__name__)

IST = ZoneInfo("Asia/Kolkata")


def execute_set_reminder(trigger_at: dict,
                         label: str = "AND9 Reminder",
                         events_sys: Optional[Any] = None) -> dict:
    """Set a reminder with optional EventSystem persistence.

    Args:
        trigger_at: Dict with time info:
            - type "absolute": {"type": "absolute", "hour": N, "minute": N}
            - type "relative": {"type": "relative", "seconds": N}
        label: Reminder title/label.
        events_sys: Optional EventSystem for persistent storage.

    Returns:
        Dict with response, action, payload.
    """
    if not trigger_at or "type" not in trigger_at:
        if label and label != "AND9 Reminder":
            return {
                "response": f"'{label}' — Kab yaad dilana hai? Time batao! ⏰",
                "action": "SET_REMINDER",
                "payload": {"label": label},
            }
        return {
            "response": "Kya aur kab yaad dilana hai? Jaise 'remind me after 10 minutes meeting' ⏰",
            "action": "SET_REMINDER",
            "payload": {},
        }

    now = datetime.now(IST)
    reminder_time = None

    if trigger_at["type"] == "absolute":
        hour = trigger_at.get("hour") or 0
        minute = trigger_at.get("minute") or 0
        reminder_time = now.replace(
            hour=hour,
            minute=minute,
            second=0, microsecond=0,
        )
        if reminder_time < now:
            reminder_time += timedelta(days=1)

    elif trigger_at["type"] == "relative":
        seconds = trigger_at.get("seconds")
        if not seconds:
            return {
                "response": "Reminder ka time samajh nahi aaya. Seconds missing. ⏰",
                "action": "SET_REMINDER",
                "payload": {},
            }
        reminder_time = now + timedelta(seconds=seconds)

    # Persist via EventSystem if available
    persisted = False
    if events_sys and reminder_time:
        try:
            events_sys.add_event(
                title=label,
                event_time=reminder_time.isoformat(),
                notes=f"Reminder: {label}",
            )
            persisted = True
        except Exception as e:
            logger.error("Failed to persist reminder: %s", e)

    # Also persist to the worker-polled SQLite DB for guaranteed firing
    if reminder_time:
        try:
            from app.reminders import storage as reminder_storage
            reminder_storage.add(title=label, trigger_time=reminder_time)
        except Exception as e:
            logger.error("Failed to persist reminder to worker storage: %s", e)

    if label and label != "AND9 Reminder":
        return {
            "response": f"Reminder set kar diya! '{label}' ke liye ⏰",
            "action": "SET_REMINDER",
            "payload": {
                "trigger_at": trigger_at,
                "label": label,
                "persisted": persisted,
            },
        }

    return {
        "response": "Reminder set kar diya! Par kya yaad dilana hai? ⏰",
        "action": "SET_REMINDER",
        "payload": {
            "trigger_at": trigger_at,
            "label": "",
        },
    }
