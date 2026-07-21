"""AND9 — Intent parsers for all supported action types."""

from app.router.intent_router import detect_intent, _extract_time, _extract_label, _extract_duration


def parse_alarm(query: str) -> dict:
    """Extract alarm parameters from a normalized query."""
    _, action_type, params = detect_intent(query)
    if action_type == "set_alarm":
        time_info = _extract_time(query)
        if time_info:
            params.update(time_info)
        label = _extract_label(query)
        if label:
            params["label"] = label
        return params
    return {}


def parse_app_launch(query: str) -> dict:
    """Extract app launch parameters from a normalized query."""
    _, action_type, params = detect_intent(query)
    if action_type == "open_app":
        return params
    return {}


def parse_call(query: str) -> dict:
    """Extract call parameters from a normalized query."""
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


def parse_youtube(query: str) -> dict:
    """Extract YouTube parameters from a normalized query."""
    _, action_type, params = detect_intent(query)
    if action_type in ("youtube_search", "youtube_play"):
        return params
    return {}


def parse_reminder(query: str) -> dict:
    """Extract reminder parameters from a normalized query."""
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


def parse_search(query: str) -> dict:
    """Extract search parameters from a normalized query."""
    _, action_type, params = detect_intent(query)
    if action_type == "search":
        return params
    return {}


def parse_timer(query: str) -> dict:
    """Extract timer parameters from a normalized query."""
    _, action_type, params = detect_intent(query)
    if action_type == "set_timer":
        duration = _extract_duration(query)
        if duration:
            params["duration_seconds"] = duration
        return params
    return {}
