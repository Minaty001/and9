"""
AND9 — Centralized Action Constants & Registry.

Single source of truth for all action types, intent types, and
brain types. Every module in AND9 imports from here to ensure
consistent naming across the system.

This replaces scattered string literals across the old reflex files.
"""
from enum import Enum


class ActionType(str, Enum):
    """All supported device actions. These map 1:1 to Android intents.

    Every action produced by AND9 must be one of these constants.
    The Android client uses these strings in its ACTION_WHITELIST.
    """
    # ── App Management ─────────────────────────────────────────
    LAUNCH_APP = "open_app"
    CLOSE_APP = "close_app"

    # ── Communication ──────────────────────────────────────────
    CALL = "call"
    SEND_SMS = "send_sms"

    # ── Device Control ─────────────────────────────────────────
    FLASHLIGHT = "flashlight"
    FLASHLIGHT_ON = "flashlight_on"
    FLASHLIGHT_OFF = "flashlight_off"
    VOLUME_UP = "volume_up"
    VOLUME_DOWN = "volume_down"
    VOLUME_MUTE = "volume_mute"
    VOLUME_MAX = "volume_max"
    WIFI = "wifi"
    BLUETOOTH = "bluetooth"
    BLUETOOTH_SCAN = "bluetooth_scan"
    BLUETOOTH_PAIRED = "bluetooth_paired"
    AIRPLANE_MODE = "airplane_mode"
    GO_HOME = "go_home"
    OPEN_CAMERA = "open_camera"

    # ── Media ──────────────────────────────────────────────────
    YOUTUBE_SEARCH = "youtube_search"
    YOUTUBE_PLAY = "youtube_play"
    MUSIC_PLAY = "music_play"

    # ── Time ───────────────────────────────────────────────────
    SET_ALARM = "set_alarm"
    SET_TIMER = "set_timer"
    SET_REMINDER = "set_reminder"

    # ── Emergency ──────────────────────────────────────────────
    EMERGENCY = "emergency"

    # ── Fallback ───────────────────────────────────────────────
    SEARCH = "search"
    CHAT = "chat"
    UNKNOWN_APP = "unknown_app"
    ERROR = "error"


class ActionRegistry:
    """Maps action type → metadata for validation and documentation.

    Usage:
        info = ActionRegistry.get(ActionType.CALL)
        # → {"description": "Make a phone call", ...}
    """
    _registry = {
        ActionType.LAUNCH_APP: {
            "description": "Open an Android app by package name",
            "requires": ["app_name", "package"],
            "response_template": "{app_name} khol raha hoon... 📱",
        },
        ActionType.CLOSE_APP: {
            "description": "Close/go back from an app",
            "requires": [],
            "response_template": "App band kar raha hoon... 🔙",
        },
        ActionType.CALL: {
            "description": "Initiate a phone call",
            "requires": ["number"],
            "response_template": "Call kar raha hoon {display} ko... 📞",
        },
        ActionType.SEND_SMS: {
            "description": "Send an SMS message",
            "requires": ["number", "message"],
            "response_template": "Message bhej raha hoon... 💬",
        },
        ActionType.FLASHLIGHT: {
            "description": "Toggle flashlight on/off",
            "requires": ["state"],
            "response_template": "Flashlight {state_str} kar diya! 💡",
        },
        ActionType.VOLUME_UP: {
            "description": "Increase volume",
            "requires": [],
            "response_template": "Volume badha diya! 🔊",
        },
        ActionType.VOLUME_DOWN: {
            "description": "Decrease volume",
            "requires": [],
            "response_template": "Volume kam kar diya! 🔉",
        },
        ActionType.WIFI: {
            "description": "Toggle WiFi on/off",
            "requires": ["state"],
            "response_template": "WiFi {state_str} kar diya! 🌐",
        },
        ActionType.BLUETOOTH: {
            "description": "Toggle Bluetooth on/off",
            "requires": ["state"],
            "response_template": "Bluetooth {state_str} kar diya! 🔵",
        },
        ActionType.AIRPLANE_MODE: {
            "description": "Toggle airplane mode on/off",
            "requires": ["state"],
            "response_template": "Flight mode {state_str} kar diya! ✈️",
        },
        ActionType.GO_HOME: {
            "description": "Go to home screen",
            "requires": [],
            "response_template": "Home screen pe ja rahe hain! 🏠",
        },
        ActionType.OPEN_CAMERA: {
            "description": "Open the camera app",
            "requires": [],
            "response_template": "Camera khol raha hoon! 📸",
        },
        ActionType.YOUTUBE_SEARCH: {
            "description": "Search YouTube for a query",
            "requires": ["query"],
            "response_template": "YouTube pe '{query}' search kar raha hoon 🔍▶️",
        },
        ActionType.YOUTUBE_PLAY: {
            "description": "Play a video/song on YouTube",
            "requires": ["query"],
            "response_template": "Baja raha hoon '{query}' 🎵",
        },
        ActionType.SET_ALARM: {
            "description": "Set an alarm at a specific time",
            "requires": ["hour", "minute"],
            "response_template": "Alarm {display_time} ke liye set kar diya! ⏰",
        },
        ActionType.SET_TIMER: {
            "description": "Set a countdown timer",
            "requires": ["duration_seconds"],
            "response_template": "Timer {display_duration} ka set kar diya! ⏲️",
        },
        ActionType.SET_REMINDER: {
            "description": "Set a reminder with label",
            "requires": ["trigger_at", "label"],
            "response_template": "Reminder set kar diya! '{label}' ke liye ⏰",
        },
        ActionType.EMERGENCY: {
            "description": "Emergency SOS action",
            "requires": [],
            "response_template": "🚨 EMERGENCY! Help bhej raha hoon!",
        },
        ActionType.SEARCH: {
            "description": "Web search via Chrome/browser",
            "requires": ["query"],
            "response_template": "Web pe '{query}' search kar raha hoon 🔍",
        },
        ActionType.UNKNOWN_APP: {
            "description": "App name not recognized",
            "requires": ["app_name"],
            "response_template": "App nahi mila '{app_name}'. Kripya sahi naam boliye! 😕",
        },
    }

    @classmethod
    def get(cls, action: ActionType) -> dict:
        return cls._registry.get(action, {
            "description": "Unknown action",
            "requires": [],
            "response_template": "Kuch gadbad ho gayi! 😅",
        })

    @classmethod
    def list_actions(cls) -> list[dict]:
        return [
            {"action": a.value, **meta}
            for a, meta in cls._registry.items()
        ]

    @classmethod
    def validate_action(cls, action: str) -> bool:
        try:
            ActionType(action)
            return True
        except ValueError:
            return False
