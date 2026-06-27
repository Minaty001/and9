"""
AND9 — Timer Intent Parser.

Parses normalized queries to extract timer duration.
"""
from backend.cognition.planner.intent_router import detect_intent, _extract_duration


def parse_timer(query: str) -> dict:
    """Extract timer parameters from a normalized query.

    Returns:
        dict with duration_seconds key.
    """
    _, action_type, params = detect_intent(query)
    if action_type == "set_timer":
        duration = _extract_duration(query)
        if duration:
            params["duration_seconds"] = duration
        return params
    return {}
