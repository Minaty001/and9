"""
app/brain/subconscious.py — Fast reflex brain for AND9

Handles all instant device commands without LLM calls.
If it can handle the intent, it executes immediately.

Intent mapping to handler:
  open_app        -> app_actions.launch_app()
  close_app       -> app_actions.close_app()
  play_music      -> youtube_actions.play_music() / spotify
  set_alarm       -> alarm_actions.set_alarm()
  set_timer       -> timer_actions.set_timer()
  set_reminder    -> reminder_actions.set_reminder()
  make_call       -> call_actions.make_call()
  volume_up       -> device_actions.volume_up()
  volume_down     -> device_actions.volume_down()
  wifi_on/off     -> device_actions.toggle_wifi()
  bluetooth_on/off-> bluetooth_actions.toggle_bluetooth()
  flashlight_on/off -> device_actions.toggle_flashlight()
  brightness      -> device_actions.set_brightness()
  camera_open     -> app_actions.launch_camera()
"""

import logging
import time

logger = logging.getLogger(__name__)

# All intents that can be handled without LLM
SUBCONSCIOUS_INTENTS = {
    "open_app", "close_app", "launch_app",
    "play_music", "pause_music", "stop_music", "next_track", "prev_track",
    "set_alarm", "cancel_alarm",
    "set_timer", "cancel_timer",
    "set_reminder",
    "make_call", "end_call",
    "volume_up", "volume_down", "mute", "unmute",
    "brightness_up", "brightness_down", "set_brightness",
    "wifi_on", "wifi_off",
    "bluetooth_on", "bluetooth_off",
    "flashlight_on", "flashlight_off",
    "camera_open", "gallery_open",
    "send_sms",
    "contacts_open",
    "calculator_open",
    "settings_open",
    "go_home",
    "go_back",
    "take_screenshot",
}


class SubconsciousBrain:
    """
    Instant, rule-based handler.
    No LLM. No network. Response within 300 ms.
    """

    def can_handle(self, intent: str) -> bool:
        return intent in SUBCONSCIOUS_INTENTS

    def execute(self, intent: str, entities: dict,
                user_id: str = "default") -> dict:
        """
        Execute a device action.
        Returns: {"success": bool, "response": str, "action": str, "latency_ms": int}
        """
        t_start = time.time()
        try:
            result = self._dispatch(intent, entities)
            latency_ms = int((time.time() - t_start) * 1000)
            return {
                "success": result.get("success", True),
                "response": result.get("response", "Done."),
                "action": intent,
                "latency_ms": latency_ms,
                "brain": "subconscious",
            }
        except Exception as e:
            logger.error(f"SubconsciousBrain: failed to execute '{intent}': {e}")
            return {
                "success": False,
                "response": f"Could not execute {intent}. Please try again.",
                "action": intent,
                "latency_ms": int((time.time() - t_start) * 1000),
                "brain": "subconscious",
                "error": str(e),
            }

    def _dispatch(self, intent: str, entities: dict) -> dict:
        """Map intent to the correct android action handler."""
        from app.android.actions import (
            app_actions, alarm_actions, timer_actions,
            reminder_actions, call_actions, device_actions,
            bluetooth_actions, youtube_actions
        )

        dispatch_map = {
            "open_app":       lambda: app_actions.launch_app(entities.get("app", "")),
            "play_music":     lambda: youtube_actions.play_music(entities.get("query", "")),
            "set_alarm":      lambda: alarm_actions.set_alarm(entities),
            "set_timer":      lambda: timer_actions.set_timer(entities),
            "set_reminder":   lambda: reminder_actions.set_reminder(entities),
            "make_call":       lambda: call_actions.make_call(entities.get("contact", "")),
            "volume_up":      lambda: device_actions.volume_up(),
            "volume_down":      lambda: device_actions.volume_down(),
            "wifi_on":        lambda: device_actions.toggle_wifi(True),
            "wifi_off":       lambda: device_actions.toggle_wifi(False),
            "bluetooth_on":   lambda: bluetooth_actions.toggle_bluetooth(True),
            "bluetooth_off":  lambda: bluetooth_actions.toggle_bluetooth(False),
            "flashlight_on":  lambda: device_actions.toggle_flashlight(True),
            "flashlight_off": lambda: device_actions.toggle_flashlight(False),
            "camera_open":    lambda: app_actions.launch_camera(),
            "go_home":        lambda: device_actions.go_home(),
            "take_screenshot":lambda: device_actions.take_screenshot(),
        }

        handler = dispatch_map.get(intent)
        if handler:
            return handler() or {"success": True, "response": "Done."}
        return {"success": False, "response": f"No handler for intent: {intent}"}