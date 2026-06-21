"""
AND9 — Unified Time Parser (Phase 6).

Single source of truth for all time/duration parsing.
Used by alarm, timer, reminder, and any other time-aware intent.

Supports:
    Relative:
        after 5 sec / after 10 sec / after 1 minute / after 5 minutes
        after 1 hour / after 2 hours
        5 second baad / 10 minute ke baad / 1 ghante baad

    Absolute:
        7 am / 7 pm / 7:30 am / 19:30
        7 baje / 7:30 baje
        tomorrow 7 am / kal subah 7 baje
        today 8 pm / aaj raat 8 baje

Returns:
    {
        "type":     "relative" | "absolute" | "unknown",
        "seconds":  int | None,         # for relative only
        "hour":     int | None,          # 24h, for absolute
        "minute":   int | None,          # for absolute
        "timestamp": float | None,       # epoch seconds
        "datetime": str | None,          # ISO 8601
        "day_offset": int,               # 0=today, 1=tomorrow
        "raw":      str,                 # original matched text
    }
"""
import re
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


# ── Unit multipliers (seconds) ─────────────────────────────────────
_UNIT_SECONDS = {
    "second": 1, "sec": 1, "s": 1, "secs": 1, "seconds": 1,
    "minute": 60, "min": 60, "m": 60, "mins": 60, "minutes": 60,
    "hour": 3600, "hr": 3600, "h": 3600, "hrs": 3600, "hours": 3600,
    "ghanta": 3600, "ghante": 3600,
}

# ── Relative time patterns ─────────────────────────────────────────
_RELATIVE_PATTERNS = [
    # "after 5 seconds" / "in 10 minutes" / "ke baad 2 hours"
    re.compile(
        r'(?:after|in|baad|me|ke\s*baad)\s+(\d+(?:\.\d+)?)\s*'
        r'(second|sec|secs|seconds|minute|min|mins|minutes|hour|hr|hrs|hours|ghanta|ghante)s?',
        re.IGNORECASE
    ),
    # "5 second baad" / "10 minute ke baad" / "1 ghante baad"
    re.compile(
        r'(\d+(?:\.\d+)?)\s*'
        r'(second|sec|secs|seconds|minute|min|mins|minutes|hour|hr|hrs|hours|ghanta|ghante)s?'
        r'\s+(?:baad|ke\s*baad|me)',
        re.IGNORECASE
    ),
    # "5 sec" / "10 min" / "2 hr" (bare number+unit with no preposition)
    re.compile(
        r'^(\d+(?:\.\d+)?)\s*(second|sec|secs|seconds|minute|min|mins|minutes|hour|hr|hrs|hours|ghanta|ghante)s?$',
        re.IGNORECASE
    ),
]

# ── Absolute time patterns ─────────────────────────────────────────
_ABS_12H = re.compile(
    r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)',
    re.IGNORECASE
)
_ABS_24H = re.compile(
    r'\b(\d{1,2}):(\d{2})\b'
)
_ABS_BAJE = re.compile(
    r'(\d{1,2})(?::(\d{2}))?\s*baje',
    re.IGNORECASE
)

# ── Day-offset keywords ────────────────────────────────────────────
_TOMORROW_KW = re.compile(r'\b(kal|tomorrow|agle\s+din)\b', re.IGNORECASE)
_TODAY_KW    = re.compile(r'\b(aaj|today|tonight)\b', re.IGNORECASE)

# ── Semantic time keywords ─────────────────────────────────────────
_MORNING_KW = re.compile(r'\b(subah|morning)\b', re.IGNORECASE)
_AFTERNOON_KW = re.compile(r'\b(dopehar|afternoon)\b', re.IGNORECASE)
_EVENING_KW = re.compile(r'\b(shaam|evening)\b', re.IGNORECASE)
_NIGHT_KW = re.compile(r'\b(raat|night|tonight)\b', re.IGNORECASE)


def parse_time(query: str) -> dict:
    """Parse a time expression from a natural language query.

    Tries relative first, then absolute.

    Args:
        query: Normalized query string containing a time expression.

    Returns:
        Time dict. See module docstring for structure.
        Returns {"type": "unknown", ...} if nothing matched.

    Examples:
        >>> parse_time("set alarm after 5 minutes")
        {'type': 'relative', 'seconds': 300, ...}
        >>> parse_time("alarm 7 am")
        {'type': 'absolute', 'hour': 7, 'minute': 0, ...}
        >>> parse_time("alarm tomorrow 7 am")
        {'type': 'absolute', 'hour': 7, 'minute': 0, 'day_offset': 1, ...}
    """
    q = query.lower().strip()

    # ── 1. Relative time ──────────────────────────────────────────
    result = _parse_relative(q)
    if result:
        return result

    # ── 2. Absolute time ─────────────────────────────────────────
    result = _parse_absolute(q)
    if result:
        return result

    return {
        "type": "unknown",
        "seconds": None,
        "hour": None,
        "minute": None,
        "timestamp": None,
        "datetime": None,
        "day_offset": 0,
        "raw": q,
    }


def parse_duration(query: str) -> Optional[int]:
    """Extract total duration in seconds from a query.

    Handles compound durations like "1 hour 30 minutes".

    Args:
        query: Any string that might contain a time duration.

    Returns:
        Total seconds as int, or None if no duration found.

    Examples:
        >>> parse_duration("5 minute timer")
        300
        >>> parse_duration("1 hour 30 minutes")
        5400
        >>> parse_duration("set timer for 45 seconds")
        45
    """
    q = query.lower().strip()
    total = 0
    found = False

    # Try compound: hours + minutes + seconds
    for unit_group, unit_mult in [
        (r'(\d+(?:\.\d+)?)\s*(?:hour|hr)s?', 3600),
        (r'(\d+(?:\.\d+)?)\s*(?:minute|min)s?', 60),
        (r'(\d+(?:\.\d+)?)\s*(?:second|sec)s?', 1),
        (r'(\d+(?:\.\d+)?)\s*(?:ghanta|ghante)s?', 3600),
    ]:
        m = re.search(unit_group, q, re.IGNORECASE)
        if m:
            total += float(m.group(1)) * unit_mult
            found = True

    return int(total) if found else None


def _parse_relative(q: str) -> Optional[dict]:
    """Try to extract a relative (offset) time."""
    for pattern in _RELATIVE_PATTERNS:
        m = pattern.search(q)
        if m:
            num = float(m.group(1))
            unit = m.group(2).lower()
            multiplier = _UNIT_SECONDS.get(unit, 1)
            total_seconds = int(num * multiplier)
            now = datetime.now()
            trigger = now + timedelta(seconds=total_seconds)
            return {
                "type": "relative",
                "seconds": total_seconds,
                "hour": None,
                "minute": None,
                "timestamp": trigger.timestamp(),
                "datetime": trigger.isoformat(),
                "day_offset": 0,
                "raw": m.group(0),
            }
    return None


def _parse_absolute(q: str) -> Optional[dict]:
    """Try to extract an absolute clock time."""
    hour = minute = None
    matched_raw = ""

    # Try 12h: "7 am", "7:30 pm"
    m = _ABS_12H.search(q)
    if m:
        hour = int(m.group(1))
        minute = int(m.group(2)) if m.group(2) else 0
        meridiem = m.group(3).lower()
        if meridiem == "pm" and hour < 12:
            hour += 12
        if meridiem == "am" and hour == 12:
            hour = 0
        matched_raw = m.group(0)

    # Try "baje": "7 baje", "7:30 baje" (treat as AM)
    if hour is None:
        m = _ABS_BAJE.search(q)
        if m:
            hour = int(m.group(1))
            minute = int(m.group(2)) if m.group(2) else 0
            # "baje" without AM/PM → assume AM for morning
            matched_raw = m.group(0)

    # Try 24h: "19:30"
    if hour is None:
        m = _ABS_24H.search(q)
        if m:
            hour = int(m.group(1))
            minute = int(m.group(2))
            matched_raw = m.group(0)

    # Priority 5: Try Semantic time ("morning", "evening", "tonight", "kal raat")
    if hour is None:
        if _MORNING_KW.search(q):
            hour, minute = 9, 0
            matched_raw = "morning"
        elif _AFTERNOON_KW.search(q):
            hour, minute = 14, 0
            matched_raw = "afternoon"
        elif _EVENING_KW.search(q):
            hour, minute = 18, 0
            matched_raw = "evening"
        elif _NIGHT_KW.search(q):
            hour, minute = 21, 0
            matched_raw = "night"

    if hour is None or not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None

    # Determine day offset
    day_offset = 0
    if _TOMORROW_KW.search(q):
        day_offset = 1

    now = datetime.now()
    trigger = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    trigger += timedelta(days=day_offset)

    # If absolute time is in the past (and not tomorrow), push to next day
    if trigger <= now and day_offset == 0:
        trigger += timedelta(days=1)

    return {
        "type": "absolute",
        "seconds": None,
        "hour": hour,
        "minute": minute,
        "timestamp": trigger.timestamp(),
        "datetime": trigger.isoformat(),
        "day_offset": day_offset,
        "raw": matched_raw,
    }


def format_duration(seconds: int) -> str:
    """Format a duration in seconds to human-readable string.

    Examples:
        >>> format_duration(90)
        '1 minute 30 seconds'
        >>> format_duration(3661)
        '1 hour 1 minute 1 second'
    """
    hours, remainder = divmod(int(seconds), 3600)
    minutes, secs = divmod(remainder, 60)
    parts = []
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if secs or not parts:
        parts.append(f"{secs} second{'s' if secs != 1 else ''}")
    return " ".join(parts)


def format_time(hour: int, minute: int) -> str:
    """Format a 24h time to 12h display string.

    Examples:
        >>> format_time(7, 0)
        '7:00 AM'
        >>> format_time(19, 30)
        '7:30 PM'
    """
    period = "AM" if hour < 12 else "PM"
    display_hour = hour % 12 or 12
    return f"{display_hour}:{minute:02d} {period}"
