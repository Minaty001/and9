"""
AND9 — Central Intent Router (Phase 3 of Refactor).

Single-file intent detection with strict priority ordering.
Device actions ALWAYS beat search. Search is always last.

Priority order:
    EMERGENCY (1) → CALL (2) → MESSAGE (3) → OPEN_APP (4) →
    CAMERA (5) → FLASHLIGHT (6) → YOUTUBE (7) → ALARM (8) →
    REMINDER (9) → TIMER (10) → DEVICE_CONTROL (11) →
    SEARCH (12) → CHAT (13)

Each intent returns structured parameters for the action layer.
"""
import re
from typing import Optional, Tuple

from app.and9.core.constants import ActionType


def detect_intent(query: str) -> Tuple[Optional[str], Optional[str], dict]:
    """Classify a normalized query into an intent with parameters.

    Args:
        query: Lowercased, normalized query string.

    Returns:
        Tuple of (intent_name, action_type, parameters_dict).
        intent_name is None for empty queries.
        action_type is the ActionType value to execute.
        parameters_dict contains extracted structured data.

    Example:
        >>> detect_intent("call mummy")
        ('call', 'call', {'number': '', 'contact': 'mummy', 'action_type': 'contact'})
        >>> detect_intent("hello")
        ('chat', None, {'query': 'hello'})
    """
    q = query.lower().strip()
    if not q:
        return None, None, {}

    # ── Priority 1: EMERGENCY ───────────────────────────────────
    if re.search(r'\b(emergency|help|bachao|danger|accident|sos|911|112)\b', q):
        return 'emergency', ActionType.EMERGENCY.value, {'type': 'emergency'}

    # ── Priority 2: CALL ────────────────────────────────────────
    m = re.search(r'(call|dial|phone)\s+(.+)', q)
    if m:
        target = m.group(2).strip().rstrip('ko').strip()
        # Check if it's a phone number
        if re.match(r'^\+?\d[\d\s\-()]{6,15}$', target):
            number = re.sub(r'[\s\-()]', '', target)
            return 'call', ActionType.CALL.value, {'number': number, 'action_type': 'dial'}
        else:
            return 'call', ActionType.CALL.value, {'contact': target, 'action_type': 'contact'}

    # ── Priority 3: MESSAGE ─────────────────────────────────────
    if re.search(r'\b(message|msg|sms|text)\b', q):
        m = re.search(r'(?:message|msg|sms|text)\s+(.+?)(?:\s+(.+))?$', q)
        if m:
            target = m.group(1).strip()
            text = m.group(2).strip() if m.group(2) else ''
            if re.match(r'^\+?\d[\d\s\-()]{6,15}$', target):
                number = re.sub(r'[\s\-()]', '', target)
                return 'message', ActionType.SEND_SMS.value, {'number': number, 'message': text}
            return 'message', ActionType.SEND_SMS.value, {'contact': target, 'message': text}
        return 'message', ActionType.SEND_SMS.value, {}

    # ── Priority 4: OPEN_APP (generic) ──────────────────────────
    # But first check device-specific intents that start with "open"
    if re.search(r'\bopen\b', q):
        # Check for camera
        if re.search(r'\bcamera\b', q):
            return 'camera', ActionType.OPEN_CAMERA.value, {}
        # Check for YouTube open
        if re.search(r'\byoutube\b', q) and not re.search(r'\b(search|play)\b', q):
            return 'youtube', ActionType.YOUTUBE_SEARCH.value, {'action': 'open'}

        # Generic app open
        m = re.search(r'\bopen\s+(.+)$', q)
        if m:
            app_name = m.group(1).strip()
            return 'open_app', ActionType.LAUNCH_APP.value, {'app_name': app_name}
        # <app> open pattern
        m = re.search(r'^(.+?)\s+open$', q)
        if m:
            app_name = m.group(1).strip()
            return 'open_app', ActionType.LAUNCH_APP.value, {'app_name': app_name}

    # ── Priority 5: CAMERA ──────────────────────────────────────
    if re.search(r'\b(camera|photo|picture|selfie)\b', q):
        return 'camera', ActionType.OPEN_CAMERA.value, {}

    # ── Priority 6: FLASHLIGHT ──────────────────────────────────
    if re.search(r'\b(flashlight|torch|flash|light)\b', q):
        # Determine on/off state
        state = None
        if re.search(r'\b(on|enable|kholo|chalu)\b', q):
            state = True
        elif re.search(r'\b(off|disable|band|bnd)\b', q):
            state = False
        return 'flashlight', ActionType.FLASHLIGHT.value, {'state': state}

    # ── Priority 7: YOUTUBE ─────────────────────────────────────
    if re.search(r'\byoutube\b', q):
        if re.search(r'\b(play|bajao|chalao|sunao)\b', q):
            return 'youtube', ActionType.YOUTUBE_PLAY.value, {'action': 'play', 'query': q}
        if re.search(r'\bsearch\b', q):
            m = re.search(r'youtube\s+search\s+(.+)$', q)
            sq = m.group(1).strip() if m else q
            return 'youtube', ActionType.YOUTUBE_SEARCH.value, {'action': 'search', 'query': sq}
        # Default: just open YouTube
        return 'youtube', ActionType.YOUTUBE_SEARCH.value, {'action': 'open'}
    # Music/song commands also go to YouTube
    if re.search(r'\b(song|music|play|gaana|gana|geet|bajao|sunao|playlist|track)\b', q):
        return 'youtube', ActionType.YOUTUBE_PLAY.value, {'action': 'play', 'query': q}

    # ── Priority 8: ALARM ───────────────────────────────────────
    if re.search(r'\balarm\b', q):
        time_params = _extract_time(q)
        return 'alarm', ActionType.SET_ALARM.value, time_params or {'type': 'unknown'}

    # ── Priority 9: REMINDER ────────────────────────────────────
    if re.search(r'\b(remind|reminder|yaad)\b', q):
        time_params = _extract_time(q)
        label = _extract_label(q)
        params = time_params or {'type': 'unknown'}
        if label:
            params['label'] = label
        return 'reminder', ActionType.SET_REMINDER.value, params

    # ── Priority 10: TIMER ──────────────────────────────────────
    if re.search(r'\btimer\b', q):
        duration = _extract_duration(q)
        return 'timer', ActionType.SET_TIMER.value, {'duration_seconds': duration} if duration else {'type': 'unknown'}

    # ── Priority 11: DEVICE_CONTROL ─────────────────────────────
    # Volume
    if re.search(r'\b(volume|mute|unmute|silent)\b', q):
        if re.search(r'\b(up|badhao|higher|louder|increase)\b', q):
            return 'volume', ActionType.VOLUME_UP.value, {}
        if re.search(r'\b(down|kam|lower|decrease|less)\b', q):
            return 'volume', ActionType.VOLUME_DOWN.value, {}
        if re.search(r'\b(mute|silent)\b', q):
            return 'volume', ActionType.VOLUME_MUTE.value, {}
        return 'volume', ActionType.VOLUME_UP.value, {}

    # WiFi
    if re.search(r'\b(wifi|wi-fi|wlan)\b', q):
        state = bool(re.search(r'\b(on|enable|chalu)\b', q)) if re.search(r'\b(on|enable|off|disable|band|chalu)\b', q) else None
        return 'wifi', ActionType.WIFI.value, {'state': state}

    # Bluetooth
    if re.search(r'\bbluetooth\b', q):
        state = bool(re.search(r'\b(on|enable|chalu)\b', q)) if re.search(r'\b(on|enable|off|disable|band|chalu)\b', q) else None
        return 'bluetooth', ActionType.BLUETOOTH.value, {'state': state}

    # Airplane mode
    if re.search(r'\b(airplane\s*mode|flight\s*mode)\b', q):
        state = bool(re.search(r'\b(on|enable)\b', q)) if re.search(r'\b(on|enable|off|disable)\b', q) else None
        return 'airplane', ActionType.AIRPLANE_MODE.value, {'state': state}

    # Go home
    if re.search(r'\bgo\s*home\b', q):
        return 'home', ActionType.GO_HOME.value, {}

    # ── Priority 12: SEARCH (always last for device actions) ───
    if re.search(r'\b(search|find|who|what|where|how|google|weather|news)\b', q):
        return 'search', ActionType.SEARCH.value, {'query': q}

    # ── Priority 13: CHAT (default fallback) ────────────────────
    return 'chat', None, {'query': q}


def _extract_time(query: str) -> dict:
    """Extract time parameters from a query.

    Returns dict with 'type': 'absolute' or 'relative' and
    time-specific fields.
    """
    q = query.lower().strip()

    # Relative: "after 10 minutes", "in 5 seconds"
    m = re.search(r'(?:after|in|baad|me|ke\s*baad)\s+(\d+)\s*(second|sec|minute|min|hour|hr)s?', q)
    if m:
        n = int(m.group(1))
        unit = m.group(2)
        mult = {"second": 1, "sec": 1, "minute": 60, "min": 60, "hour": 3600, "hr": 3600}
        return {"type": "relative", "seconds": n * mult.get(unit, 1)}

    # Absolute: "7 am", "7:30 pm", "7 baje"
    m = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm|AM|PM|baje)?', q)
    if m:
        hour = int(m.group(1))
        minute = int(m.group(2) or 0)
        meridiem = (m.group(3) or "am").lower()
        if meridiem == "baje":
            meridiem = "am"
        if meridiem == "pm" and hour < 12:
            hour += 12
        if meridiem == "am" and hour == 12:
            hour = 0
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return {"type": "absolute", "hour": hour, "minute": minute}

    return {}


def _extract_duration(query: str) -> Optional[int]:
    """Extract duration in seconds from a timer query."""
    q = query.lower().strip()
    total = 0
    found = False

    m = re.search(r'(\d+(?:\.\d+)?)\s*(hour|hr)s?', q)
    if m:
        total += float(m.group(1)) * 3600
        found = True
    m = re.search(r'(\d+(?:\.\d+)?)\s*(minute|min)s?', q)
    if m:
        total += float(m.group(1)) * 60
        found = True
    m = re.search(r'(\d+(?:\.\d+)?)\s*(second|sec)s?', q)
    if m:
        total += float(m.group(1))
        found = True

    return int(total) if found else None


def _extract_label(query: str) -> Optional[str]:
    """Extract reminder label by stripping action keywords and time."""
    q = query.lower().strip()
    for word in [
        "set alarm", "set reminder", "set timer",
        "alarm", "reminder", "timer",
        "remind me to", "remind me about", "remind me for",
        "remind me", "yaad dilana", "yaad dila",
    ]:
        q = q.replace(word, " ")

    q = re.sub(
        r'(?:after|in|baad|me|ke\s*baad|for|at|ko)\s+'
        r'\d+(?:\.\d+)?\s*(?:second|sec|minute|min|hour|hr)s?',
        '', q
    )
    q = re.sub(r'\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM|baje)?', '', q)

    noise = ["minute", "minutes", "second", "seconds", "hour", "hours",
             "sec", "min", "hr", "hrs", "baad", "me", "ke", "ka", "ki",
             "ko", "se", "par", "pe", "after", "in", "for", "at",
             "baje", "bajkar"]
    for w in noise:
        q = q.replace(f" {w} ", " ")

    q = re.sub(r'\s+', ' ', q).strip()
    return q if q and len(q) > 1 else None
