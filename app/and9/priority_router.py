"""
AND9 — Priority-Based Intent Router.

Fast single-pass matching engine that classifies user queries into
intent categories and routes them to the correct cognitive brain.
Intent priority is strictly ordered — a higher-priority intent always
wins over a lower-priority one when keywords overlap (e.g., "camera"
takes priority over generic "open" when both appear).

Priority chain:
  Emergency (1) > Call (2) > Message (3) > Camera (5) > Flashlight (6) >
  Bluetooth (7) > WiFi (8) > Airplane Mode (9) > Volume (10) >
  Open App (4 — after device-specific intents) > YouTube (11) > Music (12) >
  Alarm (13) > Reminder (14) > Timer (15) > Goal (16) > Home (17) >
  Search (19) > Chat (20)

Key design decision: Camera, Flashlight, Bluetooth, WiFi, Airplane Mode,
and Volume are checked BEFORE the generic Open App intent. This prevents
queries like "camera open" from being misclassified as app launch requests
when the user clearly wants the camera function.
"""
import re
import logging
from typing import Optional, Tuple

from app.and9.brain_types import BrainType, IntentType

logger = logging.getLogger(__name__)


# ── Intent Pattern Definitions ───────────────────────────────────
# Each pattern list is checked sequentially until a match is found.
# Word boundaries (\b) are used to prevent false positives from
# substring matches (e.g., "volume" in "evolume").

# Priority 1: Emergency / SOS
_EMERGENCY_PATTERNS = [
    r"\bemergency\b", r"\bhelp\b", r"\bbachao\b", r"\bdanger\b",
    r"\baccident\b", r"\bsos\b", r"\b911\b", r"\b112\b",
]

# Priority 2: Phone calls
_CALL_PATTERNS = [
    r"\bcall\b", r"\bdial\b", r"\bphone\b",
]

# Priority 3: Messaging
_MESSAGE_PATTERNS = [
    r"\bmessage\b", r"\bmsg\b", r"\bsms\b", r"\btext\b",
    r"\bwhatsapp\s+(?:message|send)\b",
]

# Priority 5: Camera / Photo
_CAMERA_PATTERNS = [
    r"\bcamera\b", r"\bphoto\b", r"\bpicture\b", r"\bselfie\b",
    r"\btake\s+(?:a\s+)?(?:photo|picture|selfie)\b",
]

# Priority 6: Flashlight / Torch
_FLASHLIGHT_PATTERNS = [
    r"\bflashlight\b", r"\btorch\b", r"\bflash\b",
    r"\blight\s+(?:on|off)\b",
]

# Priority 7: Bluetooth
_BLUETOOTH_PATTERNS = [
    r"\bbluetooth\b",
]

# Priority 8: WiFi
_WIFI_PATTERNS = [
    r"\bwifi\b", r"\bwi-fi\b", r"\bwlan\b",
]

# Priority 9: Airplane / Flight mode
_AIRPLANE_PATTERNS = [
    r"\bairplane\s*mode\b", r"\bflight\s*mode\b",
]

# Priority 10: Volume control
_VOLUME_PATTERNS = [
    r"\bvolume\b", r"\bmute\b", r"\bunmute\b", r"\bsilent\b",
    r"\blower\b", r"\blouder\b",
]

# Priority 4: Open / Launch app (generic)
_OPEN_APP_PATTERNS = [
    r"\bopen\b", r"\blaunch\b", r"\bstart\b",
]

# Priority 11: YouTube (specific — before generic music)
_YOUTUBE_PATTERNS = [
    r"\byoutube\b", r"\byt\b",
]

# Priority 12: Music / Songs
_MUSIC_PATTERNS = [
    r"\bsong\b", r"\bmusic\b", r"\bplay\b", r"\bplaylist\b",
    r"\btrack\b", r"\bsinger\b",
]

# Priority 13: Alarm
_ALARM_PATTERNS = [
    r"\balarm\b",
]

# Priority 14: Reminder
_REMINDER_PATTERNS = [
    r"\bremind\b", r"\breminder\b", r"\bremind me\b",
    r"\byaad\b",
]

# Priority 15: Timer
_TIMER_PATTERNS = [
    r"\btimer\b",
]

# Priority 16: Goals / Projects
_GOAL_PATTERNS = [
    r"\bgoal\b", r"\btarget\b", r"\blakshya\b",
    r"\bproject\b", r"\baim\b", r"\bobjective\b",
]

# Priority 17: Go Home
_HOME_PATTERNS = [
    r"\bgo\s*home\b", r"\bhome\s*screen\b", r"\bhome\s*jao\b",
]

# Priority 19: Web Search / Lookup
_SEARCH_PATTERNS = [
    r"\bsearch\b", r"\bfind\b", r"\bwho\s+is\b", r"\bwhat\s+is\b",
    r"\bwhere\s+is\b", r"\bhow\s+to\b", r"\bgoogle\b",
    r"\bweather\b", r"\bnews\b",
]

# Priority 20: LLM-requiring patterns (conscious brain)
_CONSCIOUS_PATTERNS = [
    r"\bexplain\b", r"\banalyze\b", r"\bwrite\b", r"\bcreate\b",
    r"\bplan\b", r"\bschedule\b", r"\bsummarize\b",
    r"\bcode\b", r"\bpython\b", r"\bjavascript\b",
    r"\bgenerate\s+(?:image|picture)\b",
    r"\btell\s+me\b", r"\bwhat do you think\b",
    r"\bhow (?:does|can|should|would)\b",
]

# Intent-to-brain mapping: determines which cognitive layer
# handles each intent category.
_INTENT_BRAIN_MAP = {
    IntentType.EMERGENCY: BrainType.REFLEX,
    IntentType.CALL: BrainType.REFLEX,
    IntentType.MESSAGE: BrainType.REFLEX,
    IntentType.OPEN_APP: BrainType.REFLEX,
    IntentType.CAMERA: BrainType.REFLEX,
    IntentType.FLASHLIGHT: BrainType.REFLEX,
    IntentType.BLUETOOTH: BrainType.REFLEX,
    IntentType.WIFI: BrainType.REFLEX,
    IntentType.AIRPLANE_MODE: BrainType.REFLEX,
    IntentType.VOLUME: BrainType.REFLEX,
    IntentType.YOUTUBE: BrainType.REFLEX,
    IntentType.MUSIC: BrainType.REFLEX,
    IntentType.SET_ALARM: BrainType.REFLEX,
    IntentType.SET_REMINDER: BrainType.REFLEX,
    IntentType.SET_TIMER: BrainType.REFLEX,
    IntentType.GOAL: BrainType.CONSCIOUS,
    IntentType.HOME: BrainType.REFLEX,
    IntentType.AUTOMATION: BrainType.SUBCONSCIOUS,
    IntentType.SEARCH: BrainType.CONSCIOUS,
    IntentType.CHAT: BrainType.CONSCIOUS,
}


def detect_intent(query: str) -> Tuple[Optional[IntentType], Optional[BrainType]]:
    """Classify a normalized query into an intent and target brain.

    Checks patterns strictly in priority order (emergency first,
    chat last). Returns as soon as the first pattern group matches.

    Args:
        query: Normalized, lowercased user query.

    Returns:
        Tuple of (IntentType, BrainType). Returns (None, None) for
        empty or whitespace-only queries.
    """
    q = query.lower().strip()
    if not q:
        return None, None

    # ── Priority 1: Emergency ───────────────────────────────────
    if any(re.search(p, q) for p in _EMERGENCY_PATTERNS):
        return IntentType.EMERGENCY, BrainType.REFLEX

    # ── Priority 2: Call ────────────────────────────────────────
    if any(re.search(p, q) for p in _CALL_PATTERNS):
        return IntentType.CALL, BrainType.REFLEX

    # ── Priority 3: Message ─────────────────────────────────────
    if any(re.search(p, q) for p in _MESSAGE_PATTERNS):
        return IntentType.MESSAGE, BrainType.REFLEX

    # ── Priority 5: Camera (before generic open_app) ────────────
    if any(re.search(p, q) for p in _CAMERA_PATTERNS):
        return IntentType.CAMERA, BrainType.REFLEX

    # ── Priority 6: Flashlight ──────────────────────────────────
    if any(re.search(p, q) for p in _FLASHLIGHT_PATTERNS):
        return IntentType.FLASHLIGHT, BrainType.REFLEX

    # ── Priority 7: Bluetooth ───────────────────────────────────
    if any(re.search(p, q) for p in _BLUETOOTH_PATTERNS):
        return IntentType.BLUETOOTH, BrainType.REFLEX

    # ── Priority 8: WiFi ────────────────────────────────────────
    if any(re.search(p, q) for p in _WIFI_PATTERNS):
        return IntentType.WIFI, BrainType.REFLEX

    # ── Priority 9: Airplane Mode ───────────────────────────────
    if any(re.search(p, q) for p in _AIRPLANE_PATTERNS):
        return IntentType.AIRPLANE_MODE, BrainType.REFLEX

    # ── Priority 10: Volume ─────────────────────────────────────
    if any(re.search(p, q) for p in _VOLUME_PATTERNS):
        return IntentType.VOLUME, BrainType.REFLEX

    # ── Priority 4: Open App (generic, after device-specific) ───
    if any(re.search(p, q) for p in _OPEN_APP_PATTERNS):
        return IntentType.OPEN_APP, BrainType.REFLEX

    # ── Priority 11: YouTube ────────────────────────────────────
    if any(re.search(p, q) for p in _YOUTUBE_PATTERNS):
        # "open youtube" should still open the app
        if any(kw in q for kw in ["open", "launch"]):
            return IntentType.OPEN_APP, BrainType.REFLEX
        return IntentType.YOUTUBE, BrainType.REFLEX

    # ── Priority 12: Music ──────────────────────────────────────
    if any(re.search(p, q) for p in _MUSIC_PATTERNS):
        return IntentType.MUSIC, BrainType.REFLEX

    # ── Priority 13: Alarm ──────────────────────────────────────
    if any(re.search(p, q) for p in _ALARM_PATTERNS):
        return IntentType.SET_ALARM, BrainType.REFLEX

    # ── Priority 14: Reminder ───────────────────────────────────
    if any(re.search(p, q) for p in _REMINDER_PATTERNS):
        return IntentType.SET_REMINDER, BrainType.REFLEX

    # ── Priority 15: Timer ──────────────────────────────────────
    if any(re.search(p, q) for p in _TIMER_PATTERNS):
        return IntentType.SET_TIMER, BrainType.REFLEX

    # ── Priority 16: Goal ───────────────────────────────────────
    if any(re.search(p, q) for p in _GOAL_PATTERNS):
        return IntentType.GOAL, BrainType.CONSCIOUS

    # ── Priority 17: Home ───────────────────────────────────────
    if any(re.search(p, q) for p in _HOME_PATTERNS):
        return IntentType.HOME, BrainType.REFLEX

    # ── Priority 19: Search ─────────────────────────────────────
    if any(re.search(p, q) for p in _SEARCH_PATTERNS):
        return IntentType.SEARCH, BrainType.CONSCIOUS

    # ── Priority 20: Conscious (LLM needed) ─────────────────────
    if any(re.search(p, q) for p in _CONSCIOUS_PATTERNS):
        return IntentType.CHAT, BrainType.CONSCIOUS

    # Default: Chat (conscious brain)
    return IntentType.CHAT, BrainType.CONSCIOUS


def extract_switch_state(query: str) -> Optional[bool]:
    """Determine whether a toggle command is asking for ON or OFF.

    Args:
        query: Normalized query containing an on/off keyword.

    Returns:
        True for ON/enable, False for OFF/disable, None if ambiguous
        or if state cannot be determined.
    """
    q = query.lower()
    if any(kw in q for kw in [" on", "on ", "enable", "start"]):
        if any(kw in q for kw in [" off", "off ", "disable", "stop"]):
            return None
        return True
    if any(kw in q for kw in [" off", "off ", "disable", "stop"]):
        return False
    return None


def extract_number(query: str) -> Optional[str]:
    """Extract a phone number from a query string.

    Matches sequences of 8-16 digits with optional + prefix,
    separator characters, and brackets.

    Args:
        query: Input text that may contain a phone number.

    Returns:
        Clean phone number string (digits and + only), or None.
    """
    m = re.search(r'(\+?\d[\d\s\-()]{7,15}\d)', query)
    if m:
        return re.sub(r'[\s\-()]', '', m.group(1))
    return None


def extract_contact_name(query: str) -> Optional[str]:
    """Extract a contact name from a call/message command.

    Handles patterns like:
      "call mummy"         → "mummy"
      "call amit kumar"    → "amit kumar"
      "message rahul"      → "rahul"
      "call 9876543210"    → None (looks like a number)

    Args:
        query: Normalized query.

    Returns:
        Contact name string, or None.
    """
    m = re.search(
        r'\b(?:call|dial|phone|message|text|msg|sms)\s+'
        r'(.+?)(?:\s+(?:ko|ke|ka|par|pe))?$',
        query
    )
    if m:
        name = m.group(1).strip()
        if not re.match(r'^\+?\d+$', name):
            return name
    return None


def extract_time_value(query: str) -> Optional[dict]:
    """Extract time information from alarm/timer/reminder commands.

    Supports both relative and absolute time formats:

    Relative:
      "after 5 seconds"   → {"type": "relative", "seconds": 5}
      "10 minute timer"   → {"type": "relative", "seconds": 600}

    Absolute:
      "7 am"              → {"type": "absolute", "hour": 7, "minute": 0}
      "7:30 pm"           → {"type": "absolute", "hour": 19, "minute": 30}

    Args:
        query: Normalized query.

    Returns:
        Dict with time info, or None if no time pattern matched.
    """
    q = query.lower()

    # Relative time: "after/in X seconds/minutes/hours"
    m = re.search(r'(?:after|in)\s+(\d+)\s*(second|sec|minute|min|hour|hr)s?', q)
    if m:
        n = int(m.group(1))
        unit = m.group(2)
        multipliers = {
            "second": 1, "sec": 1,
            "minute": 60, "min": 60,
            "hour": 3600, "hr": 3600,
        }
        seconds = n * multipliers.get(unit, 1)
        return {"type": "relative", "seconds": seconds, "label": ""}

    # Shorthand: "X second/minute timer"
    m = re.search(r'(\d+)\s*(second|sec|minute|min|hour|hr)s?\s*(timer|ka)?', q)
    if m:
        n = int(m.group(1))
        unit = m.group(2)
        multipliers = {
            "second": 1, "sec": 1,
            "minute": 60, "min": 60,
            "hour": 3600, "hr": 3600,
        }
        seconds = n * multipliers.get(unit, 1)
        return {"type": "relative", "seconds": seconds, "label": ""}

    # Absolute time: "for 7", "7 am", "7:30 pm"
    m = re.search(r'(?:for\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm|AM|PM)?', q)
    if m:
        hour = int(m.group(1))
        minute = int(m.group(2) or 0)
        meridiem = (m.group(3) or "am").lower()
        if meridiem == "pm" and hour < 12:
            hour += 12
        if meridiem == "am" and hour == 12:
            hour = 0
        return {"type": "absolute", "hour": hour, "minute": minute}

    return None


def extract_reminder_text(query: str) -> str:
    """Extract the title/label from a reminder/alarm command.

    Strips action keywords and time expressions, returning whatever
    meaningful text remains as the reminder title.

    Args:
        query: Normalized query.

    Returns:
        Clean reminder title, or empty string if nothing remains.
    """
    q = query.lower()
    for kw in [
        "set alarm", "set reminder", "set timer", "alarm", "reminder",
        "timer", "remind me to", "remind me about", "remind me for",
        "yaad dilana",
    ]:
        q = q.replace(kw, " ")
    q = re.sub(r'(?:for\s+)?\d{1,2}(?::\d{2})?\s*(?:am|pm)?', '', q)
    q = re.sub(r'(?:after|in)\s+\d+\s*(?:second|sec|minute|min|hour|hr)s?', '', q)
    q = re.sub(r'\s+', ' ', q).strip()
    return q
