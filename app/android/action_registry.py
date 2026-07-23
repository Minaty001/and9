"""
AND9 — Action Registry (Phase 12 Rebuild).

Central registry of all supported Android actions.
Every action produced by AND9 must be registered here.

Startup validation:
    validate_registry() is called at app startup.
    It asserts that every required action has a handler.
    Orphan actions (registered but unhandled) are logged as errors.

This is the single source of truth for AND9's action vocabulary.
The Android client's ACTION_WHITELIST must be derived from this registry.
"""
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


# ── Required Actions ─────────────────────────────────────────────
# Every action in this set MUST be registered in REGISTRY.
# Startup validation checks this at boot.
_REQUIRED_ACTIONS = frozenset({
    "open_app",
    "close_app",
    "call",
    "send_sms",
    "open_camera",
    "set_alarm",
    "set_timer",
    "set_reminder",
    "youtube_search",
    "youtube_play",
    "flashlight",
    "flashlight_on",
    "flashlight_off",
    "go_home",
    "volume_up",
    "volume_down",
    "volume_mute",
    "volume_max",
    "wifi",
    "bluetooth",
    "bluetooth_scan",
    "bluetooth_paired",
    "airplane_mode",
    "emergency",
    "search",

    # ── Accessibility ────────────────────────────────────────
    "describe_screen",
    "click_element",
    "type_text",
    "scroll",
    "list_elements",
    "get_current_app",
})


# ── Action Registry ──────────────────────────────────────────────
# action_type → {handler, android_intent, description, params, whitelisted}
REGISTRY: Dict[str, Dict[str, Any]] = {

    # ── App Management ─────────────────────────────────────────
    "open_app": {
        "handler": "actions.app_actions.execute_open_app",
        "android_intent": "android.intent.action.MAIN",
        "description": "Open an Android app by package name or label",
        "params": ["app_name"],
        "whitelisted": True,
    },
    "close_app": {
        "handler": "actions.app_actions.execute_close_app",
        "android_intent": "android.intent.action.MAIN",
        "description": "Close or go back from current app",
        "params": [],
        "whitelisted": True,
    },

    # ── Communication ──────────────────────────────────────────
    "call": {
        "handler": "actions.call_actions.execute_call",
        "android_intent": "android.intent.action.CALL",
        "description": "Initiate a phone call via ContactsContract lookup or direct dial",
        "params": ["contact_name", "number"],
        "whitelisted": False,  # Requires confirmation (dangerous)
    },
    "send_sms": {
        "handler": "actions.call_actions.execute_message",
        "android_intent": "android.intent.action.SENDTO",
        "description": "Send an SMS message",
        "params": ["contact_name", "number", "message"],
        "whitelisted": False,  # Requires confirmation
    },

    # ── Camera ─────────────────────────────────────────────────
    "open_camera": {
        "handler": "actions.device_actions.handle_camera",
        "android_intent": "android.media.action.STILL_IMAGE_CAMERA",
        "description": "Open the camera app",
        "params": [],
        "whitelisted": True,
    },

    # ── Time ───────────────────────────────────────────────────
    "set_alarm": {
        "handler": "actions.alarm_actions.execute_set_alarm",
        "android_intent": "AlarmClock.ACTION_SET_ALARM",
        "description": "Set an alarm at a specific time (absolute or relative)",
        "params": ["hour", "minute", "label", "query"],
        "whitelisted": True,
    },
    "set_timer": {
        "handler": "actions.timer_actions.execute_set_timer",
        "android_intent": "AlarmClock.ACTION_SET_TIMER",
        "description": "Set a countdown timer",
        "params": ["duration_seconds", "label", "query"],
        "whitelisted": True,
    },
    "set_reminder": {
        "handler": "actions.reminder_actions.execute_set_reminder",
        "android_intent": "AND9_INTERNAL",
        "description": "Set a reminder with SQLite persistence and background scheduler",
        "params": ["trigger_at", "label"],
        "whitelisted": True,
    },

    # ── Media ──────────────────────────────────────────────────
    "youtube_search": {
        "handler": "actions.youtube_actions.execute_youtube_search",
        "android_intent": "android.intent.action.VIEW",
        "description": "Search YouTube (never Chrome)",
        "params": ["query", "action"],
        "whitelisted": True,
        "chrome_blocked": True,
    },
    "youtube_play": {
        "handler": "actions.youtube_actions.execute_youtube_play",
        "android_intent": "android.intent.action.VIEW",
        "description": "Play video/song on YouTube (never Chrome)",
        "params": ["query"],
        "whitelisted": True,
        "chrome_blocked": True,
    },

    # ── Flashlight ─────────────────────────────────────────────
    "flashlight": {
        "handler": "actions.device_actions.handle_flashlight",
        "android_intent": "CameraManager.setTorchMode",
        "description": "Toggle flashlight (state=True/False/None)",
        "params": ["state"],
        "whitelisted": True,
    },
    "flashlight_on": {
        "handler": "actions.device_actions.handle_flashlight",
        "android_intent": "CameraManager.setTorchMode",
        "description": "Turn flashlight ON",
        "params": [],
        "whitelisted": True,
    },
    "flashlight_off": {
        "handler": "actions.device_actions.handle_flashlight",
        "android_intent": "CameraManager.setTorchMode",
        "description": "Turn flashlight OFF",
        "params": [],
        "whitelisted": True,
    },

    # ── Volume ─────────────────────────────────────────────────
    "volume_up": {
        "handler": "actions.device_actions.handle_volume",
        "android_intent": "AudioManager.adjustStreamVolume",
        "description": "Increase media volume",
        "params": [],
        "whitelisted": True,
    },
    "volume_down": {
        "handler": "actions.device_actions.handle_volume",
        "android_intent": "AudioManager.adjustStreamVolume",
        "description": "Decrease media volume",
        "params": [],
        "whitelisted": True,
    },
    "volume_mute": {
        "handler": "actions.device_actions.handle_volume",
        "android_intent": "AudioManager.adjustStreamVolume",
        "description": "Mute device",
        "params": [],
        "whitelisted": True,
    },
    "volume_max": {
        "handler": "actions.device_actions.handle_volume",
        "android_intent": "AudioManager.adjustStreamVolume",
        "description": "Set volume to maximum",
        "params": [],
        "whitelisted": True,
    },

    # ── Connectivity ───────────────────────────────────────────
    "wifi": {
        "handler": "actions.device_actions.handle_wifi",
        "android_intent": "Settings.ACTION_WIFI_SETTINGS",
        "description": "Toggle WiFi on/off",
        "params": ["state"],
        "whitelisted": True,
    },
    "bluetooth": {
        "handler": "actions.device_actions.handle_bluetooth",
        "android_intent": "BluetoothAdapter.enable/disable",
        "description": "Toggle Bluetooth on/off",
        "params": ["state"],
        "whitelisted": True,
    },
    "bluetooth_scan": {
        "handler": "actions.bluetooth_actions.handle_bluetooth_scan",
        "android_intent": "BluetoothAdapter.startDiscovery",
        "description": "Scan for nearby Bluetooth devices",
        "params": [],
        "whitelisted": True,
    },
    "bluetooth_paired": {
        "handler": "actions.bluetooth_actions.handle_bluetooth_paired",
        "android_intent": "BluetoothAdapter.getBondedDevices",
        "description": "List paired Bluetooth devices",
        "params": [],
        "whitelisted": True,
    },
    "airplane_mode": {
        "handler": "actions.device_actions.handle_airplane_mode",
        "android_intent": "Settings.ACTION_AIRPLANE_MODE_SETTINGS",
        "description": "Toggle airplane mode",
        "params": ["state"],
        "whitelisted": True,
    },

    # ── Navigation ─────────────────────────────────────────────
    "go_home": {
        "handler": "actions.device_actions.handle_home",
        "android_intent": "Intent.ACTION_MAIN + CATEGORY_HOME",
        "description": "Go to Android home screen",
        "params": [],
        "whitelisted": True,
    },

    # ── Emergency ──────────────────────────────────────────────
    "emergency": {
        "handler": None,  # Handled directly by Android service
        "android_intent": "android.intent.action.CALL_PRIVILEGED",
        "description": "Emergency SOS — priority 1",
        "params": ["type"],
        "whitelisted": True,
    },

    # ── Search (lowest priority — Chrome allowed here only) ────
    "search": {
        "handler": "actions.device_actions.handle_search",
        "android_intent": "android.intent.action.VIEW",
        "description": "Web search — lowest priority, Chrome allowed here",
        "params": ["query"],
        "whitelisted": True,
        "chrome_allowed": True,
    },
    "news": {
        "handler": "actions.device_actions.handle_search",
        "android_intent": "android.intent.action.VIEW",
        "description": "News search — Chrome allowed",
        "params": ["query"],
        "whitelisted": True,
        "chrome_allowed": True,
    },
    "web_lookup": {
        "handler": "actions.device_actions.handle_search",
        "android_intent": "android.intent.action.VIEW",
        "description": "General web lookup — Chrome allowed",
        "params": ["query"],
        "whitelisted": True,
        "chrome_allowed": True,
    },

    # ── Accessibility ─────────────────────────────────────────
    "describe_screen": {
        "handler": "actions.accessibility_actions.describe_screen",
        "android_intent": "AND9_INTERNAL",
        "description": "Describe the current screen contents",
        "params": ["query"],
        "whitelisted": True,
    },
    "click_element": {
        "handler": "actions.accessibility_actions.click_element",
        "android_intent": "AND9_INTERNAL",
        "description": "Click a UI element by text or description",
        "params": ["query", "text"],
        "whitelisted": True,
    },
    "type_text": {
        "handler": "actions.accessibility_actions.type_text",
        "android_intent": "AND9_INTERNAL",
        "description": "Type text into an input field",
        "params": ["query", "text", "field"],
        "whitelisted": True,
    },
    "scroll": {
        "handler": "actions.accessibility_actions.scroll",
        "android_intent": "AND9_INTERNAL",
        "description": "Scroll the current screen in a direction",
        "params": ["query", "direction"],
        "whitelisted": True,
    },
    "list_elements": {
        "handler": "actions.accessibility_actions.list_elements",
        "android_intent": "AND9_INTERNAL",
        "description": "List all actionable UI elements on screen",
        "params": ["query"],
        "whitelisted": True,
    },
    "get_current_app": {
        "handler": "actions.accessibility_actions.get_current_app",
        "android_intent": "AND9_INTERNAL",
        "description": "Get the current foreground app package",
        "params": ["query"],
        "whitelisted": True,
    },

    # ── Chat ───────────────────────────────────────────────────
    "chat": {
        "handler": "actions.device_actions.handle_chat",
        "android_intent": "AND9_INTERNAL",
        "description": "General conversation response",
        "params": ["query"],
        "whitelisted": True,
    },
}


# ── Registry API ─────────────────────────────────────────────────

def get_action(action_type: str) -> Dict[str, Any]:
    """Get action metadata by action type string.

    Args:
        action_type: e.g., "call", "open_app", "set_alarm".

    Returns:
        Action metadata dict, or empty dict if not found.
    """
    return REGISTRY.get(action_type, {})


def is_whitelisted(action_type: str) -> bool:
    """Check if an action is whitelisted (safe to auto-execute)."""
    return REGISTRY.get(action_type, {}).get("whitelisted", False)


def is_chrome_allowed(action_type: str) -> bool:
    """Check if this action is permitted to open Chrome."""
    return REGISTRY.get(action_type, {}).get("chrome_allowed", False)


def is_chrome_blocked(action_type: str) -> bool:
    """Check if this action explicitly blocks Chrome."""
    return REGISTRY.get(action_type, {}).get("chrome_blocked", False)


def list_registered_actions() -> List[str]:
    """Return sorted list of all registered action types."""
    return sorted(REGISTRY.keys())


def get_whitelist() -> List[str]:
    """Return list of whitelisted (safe) action types."""
    return [k for k, v in REGISTRY.items() if v.get("whitelisted")]


def validate_registry() -> None:
    """Assert that all required actions are registered.

    Called at application startup. Raises AssertionError if any
    required action is missing from REGISTRY.

    Also logs warnings for any registered actions that have no handler.
    """
    registered = set(REGISTRY.keys())

    # Check all required actions exist
    missing = _REQUIRED_ACTIONS - registered
    assert not missing, (
        f"AND9 Registry FATAL: Required actions not registered: {sorted(missing)}\n"
        f"Add them to app/android/action_registry.py before startup."
    )

    # Warn about handler-less registrations (except emergency)
    for action, meta in REGISTRY.items():
        if meta.get("handler") is None and action != "emergency":
            logger.warning(
                "Action '%s' has no handler registered. "
                "It will fail at execution time.", action
            )

    logger.info(
        "AND9 Action Registry validated: %d actions registered, %d required — all OK.",
        len(registered), len(_REQUIRED_ACTIONS)
    )
