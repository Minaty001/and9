"""
AND9 — App Intent Parser.

Parses normalized queries to extract app launch parameters.
"""
from app.brain.planner.intent_router import detect_intent


def parse_app_launch(query: str) -> dict:
    """Extract app launch parameters from a normalized query.

    Returns:
        dict with app_name key.
    """
    _, action_type, params = detect_intent(query)
    if action_type == "open_app":
        return params
    return {}
