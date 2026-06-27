"""
AND9 — Entity Extractor (Phase 5).

Separates entity extraction from intent classification.

Router  → classifies intent only.
Extractor → extracts structured data only.

Entities extracted:
    contact_name   — for CALL / MESSAGE
    app_name       — for OPEN_APP
    youtube_query  — for YOUTUBE_SEARCH / YOUTUBE_PLAY
    alarm_time     — for SET_ALARM   (delegates to time_parser)
    timer_duration — for SET_TIMER   (delegates to time_parser)
    reminder_label — for SET_REMINDER
    search_query   — for SEARCH

All regex patterns are imported from command_dictionary.py.
No regex is defined here.
"""
import re
import logging
from functools import lru_cache
from typing import Optional

from backend.cognition.planner.command_dictionary import (
    CALL_CONTACT,
    CALL_NUMBER,
    IS_PHONE_NUMBER,
    OPEN_APP_GENERIC,
    YOUTUBE_SEARCH_PATTERNS,
    YOUTUBE_PLAY_PATTERNS,
    YOUTUBE_PLAY_TRIGGER,
    YOUTUBE_OPEN_ONLY,
    ACTION_NOISE_WORDS,
    TIME_NOISE_WORDS,
)
from backend.utils.time_parser import parse_time, parse_duration, parse_recurring

logger = logging.getLogger(__name__)


@lru_cache(maxsize=512)
def extract_entities(intent: str, query: str) -> dict:
    """Top-level dispatcher — extract entities based on intent type.

    Args:
        intent: Detected intent name (e.g., "call", "open_app", "alarm").
        query:  Normalized query string.

    Returns:
        Dict of extracted entities relevant to the intent.

    Example:
        >>> extract_entities("call", "call mummy")
        {'contact_name': 'mummy', 'number': None, 'action_type': 'contact'}
        >>> extract_entities("open_app", "youtube kholo")
        {'app_name': 'youtube'}
        >>> extract_entities("set_alarm", "alarm 7 am")
        {'hour': 7, 'minute': 0, 'type': 'absolute', ...}
    """
    q = query.lower().strip()

    dispatchers = {
        "call":        extract_call,
        "message":     extract_message,
        "send_sms":    extract_message,
        "open_app":    extract_app,
        "youtube":     extract_youtube,
        "youtube_search": extract_youtube,
        "youtube_play":   extract_youtube,
        "alarm":       extract_alarm,
        "set_alarm":   extract_alarm,
        "timer":       extract_timer,
        "set_timer":   extract_timer,
        "reminder":    extract_reminder,
        "set_reminder": extract_reminder,
        "search":      extract_search,
    }

    fn = dispatchers.get(intent)
    if fn:
        return fn(q)
    return {"query": q}


# ── CALL ──────────────────────────────────────────────────────────

def extract_call(query: str) -> dict:
    """Extract contact name or phone number from a call command.

    Returns:
        {
            "contact_name": str | None,
            "number":       str | None,
            "action_type":  "contact" | "dial",
            "lookup_required": bool,
        }
    """
    q = query.strip()

    # Check if it's a direct number call
    for pattern in CALL_NUMBER:
        m = pattern.search(q)
        if m:
            number = re.sub(r'[\s\-()\+]', '', m.group(1)).lstrip('+')
            if len(number) >= 7:
                return {
                    "contact_name": None,
                    "number": m.group(1).strip(),
                    "action_type": "dial",
                    "lookup_required": False,
                }

    # Check for contact name
    for pattern in CALL_CONTACT:
        m = pattern.search(q)
        if m:
            name = m.group(1).strip()
            # Safety: if it looks like a number, treat as dial
            if IS_PHONE_NUMBER.match(name):
                return {
                    "contact_name": None,
                    "number": name,
                    "action_type": "dial",
                    "lookup_required": False,
                }
            return {
                "contact_name": name,
                "number": None,
                "action_type": "contact",
                "lookup_required": True,
            }

    return {
        "contact_name": None,
        "number": None,
        "action_type": "unknown",
        "lookup_required": False,
    }


# ── MESSAGE ───────────────────────────────────────────────────────

def extract_message(query: str) -> dict:
    """Extract contact + message text from a message command."""
    q = query.strip()
    # Strip the trigger word
    cleaned = re.sub(r'^(?:message|msg|sms|text)\s+', '', q, flags=re.IGNORECASE)
    parts = cleaned.split(None, 1)
    contact = parts[0] if parts else ""
    text = parts[1] if len(parts) > 1 else ""

    if IS_PHONE_NUMBER.match(contact):
        return {
            "contact_name": None,
            "number": contact,
            "message": text,
            "action_type": "dial",
            "lookup_required": False,
        }
    return {
        "contact_name": contact,
        "number": None,
        "message": text,
        "action_type": "contact",
        "lookup_required": bool(contact),
    }


# ── OPEN APP ──────────────────────────────────────────────────────

def extract_app(query: str) -> dict:
    """Extract app name from an open/launch command.

    Returns:
        {"app_name": str}
    """
    q = query.strip()

    for pattern in OPEN_APP_GENERIC:
        m = pattern.search(q)
        if m:
            app = m.group(1).strip()
            app = _clean_app_name(app)
            if app:
                return {"app_name": app}

    # Fallback: strip action verbs and return remainder
    cleaned = _strip_action_noise(q)
    return {"app_name": cleaned or q}


def _clean_app_name(name: str) -> str:
    """Remove trailing action words from an app name."""
    noise = ["app", "application", "kholo", "open", "launch", "start",
             "chalao", "karo", "open karo"]
    for word in noise:
        name = re.sub(rf'\b{re.escape(word)}\b', '', name, flags=re.IGNORECASE)
    return name.strip()


# ── YOUTUBE ───────────────────────────────────────────────────────

def extract_youtube(query: str) -> dict:
    """Extract YouTube intent type and search query.

    Returns:
        {
            "action":  "search" | "play" | "open",
            "query":   str | None,
        }
    """
    q = query.strip()

    # Check open-only (no query)
    if YOUTUBE_OPEN_ONLY.match(q):
        return {"action": "open", "query": None}

    # Try search patterns first
    for pattern in YOUTUBE_SEARCH_PATTERNS:
        m = pattern.search(q)
        if m:
            raw_query = m.group(1).strip()
            return {"action": "search", "query": _clean_media_query(raw_query)}

    # Try play patterns
    for pattern in YOUTUBE_PLAY_PATTERNS:
        m = pattern.search(q)
        if m:
            raw_query = m.group(1).strip() if m.lastindex else q
            return {"action": "play", "query": _clean_media_query(raw_query)}

    # Has youtube keyword + play trigger
    if YOUTUBE_PLAY_TRIGGER.search(q):
        cleaned = _clean_media_query(q)
        return {"action": "play", "query": cleaned or None}

    # Default: search with full query
    return {"action": "search", "query": _clean_media_query(q)}


def _clean_media_query(q: str) -> str:
    """Strip action words from a media query to get the actual content."""
    noise = [
        "youtube", "pe", "par", "aur", "search", "karo", "play",
        "sunao", "bajao", "chalao", "laga", "do", "on",
        "song", "gaana", "gana", "music", "video", "kholo",
        "open", "and",
    ]
    result = q
    for word in noise:
        result = re.sub(rf'\b{re.escape(word)}\b', ' ', result, flags=re.IGNORECASE)
    return re.sub(r'\s+', ' ', result).strip()


# ── ALARM ─────────────────────────────────────────────────────────

def extract_alarm(query: str) -> dict:
    """Extract alarm time from query using the unified time parser.

    Returns:
        Time dict from parse_time(), with label added.
        {"type": ..., "hour": ..., "minute": ..., "label": str, ...}
    """
    q = query.strip()
    result = parse_time(q)

    # Extract optional label (text remaining after stripping time and noise)
    label = _extract_label(q)
    result["label"] = label or "AND9 Alarm"
    return result


# ── TIMER ─────────────────────────────────────────────────────────

def extract_timer(query: str) -> dict:
    """Extract timer duration from query.

    Returns:
        {
            "duration_seconds": int | None,
            "label": str,
            "display": str,
        }
    """
    from backend.utils.time_parser import format_duration
    q = query.strip()
    duration = parse_duration(q)

    return {
        "duration_seconds": duration,
        "label": "AND9 Timer",
        "display": format_duration(duration) if duration else "unknown",
    }


# ── REMINDER ─────────────────────────────────────────────────────

def extract_reminder(query: str) -> dict:
    """Extract reminder time and label from query.

    Returns:
        {
            "trigger_at": time dict from parse_time(),
            "label": str,
        }
    """
    q = query.strip()
    trigger_at = parse_time(q)
    label = _extract_label(q) or "AND9 Reminder"
    recurring = parse_recurring(q)
    return {
        "trigger_at": trigger_at,
        "label": label,
        "repeat_rule": recurring["rule"] if recurring else "",
        "repeat_days": recurring["days"] if recurring else None,
        "repeat_raw": recurring["raw"] if recurring else "",
    }


# ── SEARCH ────────────────────────────────────────────────────────

def extract_search(query: str) -> dict:
    """Extract the search query by stripping trigger words."""
    q = query.strip()
    cleaned = re.sub(
        r'\b(search|google|find|look\s+up|ke\s+baare\s+mein\s+batao|'
        r'dhundo|dhundho|khojo|talaash\s+karo)\b',
        '', q, flags=re.IGNORECASE
    )
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return {"query": cleaned or q}


# ── Helpers ───────────────────────────────────────────────────────

def _strip_action_noise(q: str) -> str:
    """Strip known action verbs from a query string."""
    result = q
    for word in sorted(ACTION_NOISE_WORDS, key=len, reverse=True):
        result = re.sub(rf'\b{re.escape(word)}\b', ' ', result, flags=re.IGNORECASE)
    return re.sub(r'\s+', ' ', result).strip()


def _extract_label(query: str) -> Optional[str]:
    """Extract a clean label by stripping action keywords, time expressions, and noise.

    Used for alarm labels and reminder titles.
    """
    q = query.lower().strip()

    # Strip action keywords
    action_kw = [
        "set a reminder", "set an reminder", "set a alarm", "set an alarm", "set a timer", "set an timer",
        "set alarm", "set reminder", "set timer",
        "alarm lagao", "alarm laga do", "alarm set karo", "alarm set",
        "reminder lagao", "timer lagao",
        "alarm", "reminder", "timer",
        "remind me to", "remind me about", "remind me for", "remind me",
        "yaad dilana", "yaad dila",
    ]
    for kw in sorted(action_kw, key=len, reverse=True):
        q = q.replace(kw, " ")

    # Strip time expressions
    q = re.sub(
        r'(?:after|in|baad|me|ke\s*baad|for|at|ko)\s+'
        r'\d+(?:\.\d+)?\s*(?:second|sec|secs|seconds|s|minute|min|mins|minutes|m|hour|hr|hrs|hours|h|ghanta|ghante)s?',
        '', q, flags=re.IGNORECASE
    )
    q = re.sub(
        r'\d+(?:\.\d+)?\s*(?:second|sec|secs|seconds|s|minute|min|mins|minutes|m|hour|hr|hrs|hours|h|ghanta|ghante)s?'
        r'\s*(?:baad|ke\s*baad|me)?',
        '', q, flags=re.IGNORECASE
    )
    q = re.sub(r'\d{1,2}(?::\d{2})?\s*(?:am|pm|baje)?', '', q, flags=re.IGNORECASE)

    # Strip time noise words
    for w in TIME_NOISE_WORDS:
        q = re.sub(rf'\b{re.escape(w)}\b', ' ', q, flags=re.IGNORECASE)

    q = re.sub(r'\s+', ' ', q).strip()
    return q if q and len(q) > 1 else None
