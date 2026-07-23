"""
AND9 — Accessibility Actions Handler.

Handlers for screen awareness and element interaction actions.
These run server-side and produce action payloads that the Android
client executes via JarvisAccessibilityService.

Each handler returns a uniform dict with response text,
action type, and payload for the Android client.
"""
import logging

logger = logging.getLogger(__name__)


def describe_screen(query: str = "") -> dict:
    """Request the Android client to describe the current screen."""
    return {
        "response": "Screen describe kar raha hoon... Bata raha hoon screen pe kya hai.",
        "action": "DESCRIBE_SCREEN",
        "payload": {"action": "describe_screen"},
    }


def click_element(query: str = "", text: str = "") -> dict:
    """Request clicking a UI element matching the given text/description."""
    target = text or query
    return {
        "response": f"'{target}' ko click kar raha hoon... 👆",
        "action": "CLICK_ELEMENT",
        "payload": {
            "action": "click_element",
            "payload": target,
        },
    }


def type_text(query: str = "", text: str = "", field: str = "") -> dict:
    """Request typing text into the currently focused or specified field."""
    input_text = text or query
    return {
        "response": f"'{input_text}' type kar raha hoon... ⌨️",
        "action": "TYPE_TEXT",
        "payload": {
            "action": "type_text",
            "payload": input_text,
            "field": field,
        },
    }


def scroll(query: str = "", direction: str = "") -> dict:
    """Request scrolling in the specified direction."""
    dir_val = direction or query.lower().strip()
    if any(kw in dir_val for kw in ["down", "neeche", "niche", "forward"]):
        direction_final = "forward"
        response_text = "Neeche scroll kar raha hoon... 📜"
    elif any(kw in dir_val for kw in ["up", "upar", "backward", "back"]):
        direction_final = "backward"
        response_text = "Upar scroll kar raha hoon... 📜"
    else:
        direction_final = "forward"
        response_text = "Scroll kar raha hoon... 📜"

    return {
        "response": response_text,
        "action": "SCREEN_SCROLL",
        "payload": {
            "action": "scroll",
            "payload": direction_final,
        },
    }


def list_elements(query: str = "") -> dict:
    """Request listing all actionable elements on the current screen."""
    return {
        "response": "Screen pe jo kuch hai, bata raha hoon... 🔍",
        "action": "LIST_ELEMENTS",
        "payload": {"action": "list_elements"},
    }


def get_current_app(query: str = "") -> dict:
    """Request the current foreground app info from the device."""
    return {
        "response": "Current app pata kar raha hoon... 📱",
        "action": "GET_CURRENT_APP",
        "payload": {"action": "get_current_app"},
    }
