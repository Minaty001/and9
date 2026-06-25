"""
AND9 — Time Actions (Phase 9).

Provides handle_get_time() which returns the current IST time
in 12-hour Hinglish format. Used by the generic TIME intent.

No Android intent is needed — this is purely an informational response.
"""
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

IST = ZoneInfo("Asia/Kolkata")


def handle_get_time() -> dict:
    """Return the current IST time as a natural-language response.

    Returns:
        Dict with response text (Hinglish 12-hour format),
        action type, and empty payload.

    Examples:
        >>> result = handle_get_time()
        >>> result["response"]
        'Abhi time 7:30:15 PM hai (IST)'
    """
    now = datetime.now(IST)
    hour_12 = now.hour % 12 or 12
    period = "AM" if now.hour < 12 else "PM"
    time_str = f"{hour_12}:{now.minute:02d}:{now.second:02d} {period}"

    return {
        "response": f"Abhi time {time_str} hai (IST)",
        "action": "GET_TIME",
        "payload": {},
        "metadata": {
            "hour": now.hour,
            "minute": now.minute,
            "second": now.second,
            "timezone": "Asia/Kolkata",
            "offset": "+05:30",
        },
    }
