"""
AND9 — Device Control Actions (Phase 16 of Refactor).

Stateless handler functions for Android device features.
Each function returns a uniform dict with response text,
action type, and Android Intent payload.

Supported controls:
    - Flashlight (on/off/toggle)
    - Volume (up/down/mute/max)
    - WiFi (on/off/toggle)
    - Bluetooth (on/off/toggle)
    - Airplane mode (on/off/toggle)
    - Home screen
    - Camera
"""
import logging
import re

logger = logging.getLogger(__name__)


def handle_flashlight(q: str = "", query: str = "") -> dict:
    """Toggle flashlight on/off based on query context."""
    q = (q or query).lower()
    has_on = bool(re.search(r'\b(on|enable|kholo|chalu)\b', q))
    has_off = bool(re.search(r'\b(off|disable|band|bnd)\b', q))

    if has_on and not has_off:
        return {"response": "Flashlight on kar diya! 💡", "action": "FLASHLIGHT", "payload": {"state": True}}
    elif has_off and not has_on:
        return {"response": "Flashlight off kar diya! 🌙", "action": "FLASHLIGHT", "payload": {"state": False}}
    else:
        return {"response": "Flashlight toggle kar diya! 💡", "action": "FLASHLIGHT", "payload": {"state": "toggle"}}


def handle_volume(keyword: str = "", q: str = "", query: str = "") -> dict:
    """Adjust volume based on query context.

    Args:
        keyword: Direction keyword from skill_registry ("up", "down", "mute", "max").
        q:       Raw query string (legacy).
        query:   Raw query string (legacy).
    """
    q = (keyword or q or query).lower()
    # Check unmute BEFORE mute (since "mute" is a substring of "unmute")
    if any(kw in q for kw in ["unmute", "sound on"]):
        return {"response": "Sound wapas on kar diya! 🔊", "action": "VOLUME_MAX", "payload": {"level": 7}}
    if any(kw in q for kw in ["mute", "silent", "zero", "0"]):
        return {"response": "Phone mute kar diya! 🔇", "action": "VOLUME_MUTE", "payload": {"level": 0}}
    if any(kw in q for kw in ["max", "full", "100", "highest"]):
        return {"response": "Volume full kar diya! 🔊📢", "action": "VOLUME_MAX", "payload": {"level": 15}}
    if any(kw in q for kw in ["up", "badhao", "higher", "louder", "increase"]):
        return {"response": "Volume badha diya! 🔊", "action": "VOLUME_UP", "payload": {"delta": 2}}
    if any(kw in q for kw in ["down", "kam", "lower", "decrease", "less"]):
        return {"response": "Volume kam kar diya! 🔉", "action": "VOLUME_DOWN", "payload": {"delta": 2}}
    return {"response": "Volume badha diya! 🔊", "action": "VOLUME_UP", "payload": {"delta": 2}}


def handle_wifi(q: str = "", query: str = "") -> dict:
    """Toggle WiFi on/off."""
    q = (q or query).lower()
    has_on = bool(re.search(r'\b(on|enable|chalu)\b', q))
    has_off = bool(re.search(r'\b(off|disable|band|bnd)\b', q))
    if has_on and not has_off:
        return {"response": "WiFi on kar diya! 🌐", "action": "WIFI", "payload": {"state": True}}
    elif has_off and not has_on:
        return {"response": "WiFi off kar diya! 📶", "action": "WIFI", "payload": {"state": False}}
    return {"response": "WiFi toggle kar diya! 🌐", "action": "WIFI", "payload": {"state": "toggle"}}


def handle_bluetooth(q: str = "", query: str = "") -> dict:
    """Toggle Bluetooth on/off."""
    q = (q or query).lower()
    has_on = bool(re.search(r'\b(on|enable|chalu)\b', q))
    has_off = bool(re.search(r'\b(off|disable|band|bnd)\b', q))
    if has_on and not has_off:
        return {"response": "Bluetooth on kar diya! 🔵", "action": "BLUETOOTH", "payload": {"state": True}}
    elif has_off and not has_on:
        return {"response": "Bluetooth off kar diya! 🔘", "action": "BLUETOOTH", "payload": {"state": False}}
    return {"response": "Bluetooth toggle kar diya! 🔵", "action": "BLUETOOTH", "payload": {"state": "toggle"}}


def handle_airplane_mode(q: str = "", query: str = "") -> dict:
    """Toggle airplane mode on/off."""
    q = (q or query).lower()
    has_on = bool(re.search(r'\b(on|enable)\b', q))
    has_off = bool(re.search(r'\b(off|disable)\b', q))
    if has_on and not has_off:
        return {"response": "Flight mode on kar diya! ✈️", "action": "AIRPLANE_MODE", "payload": {"state": True}}
    elif has_off and not has_on:
        return {"response": "Flight mode off kar diya! 📱", "action": "AIRPLANE_MODE", "payload": {"state": False}}
    return {"response": "Flight mode toggle kar diya! ✈️", "action": "AIRPLANE_MODE", "payload": {"state": "toggle"}}


def handle_home() -> dict:
    """Go to home screen."""
    return {"response": "Home screen pe ja rahe hain! 🏠", "action": "GO_HOME", "payload": {}}


def handle_camera() -> dict:
    """Open the camera app."""
    return {
        "response": "Camera khol raha hoon! 📸",
        "action": "OPEN_CAMERA",
        "payload": {
            "action": "android.intent.action.MAIN",
            "package": "com.android.camera2",
            "component": "com.android.camera2/.CameraActivity",
            "category": "android.intent.category.LAUNCHER",
        },
    }


def handle_search(query: str = "", q: str = "") -> dict:
    """Perform a web search via Android Chrome/browser intent.

    Args:
        query: Search query string.
        q:     Alternative query parameter name.

    Returns:
        Dict with response, action, and browser payload.
    """
    from urllib.parse import quote_plus
    from backend.core.and9_config import CHROME_PACKAGE, CHROME_COMPONENT

    search_term = (query or q).strip()
    if not search_term:
        return {
            "response": "Kya search karna hai? Topic batao. 🔍",
            "action": "SEARCH",
            "payload": {},
        }

    search_url = f"https://www.google.com/search?q={quote_plus(search_term)}"
    return {
        "response": f"Web pe '{search_term}' search kar raha hoon 🔍",
        "action": "SEARCH",
        "payload": {
            "action": "android.intent.action.VIEW",
            "package": CHROME_PACKAGE,
            "component": CHROME_COMPONENT,
            "data": search_url,
        },
    }


def handle_clipboard(keyword: str = "", q: str = "", query: str = "") -> dict:
    """Read from or write to clipboard.
    
    Args:
        keyword: 'read' or 'write'.
        q/query: Text to write if 'write' is chosen.
    """
    raw_query = (q or query).lower()
    text_to_write = ""
    
    # Try to extract what needs to be copied/written
    match = re.search(r'(?:copy|copy to clipboard|write|write to clipboard|clipboard main likho|copy karo)\s+(.*)', (q or query), re.IGNORECASE)
    if match:
        text_to_write = match.group(1).strip()
    else:
        # Check if keyword says copy
        if "copy" in raw_query or "write" in raw_query or "likho" in raw_query:
            text_to_write = (q or query).strip()

    if text_to_write:
        return {
            "response": f"Clipboard main write kar raha hoon: '{text_to_write}' 📋",
            "action": "CLIPBOARD_WRITE",
            "payload": {"text": text_to_write}
        }
    else:
        return {
            "response": "Clipboard read kar raha hoon 📋",
            "action": "CLIPBOARD_READ",
            "payload": {}
        }


def handle_media_control(action_type: str = "", q: str = "", query: str = "") -> dict:
    """Control media playback (play/pause, next, previous)."""
    raw_query = (action_type or q or query).lower()
    
    if any(kw in raw_query for kw in ["next", "agla", "aage"]):
        return {"response": "Next track play kar raha hoon ⏭️", "action": "MEDIA_NEXT", "payload": {}}
    if any(kw in raw_query for kw in ["prev", "previous", "piche", "pichla"]):
        return {"response": "Previous track play kar raha hoon ⏮️", "action": "MEDIA_PREV", "payload": {}}
    
    # Default is toggle play/pause
    return {"response": "Media play/pause toggle kar raha hoon ⏯️", "action": "MEDIA_PLAY_PAUSE", "payload": {}}


def handle_screen_state() -> dict:
    """Query the device screen state."""
    return {"response": "Screen state check kar raha hoon... 📱", "action": "SCREEN_STATE", "payload": {}}


def handle_notification_read() -> dict:
    """Read the last received notification."""
    return {"response": "Aapki aakhri notification check kar raha hoon... 🔔", "action": "READ_NOTIFICATIONS", "payload": {}}
