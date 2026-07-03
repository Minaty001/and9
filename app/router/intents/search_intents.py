"""
AND9 — Search Intent Parser.

Parses normalized queries to extract search parameters.
"""
from app.router.intent_router import detect_intent


def parse_search(query: str) -> dict:
    """Extract search parameters from a normalized query.

    Returns:
        dict with query key.
    """
    _, action_type, params = detect_intent(query)
    if action_type == "search":
        return params
    return {}
