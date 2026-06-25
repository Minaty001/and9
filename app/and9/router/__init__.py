"""AND9 — Intent Routing Pipeline.

The routing layer normalizes user queries, detects intents, extracts entities,
validates parameters, and scores confidence.
"""

from .normalizer import QueryNormalizer
from .entity_extractor import (
    extract_entities,
    extract_call,
    extract_message,
    extract_app,
    extract_youtube,
    extract_alarm,
    extract_timer,
    extract_reminder,
    extract_search,
)
from .intent_router import detect_intent, detect_intent_with_confidence
from .intent_validator import validate_intent
from .command_dictionary import (
    EMERGENCY, CALL_CONTACT, CALL_NUMBER, MESSAGE,
    OPEN_APP_SPECIFIC, OPEN_APP_GENERIC, CAMERA,
    YOUTUBE_SEARCH_PATTERNS, YOUTUBE_PLAY_PATTERNS,
    ALARM_PATTERNS, REMINDER_PATTERNS, TIMER_PATTERNS, CHAT_TRIGGERS,
)
from .confidence_scorer import score_intent

__all__ = [
    "QueryNormalizer",
    "extract_entities",
    "extract_call",
    "extract_message",
    "extract_app",
    "extract_youtube",
    "extract_alarm",
    "extract_timer",
    "extract_reminder",
    "extract_search",
    "detect_intent",
    "detect_intent_with_confidence",
    "validate_intent",
    "EMERGENCY", "CALL_CONTACT", "CALL_NUMBER", "MESSAGE",
    "OPEN_APP_SPECIFIC", "OPEN_APP_GENERIC", "CAMERA",
    "YOUTUBE_SEARCH_PATTERNS", "YOUTUBE_PLAY_PATTERNS",
    "ALARM_PATTERNS", "REMINDER_PATTERNS", "TIMER_PATTERNS", "CHAT_TRIGGERS",
    "score_intent",
]
