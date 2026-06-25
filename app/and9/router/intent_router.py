"""
AND9 — Central Intent Router (Phase 5 Refactor).

Single-responsibility: CLASSIFY ONLY.
All entity extraction is delegated to entity_extractor.py.
All regex patterns are imported from command_dictionary.py.

AND9 Cognitive Architecture — Execution Priority:
    EMERGENCY (1) → CALL (2) → MESSAGE (3) → OPEN_APP (4) →
    CAMERA (5) → FLASHLIGHT (6) → BLUETOOTH (7) → WIFI (8) →
    VOLUME (9) → YOUTUBE (10) → MUSIC (11) → ALARM (12) →
    REMINDER (13) → TIMER (14) → GOAL (15) → AUTOMATION (16) →
    SEARCH (17) → CHAT (18)

Search is ALWAYS last. Device actions ALWAYS win.
Chrome is NEVER opened except for SEARCH/NEWS/WEB_LOOKUP.
"""
import re
import logging
from functools import lru_cache
from typing import Optional, Tuple

from app.and9.core.constants import ActionType
from app.and9.router.command_dictionary import (
    EMERGENCY,
    CALL_CONTACT, CALL_NUMBER, IS_PHONE_NUMBER,
    MESSAGE,
    OPEN_APP_TRIGGERS, OPEN_APP_SPECIFIC,
    CAMERA,
    FLASHLIGHT, FLASHLIGHT_ON, FLASHLIGHT_OFF,
    BLUETOOTH, TOGGLE_ON, TOGGLE_OFF,
    WIFI,
    VOLUME, VOLUME_UP, VOLUME_DOWN, VOLUME_MUTE, VOLUME_MAX,
    YOUTUBE_TRIGGER, YOUTUBE_PLAY_TRIGGER, YOUTUBE_OPEN_ONLY,
    MUSIC_TRIGGER,
    ALARM_TRIGGER,
    REMINDER_TRIGGER,
    TIMER_TRIGGER,
    TIME_TRIGGER,
    GOAL_TRIGGER,
    AUTOMATION_TRIGGER,
    SEARCH_TRIGGER,
    GO_HOME,
    AIRPLANE_MODE,
)
from app.and9.router.entity_extractor import extract_entities

logger = logging.getLogger(__name__)


@lru_cache(maxsize=512)
def detect_intent(query: str) -> Tuple[Optional[str], Optional[str], dict]:
    """Classify a normalized query into an intent with extracted parameters.

    The router ONLY classifies — no regex extraction happens here.
    All entity extraction is handled by entity_extractor.extract_entities().

    Args:
        query: Lowercased, normalized query string.

    Returns:
        Tuple of (intent_name, action_type, parameters_dict).
        intent_name is None for empty queries.
        action_type is an ActionType value string.
        parameters_dict contains extracted structured entities.

    Priority order:
        1. EMERGENCY   7. BLUETOOTH  13. REMINDER
        2. CALL        8. WIFI       14. TIMER
        3. MESSAGE     9. VOLUME     15. CITY_TIME
        4. OPEN_APP   10. YOUTUBE    16. GOAL
        5. CAMERA     11. MUSIC      17. AUTOMATION
        6. FLASHLIGHT 12. ALARM      18. SEARCH
                                                           19. CHAT
    """
    q = query.lower().strip()
    if not q:
        return None, None, {}

    # ── Priority 1: EMERGENCY ─────────────────────────────────────
    for pattern in EMERGENCY:
        if pattern.search(q):
            return 'emergency', ActionType.EMERGENCY.value, {'type': 'emergency'}

    # ── Priority 2: CALL ─────────────────────────────────────────
    # Check call patterns before open (avoids "call" being caught by app launch)
    for pattern in CALL_NUMBER:
        if pattern.search(q):
            return 'call', ActionType.CALL.value, extract_entities('call', q)

    for pattern in CALL_CONTACT:
        if pattern.search(q):
            return 'call', ActionType.CALL.value, extract_entities('call', q)

    # ── Priority 3: MESSAGE ──────────────────────────────────────
    if MESSAGE[0].search(q):
        return 'message', ActionType.SEND_SMS.value, extract_entities('message', q)

    # ── Priority 4: OPEN APP ─────────────────────────────────────
    # First ensure it's not a device-specific command masquerading as open
    has_open_trigger = OPEN_APP_TRIGGERS.search(q)

    if has_open_trigger:
        # Camera is Priority 5 but "camera kholo" triggers open — handle here
        for pattern in CAMERA:
            if pattern.search(q):
                return 'camera', ActionType.OPEN_CAMERA.value, {}

        # YouTube open → Priority 10, but "youtube kholo" is app launch
        if YOUTUBE_TRIGGER.search(q) and not YOUTUBE_PLAY_TRIGGER.search(q):
            params = extract_entities('youtube', q)
            if params.get('action') == 'open':
                return 'youtube', ActionType.YOUTUBE_SEARCH.value, params
            # Has a query → youtube search
            return 'youtube', ActionType.YOUTUBE_SEARCH.value, params

        # Generic app open
        params = extract_entities('open_app', q)
        if params.get('app_name'):
            return 'open_app', ActionType.LAUNCH_APP.value, params

    # ── Priority 5: CAMERA ───────────────────────────────────────
    for pattern in CAMERA:
        if pattern.search(q):
            return 'camera', ActionType.OPEN_CAMERA.value, {}

    # ── Priority 6: FLASHLIGHT ───────────────────────────────────
    if FLASHLIGHT.search(q):
        state = None
        if FLASHLIGHT_ON.search(q):
            state = True
        elif FLASHLIGHT_OFF.search(q):
            state = False
        action = ActionType.FLASHLIGHT_ON.value if state is True \
            else ActionType.FLASHLIGHT_OFF.value if state is False \
            else ActionType.FLASHLIGHT.value
        return 'flashlight', action, {'state': state}

    # ── Priority 7: BLUETOOTH ────────────────────────────────────
    if BLUETOOTH.search(q):
        state = None
        if TOGGLE_ON.search(q):
            state = True
        elif TOGGLE_OFF.search(q):
            state = False
        return 'bluetooth', ActionType.BLUETOOTH.value, {'state': state}

    # ── Priority 8: WIFI ─────────────────────────────────────────
    if WIFI.search(q):
        state = None
        if TOGGLE_ON.search(q):
            state = True
        elif TOGGLE_OFF.search(q):
            state = False
        return 'wifi', ActionType.WIFI.value, {'state': state}

    # ── Airplane mode (between WiFi and Volume) ───────────────────
    if AIRPLANE_MODE.search(q):
        state = None
        if TOGGLE_ON.search(q):
            state = True
        elif TOGGLE_OFF.search(q):
            state = False
        return 'airplane', ActionType.AIRPLANE_MODE.value, {'state': state}

    # ── Priority 9: VOLUME ───────────────────────────────────────
    if VOLUME.search(q):
        if VOLUME_MAX.search(q):
            return 'volume', ActionType.VOLUME_MAX.value, {}
        if VOLUME_MUTE.search(q):
            return 'volume', ActionType.VOLUME_MUTE.value, {}
        if VOLUME_UP.search(q):
            return 'volume', ActionType.VOLUME_UP.value, {}
        if VOLUME_DOWN.search(q):
            return 'volume', ActionType.VOLUME_DOWN.value, {}
        return 'volume', ActionType.VOLUME_UP.value, {}

    # ── Go Home (device control) ─────────────────────────────────
    if GO_HOME.search(q):
        return 'home', ActionType.GO_HOME.value, {}

    # ── Priority 10: YOUTUBE ─────────────────────────────────────
    if YOUTUBE_TRIGGER.search(q):
        params = extract_entities('youtube', q)
        action = params.get('action', 'open')
        if action == 'play':
            return 'youtube', ActionType.YOUTUBE_PLAY.value, params
        if action == 'search':
            return 'youtube', ActionType.YOUTUBE_SEARCH.value, params
        return 'youtube', ActionType.YOUTUBE_SEARCH.value, params

    # ── Priority 11: MUSIC ───────────────────────────────────────
    if MUSIC_TRIGGER.search(q):
        params = extract_entities('youtube', q)
        params['action'] = 'play'
        return 'youtube', ActionType.YOUTUBE_PLAY.value, params

    # ── Priority 12: ALARM ───────────────────────────────────────
    if ALARM_TRIGGER.search(q):
        return 'alarm', ActionType.SET_ALARM.value, extract_entities('alarm', q)

    # ── Priority 13: REMINDER ────────────────────────────────────
    if REMINDER_TRIGGER.search(q):
        return 'reminder', ActionType.SET_REMINDER.value, extract_entities('reminder', q)

    # ── Priority 14: TIMER ───────────────────────────────────────
    if TIMER_TRIGGER.search(q):
        return 'timer', ActionType.SET_TIMER.value, extract_entities('timer', q)

    # ── Priority 15: CITY TIME (before generic TIME / GOAL) ────────
    from app.and9.utils.timezone_utils import detect_city_time_query
    city = detect_city_time_query(q)
    if city:
        return 'city_time', ActionType.CITY_TIME.value, {'city': city}

    # ── Priority 15: TIME (generic, after city_time) ───────────────
    # Catches "time batao", "what's time" etc. Only matches after
    # city_time check fails (no city detected in query).
    if TIME_TRIGGER.search(q):
        return 'time', ActionType.GET_TIME.value, {}

    # ── Priority 16: GOAL ────────────────────────────────────────
    if GOAL_TRIGGER.search(q):
        return 'goal', ActionType.CHAT.value, {'query': q}

    # ── Priority 16: AUTOMATION ──────────────────────────────────
    if AUTOMATION_TRIGGER.search(q):
        return 'automation', ActionType.CHAT.value, {'query': q}

    # ── Priority 17: SEARCH (LAST for device actions) ────────────
    if SEARCH_TRIGGER.search(q):
        return 'search', ActionType.SEARCH.value, extract_entities('search', q)

    # ── Priority 18: CHAT (default fallback) ─────────────────────
    return 'chat', ActionType.CHAT.value, {'query': q}


def detect_intent_with_confidence(query: str) -> Tuple[Optional[str], Optional[str], dict, float]:
    """Classify a normalized query into an intent with confidence scoring.

    Args:
        query: Normalized query string.

    Returns:
        Tuple of (intent_name, action_type, parameters_dict, confidence_score).
    """
    intent, action, params = detect_intent(query)
    if intent is None:
        return None, None, {}, 0.0
    
    from app.and9.router.confidence_scorer import score_intent
    confidence = score_intent(intent, query, params)
    return intent, action, params, confidence


# ── Backwards compatibility shims ────────────────────────────────
# These are kept so existing callers don't break during migration.
# They delegate to the unified time parser.

def _extract_time(query: str) -> dict:
    """DEPRECATED: Use app.and9.utils.time_parser.parse_time() instead."""
    from app.and9.utils.time_parser import parse_time
    result = parse_time(query)
    if result['type'] == 'unknown':
        return {}
    return result


def _extract_duration(query: str) -> Optional[int]:
    """DEPRECATED: Use app.and9.utils.time_parser.parse_duration() instead."""
    from app.and9.utils.time_parser import parse_duration
    return parse_duration(query)


def _extract_label(query: str) -> Optional[str]:
    """DEPRECATED: Use app.and9.router.entity_extractor._extract_label() instead."""
    from app.and9.router.entity_extractor import _extract_label
    return _extract_label(query)
