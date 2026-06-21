"""
AND9 — Timer Actions (Phase 10 of Refactor).

Sets Android countdown timers via AlarmClock.ACTION_SET_TIMER intent.
Maximum duration is 24 hours (configurable in core/config.py).

Supports:
    timer 5 minutes      → 300s timer
    timer 30 seconds     → 30s timer
    2 hour timer         → 7200s timer
"""
import logging
from app.and9.core.config import MAX_TIMER_SECONDS

logger = logging.getLogger(__name__)


def execute_set_timer(duration_seconds: int,
                      label: str = "AND9 Timer") -> dict:
    """Set a countdown timer.

    Args:
        duration_seconds: Timer duration in seconds (max 24h).
        label: Optional timer label.

    Returns:
        Dict with response, action, payload.
    """
    if not duration_seconds or duration_seconds <= 0:
        return {
            "response": "Kitne der ka timer set karna hai? Duration batao! ⏲️",
            "action": "SET_TIMER",
            "payload": {},
        }

    if duration_seconds > MAX_TIMER_SECONDS:
        return {
            "response": "Timer sirf 24 ghante ka set kar sakte hain. Koi aur time batao! ⏲️",
            "action": "SET_TIMER",
            "payload": {},
        }

    duration_str = _format_duration(duration_seconds)

    # Use standard Android AlarmClock.ACTION_SET_TIMER
    payload = {
        "action": "android.intent.action.SET_TIMER",
        "length": duration_seconds,
        "label": label,
    }

    return {
        "response": f"Timer {duration_str} ka set kar diya! ⏲️",
        "action": "SET_TIMER",
        "payload": payload,
    }


def _format_duration(seconds: int) -> str:
    """Format seconds into human-readable string."""
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    parts = []
    if hours > 0:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes > 0:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if secs > 0 or not parts:
        parts.append(f"{secs} second{'s' if secs != 1 else ''}")
    return " ".join(parts)
