"""
AND9 — Action Registry (Phase 11 of Refactor).

Central registry of all supported Android actions. Every action
produced by AND9 is registered here with its metadata, handler
reference, required parameters, and the corresponding Android
intent type.

This is the single source of truth for the Android action
vocabulary. The Android client's ACTION_WHITELIST should be
derived from this registry.
"""
from typing import Dict, Any


# ── Action Registry ──────────────────────────────────────────────
# Maps action string → {handler, android_intent, description, params}
# handler: function reference or module path
# android_intent: Android Intent action constant (e.g., ACTION_CALL)
# description: Human-readable description
# params: List of required/optional parameter names
REGISTRY: Dict[str, Dict[str, Any]] = {
    # ── App Management ─────────────────────────────────────────
    "open_app": {
        "handler": "actions.app_actions.execute_open_app",
        "android_intent": "android.intent.action.MAIN",
        "description": "Open an Android app by package name",
        "params": ["app_name", "package"],
        "whitelisted": True,
    },
    "close_app": {
        "handler": "actions.app_actions.execute_close_app",
        "android_intent": "android.intent.action.MAIN",
        "description": "Close/go back from current app",
        "params": [],
        "whitelisted": True,
    },

    # ── Communication ──────────────────────────────────────────
    "call": {
        "handler": "actions.call_actions.execute_call",
        "android_intent": "android.intent.action.CALL",
        "description": "Initiate a phone call",
        "params": ["number"],
        "whitelisted": False,  # Dangerous — needs confirmation
    },
    "send_sms": {
        "handler": "actions.call_actions.execute_message",
        "android_intent": "android.intent.action.SENDTO",
        "description": "Send an SMS message",
        "params": ["number", "message"],
        "whitelisted": False,  # Dangerous — needs confirmation
    },

    # ── Device Control ─────────────────────────────────────────
    "flashlight": {
        "handler": "actions.device_actions.handle_flashlight",
        "android_intent": "CameraManager.setTorchMode",
        "description": "Toggle flashlight on/off",
        "params": ["state"],
        "whitelisted": True,
    },
    "volume_up": {
        "handler": "actions.device_actions.handle_volume",
        "android_intent": "AudioManager.adjustStreamVolume",
        "description": "Increase volume",
        "params": [],
        "whitelisted": True,
    },
    "volume_down": {
        "handler": "actions.device_actions.handle_volume",
        "android_intent": "AudioManager.adjustStreamVolume",
        "description": "Decrease volume",
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
    "wifi": {
        "handler": "actions.device_actions.handle_wifi",
        "android_intent": "Settings.ACTION_WIFI_SETTINGS",
        "description": "Toggle WiFi on/off",
        "params": ["state"],
        "whitelisted": True,
    },
    "bluetooth": {
        "handler": "actions.device_actions.handle_bluetooth",
        "android_intent": "Settings.ACTION_BLUETOOTH_SETTINGS",
        "description": "Toggle Bluetooth on/off",
        "params": ["state"],
        "whitelisted": True,
    },
    "airplane_mode": {
        "handler": "actions.device_actions.handle_airplane_mode",
        "android_intent": "Settings.ACTION_AIRPLANE_MODE_SETTINGS",
        "description": "Toggle airplane mode on/off",
        "params": ["state"],
        "whitelisted": True,
    },
    "go_home": {
        "handler": "actions.device_actions.handle_home",
        "android_intent": "ACTION_HOME",
        "description": "Go to home screen",
        "params": [],
        "whitelisted": True,
    },
    "open_camera": {
        "handler": "actions.device_actions.handle_camera",
        "android_intent": "MediaStore.INTENT_ACTION_STILL_IMAGE_CAMERA",
        "description": "Open the camera app",
        "params": [],
        "whitelisted": True,
    },

    # ── Media ──────────────────────────────────────────────────
    "youtube_search": {
        "handler": "actions.youtube_actions.execute_youtube_search",
        "android_intent": "android.intent.action.VIEW",
        "description": "Search YouTube",
        "params": ["query"],
        "whitelisted": True,
    },
    "youtube_play": {
        "handler": "actions.youtube_actions.execute_youtube_play",
        "android_intent": "android.intent.action.VIEW",
        "description": "Play video/song on YouTube",
        "params": ["query"],
        "whitelisted": True,
    },

    # ── Time ───────────────────────────────────────────────────
    "set_alarm": {
        "handler": "actions.alarm_actions.execute_set_alarm",
        "android_intent": "AlarmClock.ACTION_SET_ALARM",
        "description": "Set an alarm",
        "params": ["hour", "minute"],
        "whitelisted": True,
    },
    "set_timer": {
        "handler": "actions.timer_actions.execute_set_timer",
        "android_intent": "AlarmClock.ACTION_SET_TIMER",
        "description": "Set a countdown timer",
        "params": ["duration_seconds"],
        "whitelisted": True,
    },
    "set_reminder": {
        "handler": "actions.reminder_actions.execute_set_reminder",
        "android_intent": "CalendarContract.ACTION_EVENT_INSERT",
        "description": "Set a reminder",
        "params": ["trigger_at", "label"],
        "whitelisted": True,
    },

    # ── Emergency ──────────────────────────────────────────────
    "emergency": {
        "handler": None,  # Handled by device layer
        "android_intent": "android.intent.action.CALL_PRIVILEGED",
        "description": "Emergency SOS",
        "params": ["type"],
        "whitelisted": True,
    },
}


def get_action(action_type: str) -> Dict[str, Any]:
    """Get action metadata by action type string.

    Args:
        action_type: Action type (e.g., "call", "open_app").

    Returns:
        Action metadata dict or empty dict if not found.
    """
    return REGISTRY.get(action_type, {})


def is_whitelisted(action_type: str) -> bool:
    """Check if an action is whitelisted (safe to execute)."""
    info = REGISTRY.get(action_type, {})
    return info.get("whitelisted", False)


def list_registered_actions() -> list[str]:
    """Return sorted list of all registered action types."""
    return sorted(REGISTRY.keys())


def get_whitelist() -> list[str]:
    """Return list of whitelisted (safe) action types."""
    return [k for k, v in REGISTRY.items() if v.get("whitelisted")]
