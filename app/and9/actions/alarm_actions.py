"""
AND9 — Alarm Actions (Phase 8 of Refactor).

Sets Android alarms via IntentExecutor or direct Android intent.
Never falls back to Chrome or web search for alarm commands.

Uses AlarmClock.ACTION_SET_ALARM intent which is the standard
Android API for setting alarms.
"""
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


def execute_set_alarm(hour: int, minute: int,
                      label: Optional[str] = None) -> dict:
    """Set an alarm at the specified time.

    Uses IntentExecutor.set_alarm() if available, otherwise
    returns a structured payload for the Android client.

    Args:
        hour: Hour in 24h format (0-23).
        minute: Minute (0-59).
        label: Optional alarm label.

    Returns:
        Dict with response, action, payload.
    """
    # Validate
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return {
            "response": "Time sahi nahi hai. Kripya valid time batao! ⏰",
            "action": "SET_ALARM",
            "payload": {},
        }

    display_hour = hour if hour <= 12 else hour - 12
    if display_hour == 0:
        display_hour = 12
    period = "AM" if hour < 12 else "PM"
    label = label or "AND9 Alarm"

    # Try using IntentExecutor
    try:
        from app.skills.intent_executor import IntentExecutor
        result = IntentExecutor.set_alarm(hour, minute, label)
        if result:
            return {
                "response": f"Alarm {display_hour}:{minute:02d} {period} ke liye set kar diya! ⏰",
                "action": "SET_ALARM",
                "payload": result,
            }
    except Exception as e:
        logger.debug("IntentExecutor.set_alarm failed: %s", e)

    # Fallback: return standard Android AlarmClock intent
    return {
        "response": f"Alarm {display_hour}:{minute:02d} {period} ke liye set kar diya! ⏰",
        "action": "SET_ALARM",
        "payload": {
            "action": "android.intent.action.SET_ALARM",
            "hour": hour,
            "minute": minute,
            "label": label,
        },
    }
