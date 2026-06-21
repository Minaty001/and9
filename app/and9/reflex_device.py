"""
AND9 — Reflex Device Control Handlers.

Stateless handler functions for Android device features: flashlight,
volume, WiFi, Bluetooth, airplane mode, home screen, and camera.
Each function takes the normalized query and returns a response dict
with Hinglish feedback text, an action constant, and an Android
Intent payload that the device layer can execute.

All handlers return dicts with keys:
  - response: Human-readable feedback (Hinglish with emoji)
  - action:   Action type constant (e.g., "FLASHLIGHT", "VOLUME_UP")
  - payload:  Android Intent or action parameters dict

Note: Actual device execution (e.g., turning on the flashlight via
Android API) happens in the device layer — these handlers only
prepare the intent structure. On Termux or non-Android environments,
only the response text is meaningful.
"""
import logging
import re

logger = logging.getLogger(__name__)


def _has_on(query: str) -> bool:
    """Check if the query contains an ON/enable keyword.

    Args:
        query: Normalized lowercase query.

    Returns:
        True if ON intent is detected.
    """
    return bool(re.search(r'\b(on|enable|start|kholo|chalu)\b', query))


def _has_off(query: str) -> bool:
    """Check if the query contains an OFF/disable keyword.

    Args:
        query: Normalized lowercase query.

    Returns:
        True if OFF intent is detected.
    """
    return bool(re.search(r'\b(off|disable|stop|band|bnd)\b', query))


def handle_flashlight(query: str) -> dict:
    """Toggle flashlight (torch) on or off based on query context.

    Args:
        query: Normalized user query.

    Returns:
        Response dict with FLASHLIGHT action and state payload.
    """
    if _has_on(query) and not _has_off(query):
        return {
            "response": "Flashlight on kar diya! 💡",
            "action": "FLASHLIGHT",
            "payload": {"state": True},
        }
    elif _has_off(query) and not _has_on(query):
        return {
            "response": "Flashlight off kar diya! 🌙",
            "action": "FLASHLIGHT",
            "payload": {"state": False},
        }
    else:
        # Ambiguous or just "flashlight" — toggle
        return {
            "response": "Flashlight toggle kar diya! 💡",
            "action": "FLASHLIGHT",
            "payload": {"state": "toggle"},
        }


def handle_volume(query: str) -> dict:
    """Adjust device volume based on query context.

    Supports up, down, mute, unmute, and max. Defaults to up if
    direction cannot be determined.

    Args:
        query: Normalized user query.

    Returns:
        Response dict with appropriate VOLUME action.
    """
    q = query.lower()

    if any(kw in q for kw in ["mute", "silent", "zero", "0"]):
        return {
            "response": "Phone mute kar diya! 🔇",
            "action": "VOLUME_MUTE",
            "payload": {"level": 0},
        }
    elif any(kw in q for kw in ["unmute", "sound on"]):
        return {
            "response": "Sound wapas on kar diya! 🔊",
            "action": "VOLUME_UNMUTE",
            "payload": {"level": 7},
        }
    elif any(kw in q for kw in ["max", "full", "100", "highest"]):
        return {
            "response": "Volume full kar diya! 🔊📢",
            "action": "VOLUME_MAX",
            "payload": {"level": 15},
        }
    elif any(kw in q for kw in ["up", "badhao", "higher", "louder", "increase"]):
        return {
            "response": "Volume badha diya! 🔊",
            "action": "VOLUME_UP",
            "payload": {"delta": 2},
        }
    elif any(kw in q for kw in ["down", "kam", "lower", "decrease", "less"]):
        return {
            "response": "Volume kam kar diya! 🔉",
            "action": "VOLUME_DOWN",
            "payload": {"delta": 2},
        }
    else:
        # Default: volume up
        return {
            "response": "Volume badha diya! 🔊",
            "action": "VOLUME_UP",
            "payload": {"delta": 2},
        }


def handle_wifi(query: str) -> dict:
    """Toggle WiFi on or off based on query context.

    Args:
        query: Normalized user query.

    Returns:
        Response dict with WIFI action and state payload.
    """
    if _has_on(query) and not _has_off(query):
        return {
            "response": "WiFi on kar diya! 🌐",
            "action": "WIFI",
            "payload": {"state": True},
        }
    elif _has_off(query) and not _has_on(query):
        return {
            "response": "WiFi off kar diya! 📶",
            "action": "WIFI",
            "payload": {"state": False},
        }
    else:
        # Just "wifi" → toggle
        return {
            "response": "WiFi toggle kar diya! 🌐",
            "action": "WIFI",
            "payload": {"state": "toggle"},
        }


def handle_bluetooth(query: str) -> dict:
    """Toggle Bluetooth on or off based on query context.

    Args:
        query: Normalized user query.

    Returns:
        Response dict with BLUETOOTH action and state payload.
    """
    if _has_on(query) and not _has_off(query):
        return {
            "response": "Bluetooth on kar diya! 🔵",
            "action": "BLUETOOTH",
            "payload": {"state": True},
        }
    elif _has_off(query) and not _has_on(query):
        return {
            "response": "Bluetooth off kar diya! 🔘",
            "action": "BLUETOOTH",
            "payload": {"state": False},
        }
    else:
        return {
            "response": "Bluetooth toggle kar diya! 🔵",
            "action": "BLUETOOTH",
            "payload": {"state": "toggle"},
        }


def handle_airplane_mode(query: str) -> dict:
    """Toggle airplane/flight mode on or off based on query context.

    Args:
        query: Normalized user query.

    Returns:
        Response dict with AIRPLANE_MODE action and state payload.
    """
    if _has_on(query) and not _has_off(query):
        return {
            "response": "Flight mode on kar diya! ✈️",
            "action": "AIRPLANE_MODE",
            "payload": {"state": True},
        }
    elif _has_off(query) and not _has_on(query):
        return {
            "response": "Flight mode off kar diya! 📱",
            "action": "AIRPLANE_MODE",
            "payload": {"state": False},
        }
    else:
        return {
            "response": "Flight mode toggle kar diya! ✈️",
            "action": "AIRPLANE_MODE",
            "payload": {"state": "toggle"},
        }


def handle_home() -> dict:
    """Go to the Android home screen.

    Returns:
        Response dict with GO_HOME action.
    """
    return {
        "response": "Home screen pe ja rahe hain! 🏠",
        "action": "GO_HOME",
        "payload": {},
    }


def handle_camera() -> dict:
    """Open the device camera.

    Returns:
        Response dict with LAUNCH_APP action pointing to camera.
    """
    return {
        "response": "Camera khol raha hoon! 📸",
        "action": "LAUNCH_APP",
        "payload": {
            "action": "android.intent.action.MAIN",
            "package": "com.android.camera2",
            "component": "com.android.camera2/.CameraActivity",
            "category": "android.intent.category.LAUNCHER",
        },
    }
