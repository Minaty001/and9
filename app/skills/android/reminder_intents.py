"""
AND9 — Reminder Intent Parser.

Parses normalized queries to extract reminder parameters.
"""
from app.brain.planner.intent_router import detect_intent, _extract_time, _extract_label


def parse_reminder(query: str) -> dict:
    """Extract reminder parameters from a normalized query.

    Returns:
        dict with trigger_at, label, and type keys.
    """
    _, action_type, params = detect_intent(query)
    if action_type == "set_reminder":
        time_info = _extract_time(query)
        if time_info:
            params["trigger_at"] = time_info
        label = _extract_label(query)
        if label:
            params["label"] = label
        return params
    return {}
