"""
AND9 — Alarm Intent Parser.

Parses normalized queries to extract alarm parameters.
Delegates time parsing to router/intent_router.py.
"""
from backend.cognition.planner.intent_router import detect_intent, _extract_time, _extract_label


def parse_alarm(query: str) -> dict:
    """Extract alarm parameters from a normalized query.

    Returns:
        dict with hour, minute, label, and type keys.
    """
    _, action_type, params = detect_intent(query)
    if action_type == "set_alarm":
        # Add time params from raw query
        time_info = _extract_time(query)
        if time_info:
            params.update(time_info)
        label = _extract_label(query)
        if label:
            params["label"] = label
        return params
    return {}
