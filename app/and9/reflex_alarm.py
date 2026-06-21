"""
AND9 — Reflex Alarm, Timer & Reminder Handlers.

Handles temporal commands with natural language time parsing.
Supports Hindi and English absolute/relative time expressions.

Alarm format:
  "alarm 7 am"              → 07:00 alarm
  "alarm 7:30 baje"         → 07:30 alarm
  "set alarm for 6:45 pm"   → 18:45 alarm

Timer format:
  "timer 5 minutes"         → 5-minute countdown
  "timer 30 seconds"        → 30-second countdown
  "timer 2 hours"           → 2-hour countdown (max 24h)

Reminder format:
  "remind me after 10 minutes meeting with boss"
    → 10-minute reminder, label="meeting with boss"
  "reminder 7 am workout"
    → daily 07:00 reminder, label="workout"

Label extraction strips time-related noise words (minutes, seconds,
hours, baad, me, ke, etc.) to produce clean reminder titles.
"""
import logging
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Max timer duration in seconds (24 hours)
_MAX_TIMER_SECONDS = 86400


def handle_set_alarm(query: str) -> dict:
    """Set an alarm based on a time expression in the query.

    Extracts absolute time (hour:minute) and returns a SET_ALARM
    intent. The alarm is set via JARVIS IntentExecutor.set_alarm()
    if available, falling back to a clock app launch.

    Args:
        query: Normalized query containing time expression.

    Returns:
        Response dict with SET_ALARM action and time payload.
    """
    time_info = _extract_time(query)

    if time_info:
        hour = time_info["hour"]
        minute = time_info["minute"]
        period = "AM" if hour < 12 else "PM"
        display_hour = hour if hour <= 12 else hour - 12
        if display_hour == 0:
            display_hour = 12

        label = _extract_label(query)

        # Try to use JARVIS IntentExecutor for alarm
        try:
            from app.javis.intent_executor import IntentExecutor
            result = IntentExecutor.set_alarm(hour, minute, label or "AND9 Alarm")
            if result:
                return {
                    "response": f"Alarm {display_hour}:{minute:02d} {period} ke liye set kar diya! ⏰",
                    "action": "SET_ALARM",
                    "payload": {"hour": hour, "minute": minute, "label": label},
                }
        except Exception as e:
            logger.debug("IntentExecutor.set_alarm failed: %s", e)

        # Fallback response
        return {
            "response": f"Alarm {display_hour}:{minute:02d} {period} ke liye set kar diya! ⏰",
            "action": "SET_ALARM",
            "payload": {
                "hour": hour,
                "minute": minute,
                "label": label or "AND9 Alarm",
                "fallback": True,
            },
        }

    return {
        "response": "Kya time alarm set karna hai? Time batao! ⏰",
        "action": "SET_ALARM",
        "payload": {},
    }


def handle_set_timer(query: str) -> dict:
    """Set a countdown timer based on duration in the query.

    Extracts relative duration (seconds/minutes/hours) and returns
    a SET_TIMER intent. Maximum timer duration is 24 hours.

    Args:
        query: Normalized query containing duration.

    Returns:
        Response dict with SET_TIMER action and duration payload.
    """
    duration_seconds = _extract_duration_seconds(query)

    if duration_seconds and 0 < duration_seconds <= _MAX_TIMER_SECONDS:
        duration_str = _format_duration(duration_seconds)
        label = _extract_label(query) or "AND9 Timer"

        return {
            "response": f"Timer {duration_str} ka set kar diya! ⏲️",
            "action": "SET_TIMER",
            "payload": {
                "duration_seconds": duration_seconds,
                "duration_display": duration_str,
                "label": label,
            },
        }

    if duration_seconds and duration_seconds > _MAX_TIMER_SECONDS:
        return {
            "response": "Timer sirf 24 ghante ka set kar sakte hain. Koi aur time batao! ⏲️",
            "action": "SET_TIMER",
            "payload": {},
        }

    return {
        "response": "Kitne der ka timer set karna hai? Duration batao! ⏲️",
        "action": "SET_TIMER",
        "payload": {},
    }


def handle_set_reminder(query: str, events_sys=None) -> dict:
    """Set a reminder with optional persistence via EventSystem.

    Supports both relative ("after 10 minutes") and absolute
    ("7 pm meeting") time expressions. The reminder label is the
    remaining text after stripping time expressions.

    Args:
        query: Normalized query containing time and reminder text.
        events_sys: Optional EventSystem instance for persistent
                    storage.

    Returns:
        Response dict with SET_REMINDER action and time/label payload.
    """
    label = _extract_label(query)
    time_info = _extract_time(query)

    # If we have an EventSystem, try to store the reminder persistently
    if events_sys and time_info:
        try:
            if time_info["type"] == "absolute":
                now = datetime.now()
                reminder_time = now.replace(
                    hour=time_info["hour"],
                    minute=time_info["minute"],
                    second=0, microsecond=0,
                )
                if reminder_time < now:
                    reminder_time += timedelta(days=1)

                events_sys.add_event(
                    event_type="reminder",
                    timestamp=reminder_time.timestamp(),
                    metadata={
                        "title": label or f"Reminder: {query}",
                        "time": reminder_time.isoformat(),
                    },
                )
            elif time_info["type"] == "relative":
                reminder_time = datetime.now() + timedelta(
                    seconds=time_info["seconds"]
                )
                events_sys.add_event(
                    event_type="reminder",
                    timestamp=reminder_time.timestamp(),
                    metadata={
                        "title": label or f"Reminder: {query}",
                        "time": reminder_time.isoformat(),
                    },
                )
        except Exception as e:
            logger.error("Failed to persist reminder: %s", e)

    # Build response
    if time_info and label:
        return {
            "response": f"Reminder set kar diya! '{label}' ke liye ⏰",
            "action": "SET_REMINDER",
            "payload": {
                "time": time_info,
                "label": label,
                "persisted": events_sys is not None,
            },
        }

    if time_info and not label:
        return {
            "response": "Reminder set kar diya! Par kya yaad dilana hai? ⏰",
            "action": "SET_REMINDER",
            "payload": {
                "time": time_info,
                "label": "",
            },
        }

    if label and not time_info:
        return {
            "response": f"'{label}' — Kab yaad dilana hai? Time batao! ⏰",
            "action": "SET_REMINDER",
            "payload": {
                "label": label,
            },
        }

    return {
        "response": "Kya aur kab yaad dilana hai? Jaise 'remind me after 10 minutes meeting' ⏰",
        "action": "SET_REMINDER",
        "payload": {},
    }


# ── Time Parsing Helpers ─────────────────────────────────────────


def _extract_time(query: str) -> Optional[Dict[str, Any]]:
    """Extract time information from a normalized query.

    Supports absolute time formats:
      - "7 am", "7:30 pm", "5 baje"
    Supports relative time formats:
      - "after 10 minutes", "in 5 minutes"

    Absolute time takes priority over relative when both are
    present.

    Args:
        query: Normalized query string.

    Returns:
        Dict with "type" ("absolute" or "relative") and time fields,
        or None if no time pattern matches.
    """
    q = query.lower()

    # ── Relative time (check first to avoid "baad" interference) ─
    m = re.search(
        r'(?:after|in|baad|me|ke\s*baad)\s+'
        r'(\d+)\s*(second|sec|minute|min|hour|hr)s?\b',
        q
    )
    if m:
        n = int(m.group(1))
        unit = m.group(2)
        multipliers = {
            "second": 1, "sec": 1,
            "minute": 60, "min": 60,
            "hour": 3600, "hr": 3600,
        }
        seconds = n * multipliers.get(unit, 1)
        return {"type": "relative", "seconds": seconds}

    # ── Shorthand: "5 minute timer", "10 second" ────────────────
    m = re.search(r'(\d+)\s*(second|sec|minute|min|hour|hr)s?', q)
    if m:
        n = int(m.group(1))
        unit = m.group(2)
        multipliers = {
            "second": 1, "sec": 1,
            "minute": 60, "min": 60,
            "hour": 3600, "hr": 3600,
        }
        seconds = n * multipliers.get(unit, 1)
        return {"type": "relative", "seconds": seconds}

    # ── Absolute time: "7 am", "7:30 pm", "5 baje" ─────────────
    m = re.search(
        r'(?:for\s+|at\s+|ko\s+)?'
        r'(\d{1,2})(?::(\d{2}))?\s*(am|pm|AM|PM|baje)?',
        q
    )
    if m:
        hour = int(m.group(1))
        minute = int(m.group(2) or 0)
        meridiem = (m.group(3) or "am").lower()

        # Handle "baje" (o'clock) — usually implies AM unless context
        if meridiem == "baje":
            meridiem = "am"

        if meridiem == "pm" and hour < 12:
            hour += 12
        if meridiem == "am" and hour == 12:
            hour = 0
        if hour > 23:
            return None

        return {"type": "absolute", "hour": hour, "minute": minute}

    # ── Pure digit: just "7" or "7:00" ──────────────────────────
    m = re.search(r'(\d{1,2})(?::(\d{2}))?\s*$', q)
    if m:
        hour = int(m.group(1))
        minute = int(m.group(2) or 0)
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return {"type": "absolute", "hour": hour, "minute": minute}

    return None


def _extract_duration_seconds(query: str) -> Optional[int]:
    """Extract duration in seconds from a timer query.

    Supports complex duration expressions:
      - "2 minutes 30 seconds"
      - "1.5 hours"
      - "5 minute"
      - "90 seconds"

    Args:
        query: Normalized query string.

    Returns:
        Total duration in seconds, or None if no duration pattern
        matches.
    """
    q = query.lower()
    total_seconds = 0
    found = False

    # Extract hours
    m = re.search(r'(\d+(?:\.\d+)?)\s*(hour|hr)s?', q)
    if m:
        total_seconds += float(m.group(1)) * 3600
        found = True

    # Extract minutes
    m = re.search(r'(\d+(?:\.\d+)?)\s*(minute|min)s?', q)
    if m:
        total_seconds += float(m.group(1)) * 60
        found = True

    # Extract seconds
    m = re.search(r'(\d+(?:\.\d+)?)\s*(second|sec)s?', q)
    if m:
        total_seconds += float(m.group(1))
        found = True

    if found:
        return int(total_seconds)

    return None


def _extract_label(query: str) -> Optional[str]:
    """Extract a clean label from a reminder/alarm/timer query.

    Strips all known action keywords and time expressions from the
    query, returning the remaining text as the label. This ensures
    that "remind me after 10 minutes meeting with boss" yields
    "meeting with boss" rather than "10 minutes meeting with boss".

    Args:
        query: Normalized query string.

    Returns:
        Clean label string, or None if nothing meaningful remains
        after stripping.
    """
    q = query.lower()

    # Remove known action keywords (longest first to avoid
    # partial stripping)
    action_words = [
        "set alarm", "set reminder", "set timer",
        "alarm", "reminder", "timer",
        "remind me to", "remind me about", "remind me for",
        "remind me", "yaad dilana", "yaad dila",
    ]
    for word in sorted(action_words, key=len, reverse=True):
        q = q.replace(word, " ")

    # Remove time expressions: both absolute and relative
    # "after 10 minutes", "in 5 hours", "7 am", "7:30 pm"
    q = re.sub(
        r'(?:after|in|baad|me|ke\s*baad|for|at|ko)\s+'
        r'\d+(?:\.\d+)?\s*(?:second|sec|minute|min|hour|hr)s?',
        '',
        q
    )
    q = re.sub(
        r'\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM|baje)?',
        '',
        q
    )

    # Remove noise words that appear around time expressions
    noise_words = [
        "minute", "minutes", "second", "seconds", "hour", "hours",
        "sec", "min", "hr", "hrs",
        "baad", "me", "ke", "ka", "ki", "ko", "se", "par", "pe",
        "after", "in", "for", "at",
        "baje", "bajkar",
    ]
    for word in noise_words:
        q = q.replace(f" {word} ", " ")

    # Clean up: collapse whitespace, strip
    q = re.sub(r'\s+', ' ', q).strip()

    return q if q and len(q) > 1 else None


def _format_duration(seconds: int) -> str:
    """Format a duration in seconds into a human-readable string.

    Args:
        seconds: Total duration in seconds.

    Returns:
        Human-readable duration string (e.g., "2 minutes 30 seconds").
    """
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
