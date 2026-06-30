"""
AND9 — Call Intent Parser.

Parses normalized queries to extract call parameters.
Delegates parsing to router/intent_router.py.
"""
from app.brain.planner.intent_router import detect_intent


def parse_call(query: str) -> dict:
    """Extract call parameters from a normalized query.

    Returns:
        dict with number, contact, and action_type keys.
    """
    _, action_type, params = detect_intent(query)
    if action_type == "call":
        return params
    return {}


def parse_message(query: str) -> dict:
    """Extract message parameters from a normalized query."""
    _, action_type, params = detect_intent(query)
    if action_type == "send_sms":
        return params
    return {}
