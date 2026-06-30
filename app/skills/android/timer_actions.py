"""
AND9 — Timer Actions (Phase 9 Rebuild).

Sets Android countdown timers via AlarmClock.ACTION_SET_TIMER.
Uses the unified time_parser for all duration extraction.
Never searches Google. Never opens Chrome.

Supported commands:
    set timer / timer lagao
    5 second timer / 10 second timer / 30 second timer
    1 minute timer / 5 minute timer / 10 minute timer
    1 hour timer / 2 hour timer
"""
import logging
from typing import Optional

from app.utils.time_parser import parse_duration, format_duration
from app.core.and9_config import MAX_TIMER_SECONDS

logger = logging.getLogger(__name__)

# Android Intent action for timers
_ACTION_SET_TIMER = "android.intent.action.SET_TIMER"


def execute_set_timer(
    duration_seconds: Optional[int] = None,
    label: str = "AND9 Timer",
    query: Optional[str] = None,
) -> dict:
    """Set a countdown timer via Android AlarmClock.ACTION_SET_TIMER.

    Accepts either a pre-parsed duration or a raw query string.
    Never falls back to Chrome or Google search.

    Args:
        duration_seconds: Duration in seconds. Ignored if query is given.
        label:            Timer label.
        query:            Raw query to parse duration from (overrides duration_seconds).

    Returns:
        Dict with response, action, payload.

    Examples:
        >>> execute_set_timer(duration_seconds=300)
        {'response': '5 minutes ka timer set kar diya! ⏲️', ...}

        >>> execute_set_timer(query="5 minute timer")
        {'response': '5 minutes ka timer set kar diya! ⏲️', ...}
    """
    # ── Parse from query if provided ─────────────────────────────
    if query:
        duration_seconds = parse_duration(query)
        if duration_seconds is None:
            return {
                "response": "Timer ki duration samajh nahi aaya. "
                            "Jaise: '5 minute timer' ya '30 seconds'. ⏲️",
                "action": "SET_TIMER",
                "payload": {},
            }

    # ── Validate ─────────────────────────────────────────────────
    if not duration_seconds or duration_seconds <= 0:
        return {
            "response": "Timer ki duration batao — jaise '5 minute timer'. ⏲️",
            "action": "SET_TIMER",
            "payload": {},
        }

    if duration_seconds > MAX_TIMER_SECONDS:
        max_display = format_duration(MAX_TIMER_SECONDS)
        return {
            "response": f"Timer {max_display} se zyada nahi ho sakta. ⏲️",
            "action": "SET_TIMER",
            "payload": {},
        }

    display = format_duration(duration_seconds)

    return {
        "response": f"{display} ka timer set kar diya! ⏲️",
        "action": "SET_TIMER",
        "payload": {
            "action": _ACTION_SET_TIMER,
            "length": duration_seconds,
            "label": label,
            "skip_ui": False,
        },
    }
