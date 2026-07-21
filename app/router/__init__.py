"""app/router — Intent detection pipeline."""

from app.router.normalizer import QueryNormalizer
from app.router.intent_router import detect_intent
from app.router.intent_validator import validate_intent
from app.router.entity_extractor import extract_entities
from app.router.intents import (  # consolidated intent parsers
    parse_alarm, parse_timer, parse_reminder, parse_call, parse_message,
    parse_app_launch, parse_youtube, parse_search,
)

__all__ = [
    "QueryNormalizer", "detect_intent", "validate_intent", "extract_entities",
    "parse_alarm", "parse_timer", "parse_reminder", "parse_call", "parse_message",
    "parse_app_launch", "parse_youtube", "parse_search",
]
