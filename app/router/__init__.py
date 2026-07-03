"""
app/router — Intent detection pipeline.

Normalization → intent detection → entity extraction → validation.
And intent-specific parsers for alarm, timer, reminder, call, app, media, search.
"""

from app.router.normalizer import QueryNormalizer
from app.router.intent_router import detect_intent
from app.router.intent_validator import validate_intent
from app.router.entity_extractor import extract_entities

# Intent-specific parsers
from app.router.intents.alarm_intents import parse_alarm
from app.router.intents.timer_intents import parse_timer
from app.router.intents.reminder_intents import parse_reminder
from app.router.intents.call_intents import parse_call, parse_message
from app.router.intents.app_intents import parse_app_launch
from app.router.intents.media_intents import parse_youtube
from app.router.intents.search_intents import parse_search

__all__ = [
    "QueryNormalizer",
    "detect_intent",
    "validate_intent",
    "extract_entities",
    "parse_alarm",
    "parse_timer",
    "parse_reminder",
    "parse_call",
    "parse_message",
    "parse_app_launch",
    "parse_youtube",
    "parse_search",
]
