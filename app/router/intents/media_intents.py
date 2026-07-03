"""
AND9 — Media Intent Parser.

Parses normalized queries to extract media playback parameters.
"""
from app.router.intent_router import detect_intent


def parse_youtube(query: str) -> dict:
    """Extract YouTube parameters from a normalized query.

    Returns:
        dict with action (search/play/open), query keys.
    """
    _, action_type, params = detect_intent(query)
    if action_type in ("youtube_search", "youtube_play"):
        return params
    return {}
