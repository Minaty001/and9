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

    Recurring (Phase B):
        har somvar / every Monday → weekly[day]
        har roz / every day → daily
        weekdays / kaam ke din → weekdays
        har mahina / every month → monthly
        har saal / every year → yearly

    Calendar-relative (Phase B):
        next Monday → next weekday occurrence + time
        this evening / aaj shaam → today at 18:00
        tonight / aaj raat → today at 21:00
        tomorrow morning / kal subah → tomorrow at 9:00
        parson / day after tomorrow → day_offset=2
        next week → day_offset=7

Returns:
    {
        "type":     "relative" | "absolute" | "recurring" | "unknown",
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
from functools import lru_cache
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Optional

logger = logging.getLogger(__name__)

# ── IST timezone ─────────────────────────────────────────────────────
IST = ZoneInfo("Asia/Kolkata")


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

    # ── 2. Calendar-relative time ────────────────────────────────
    result = parse_calendar_time(q)
    if result:
        return result

    # ── 3. Absolute time ─────────────────────────────────────────
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


@lru_cache(maxsize=256)
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
            now = datetime.now(IST)
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

    now = datetime.now(IST)
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


# ── Recurring Rule Parsing (Phase B) ─────────────────────────────────


# Hinglish/English day-of-week names → weekday index (0=Monday … 6=Sunday)
_DAY_NAMES: dict[str, int] = {
    # English
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
    # Hinglish
    "somvar": 0, "mangalvar": 1, "budhvar": 2,
    "guruvar": 3, "veervar": 3,
    "shukravar": 4, "shanivar": 5, "ravivar": 6,
    "som": 0, "mangal": 1, "budh": 2,
    "guru": 3, "veer": 3,
    "shukra": 4, "shani": 5, "ravi": 6,
}

_RECURRING_PATTERNS: list[tuple[re.Pattern, str, Optional[int]]] = [
    # daily — "har roz", "har din", "daily", "every day"
    # "din" alone is too short — require "har din" or "har roz"
    (re.compile(r'\b(?:har\s+(?:roz|din)|daily|every\s*day)\b', re.IGNORECASE), "daily", None),
    # weekdays / working days
    (re.compile(r'\b(?:weekdays?|working\s*days?|kaam\s*ke\s*din)\b', re.IGNORECASE), "weekdays", None),
    # weekly / every week / har hafte
    (re.compile(r'\b(?:weekly|every\s*week|har\s*hafte)\b', re.IGNORECASE), "weekly", None),
    # monthly / every month / har mahina
    (re.compile(r'\b(?:monthly|every\s*month|har\s*mahina)\b', re.IGNORECASE), "monthly", None),
    # yearly / every year / har saal
    (re.compile(r'\b(?:yearly|every\s*years?|har\s*saal)\b', re.IGNORECASE), "yearly", None),
    # every <day-of-week> / har <day>
    (re.compile(
        r'\b(?:every|har)\s+(' + '|'.join(re.escape(d) for d in _DAY_NAMES) + r')\b',
        re.IGNORECASE
    ), "weekly", None),  # will fill day index after match
]


def parse_recurring(query: str) -> Optional[dict]:
    """Extract a recurring rule from a natural language query.

    Args:
        query: Normalized query string.

    Returns:
        {"rule": str, "days": Optional[list[int]], "raw": str} or None.

    Result rule values:
        - "daily"     → fires every day
        - "weekdays"  → fires Monday–Friday
        - "weekly"    → fires every N weeks (days list specifies weekdays)
        - "monthly"   → fires on the same day every month
        - "yearly"    → fires on the same date every year

    Examples:
        >>> parse_recurring("har somvar reminder")
        {"rule": "weekly", "days": [0], "raw": "har somvar"}
        >>> parse_recurring("daily alarm")
        {"rule": "daily", "days": None, "raw": "daily"}
    """
    q = query.lower().strip()
    for pattern, rule, _ in _RECURRING_PATTERNS:
        m = pattern.search(q)
        if m:
            days = None
            # If this is a "every <day>" pattern, extract the day index
            if rule == "weekly" and len(m.groups()) >= 1:
                day_name = m.group(1).lower()
                idx = _DAY_NAMES.get(day_name)
                if idx is not None:
                    days = [idx]
            return {
                "rule": rule,
                "days": days,
                "raw": m.group(0),
            }
    return None


# ── Calendar-Relative Parsing (Phase B) ──────────────────────────────


_CALENDAR_TODAY_PART = re.compile(
    r'\b(?:aaj\s*)?(?:subah|morning|dopehar|afternoon|shaam|evening|raat|night|tonight)\b',
    re.IGNORECASE
)
_CALENDAR_TOMORROW_PART = re.compile(
    r'\b(?:kal|tomorrow)\s+(?:subah|morning|dopehar|afternoon|shaam|evening|raat|night)\b',
    re.IGNORECASE
)
_CALENDAR_NEXT_DAY = re.compile(
    r'\b(?:agle|next)\s+(' + '|'.join(re.escape(d) for d in _DAY_NAMES) + r')\b',
    re.IGNORECASE
)
_CALENDAR_PASSON = re.compile(r'\b(?:parson|day\s+after\s+tomorrow|next\s+(?:to\s+)?2\s*days)\b', re.IGNORECASE)
_CALENDAR_NEXT_WEEK = re.compile(r'\bnext\s+week\b', re.IGNORECASE)


def parse_calendar_time(query: str) -> Optional[dict]:
    """Parse a calendar-relative expression into a concrete datetime.

    Handles constructs like "next Monday", "this evening", "kal subah",
    "parson", "next week".

    Args:
        query: Normalized query string.

    Returns:
        Time dict (same shape as parse_time return) or None if no match.

    Examples:
        >>> parse_calendar_time("next Monday 7 am")
        # → absolute time for next Monday 7:00 AM
        >>> parse_calendar_time("aaj raat")
        # → today at 21:00
    """
    q = query.lower().strip()
    now = datetime.now(IST)
    result = None

    # 1. "parson" / "day after tomorrow" → +2 days
    if _CALENDAR_PASSON.search(q):
        result = _apply_time_to_base(q, now + timedelta(days=2))
        if result:
            result["day_offset"] = 2
            return result

    # 2. "next week" → +7 days
    if _CALENDAR_NEXT_WEEK.search(q):
        result = _apply_time_to_base(q, now + timedelta(days=7))
        if result:
            result["day_offset"] = 7
            return result

    # 3. "next <day>", "agle <day>" → next occurrence of that weekday
    m = _CALENDAR_NEXT_DAY.search(q)
    if m:
        day_name = m.group(1).lower()
        target_weekday = _DAY_NAMES.get(day_name)
        if target_weekday is not None:
            days_ahead = target_weekday - now.weekday()
            if days_ahead <= 0:  # target day is today or already passed this week
                days_ahead += 7
            base = now + timedelta(days=days_ahead)
            result = _apply_time_to_base(q, base)
            if result:
                result["day_offset"] = days_ahead
                return result

    # 4. "kal <part>" / "tomorrow <part>" → tomorrow + semantic time
    m = _CALENDAR_TOMORROW_PART.search(q)
    if m:
        return _resolve_calendar_part(q, _find_part_of_day(m.group(0)), day_offset=1)

    # 5. "aaj <part>" / "this <part>" / standalone part-of-day → today
    if _CALENDAR_TODAY_PART.search(q):
        return _resolve_calendar_part(q, _find_part_of_day(q), day_offset=0)

    return None


# ── Part-of-day mapping ──────────────────────────────────────────────

_SEMANTIC_HOURS: dict[str, tuple[int, int]] = {
    "subah": (9, 0),
    "morning": (9, 0),
    "dopehar": (14, 0),
    "afternoon": (14, 0),
    "shaam": (18, 0),
    "evening": (18, 0),
    "raat": (21, 0),
    "night": (21, 0),
    "tonight": (21, 0),
}


def _find_part_of_day(text: str) -> tuple[int, int]:
    """Extract the (hour, minute) tuple from a part-of-day keyword in text."""
    for kw, (h, m) in _SEMANTIC_HOURS.items():
        if kw in text:
            return (h, m)
    return (18, 0)  # default to evening


def _resolve_calendar_part(query: str,
                           hour_minute: tuple[int, int],
                           day_offset: int = 0) -> Optional[dict]:
    """Build a time dict from a semantic part-of-day with offset."""
    hour, minute = hour_minute
    now = datetime.now(IST)
    base = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    trigger = base + timedelta(days=day_offset)
    if trigger <= now:
        trigger += timedelta(days=1)

    # Extract matched raw text
    raw_match = query
    return {
        "type": "absolute",
        "seconds": None,
        "hour": hour,
        "minute": minute,
        "timestamp": trigger.timestamp(),
        "datetime": trigger.isoformat(),
        "day_offset": day_offset,
        "raw": raw_match,
    }


def _apply_time_to_base(query: str, base: datetime) -> Optional[dict]:
    """If query also contains a clock time, use it; otherwise use now's time.

    This helper checks whether the query has an absolute clock time
    (7 am, 7:30 pm, 19:30, subah, raat, etc.) and combines it with
    the calendar base date.
    """
    # Try absolute clock time first
    abs_result = _parse_absolute(query)
    if abs_result:
        # Override date part with the calendar base
        base_dt = base.replace(
            hour=abs_result["hour"], minute=abs_result["minute"],
            second=0, microsecond=0,
        )
        now = datetime.now(IST)
        if base_dt <= now:
            base_dt += timedelta(days=1)
        abs_result["timestamp"] = base_dt.timestamp()
        abs_result["datetime"] = base_dt.isoformat()
        abs_result["day_offset"] = (base_dt.date() - now.date()).days
        abs_result["raw"] = abs_result.get("raw", query)
        return abs_result

    # Try part-of-day semantic
    part = _find_part_of_day(query)
    hour, minute = part
    base_dt = base.replace(hour=hour, minute=minute, second=0, microsecond=0)
    now = datetime.now(IST)
    if base_dt <= now:
        base_dt += timedelta(days=1)
    return {
        "type": "absolute",
        "seconds": None,
        "hour": hour,
        "minute": minute,
        "timestamp": base_dt.timestamp(),
        "datetime": base_dt.isoformat(),
        "day_offset": (base_dt.date() - now.date()).days,
        "raw": query,
    }
