"""
AND9 — Alarm Actions (Phase 7 Rebuild).

Sets Android alarms using AlarmClock.ACTION_SET_ALARM.
No Chrome fallback. No web search fallback.

Supported commands:
    set alarm / alarm lagao / alarm laga do
    set alarm for 7 am / set alarm for 7 pm
    alarm 7 baje / kal subah 7 baje alarm lagao
    set alarm after 5 seconds / after 10 minutes / after 2 hours
    alarm tomorrow 7 am / alarm today 8 pm
"""
import logging
from typing import Optional

from app.and9.utils.time_parser import parse_time, format_time

logger = logging.getLogger(__name__)

# Android Intent action for alarms
_ACTION_SET_ALARM = "android.intent.action.SET_ALARM"
_ALARM_PACKAGE = "com.android.deskclock"


def execute_set_alarm(
    hour: Optional[int] = None,
    minute: Optional[int] = None,
    label: Optional[str] = None,
    query: Optional[str] = None,
) -> dict:
    """Set an alarm via Android AlarmClock.ACTION_SET_ALARM intent.

    Accepts either pre-parsed hour/minute or a raw query string.
    Never falls back to Chrome or Google search.

    Args:
        hour:   Hour in 24h format (0-23). Ignored if query is given.
        minute: Minute (0-59). Ignored if query is given.
        label:  Optional alarm label.
        query:  Raw query string to parse time from (overrides hour/minute).

    Returns:
        Dict with response, action, payload.

    Examples:
        >>> execute_set_alarm(hour=7, minute=0)
        {'response': 'Alarm 7:00 AM ke liye set kar diya! ⏰', 'action': 'SET_ALARM', ...}

        >>> execute_set_alarm(query="alarm after 10 minutes")
        {'response': 'Alarm 10 minutes baad lagega! ⏰', 'action': 'SET_ALARM', ...}
    """
    label = label or "AND9 Alarm"
    day_offset = 0  # 0=today, 1=tomorrow

    # ── Parse from query if provided ──────────────────────────────
    if query:
        parsed = parse_time(query)

        if parsed["type"] == "relative":
            seconds = parsed["seconds"]
            from app.and9.utils.time_parser import format_duration
            display = format_duration(seconds)
            return {
                "response": f"Alarm {display} baad lagega! ⏰",
                "action": "SET_ALARM",
                "payload": {
                    "action": _ACTION_SET_ALARM,
                    "type": "relative",
                    "offset_seconds": seconds,
                    "label": label,
                    "skip_ui": True,
                },
            }

        if parsed["type"] == "absolute":
            hour = parsed["hour"]
            minute = parsed["minute"]
            day_offset = parsed.get("day_offset", 0)
            # Fall through to absolute handling below

        else:
            return {
                "response": "Alarm ka time samajh nahi aaya. "
                            "Kripya batao — jaise '7 AM' ya 'after 10 minutes'. ⏰",
                "action": "SET_ALARM",
                "payload": {},
            }

    # ── Absolute alarm ────────────────────────────────────────────
    if hour is None or minute is None:
        return {
            "response": "Alarm ka time batao — jaise '7 AM' ya 'after 10 minutes'. ⏰",
            "action": "SET_ALARM",
            "payload": {},
        }

    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return {
            "response": "Time sahi nahi hai. Valid time batao (0-23 ghante, 0-59 minute). ⏰",
            "action": "SET_ALARM",
            "payload": {},
        }

    display = format_time(hour, minute)
    day_label = " (kal)" if day_offset else ""

    return {
        "response": f"Alarm {display}{day_label} ke liye set kar diya! ⏰",
        "action": "SET_ALARM",
        "payload": {
            "action": _ACTION_SET_ALARM,
            "type": "absolute",
            "hour": hour,
            "minute": minute,
            "day_offset": day_offset,
            "label": label,
            "skip_ui": False,
        },
    }
