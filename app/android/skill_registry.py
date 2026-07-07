"""
AND9 — Skill Registry System (Priority 10).

Replaces the hardcoded if/elif chains in android_executor.py.
Dynamically routes Android actions to their specific handler arguments.
"""
import logging
from typing import Callable, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# Action Type -> (Module Path, Function Name, Arg Mapper)
# Arg Mapper takes (params, events_sys) and returns kwargs dict
_SKILL_REGISTRY: Dict[str, Tuple[str, str, Callable]] = {}

def register_skill(action_type: str, module_path: str, func_name: str, arg_mapper: Callable):
    """Register a skill handler and its argument mapper."""
    _SKILL_REGISTRY[action_type] = (module_path, func_name, arg_mapper)

def _default_mapper(params: dict, events_sys: Any) -> dict:
    return params

def _alarm_mapper(params: dict, events_sys: Any) -> dict:
    return {
        "hour": params.get("hour", 7),
        "minute": params.get("minute", 0),
        "label": params.get("label"),
    }

def _timer_mapper(params: dict, events_sys: Any) -> dict:
    return {
        "duration_seconds": params.get("duration_seconds", 60),
        "label": params.get("label", "AND9 Timer"),
    }

def _reminder_mapper(params: dict, events_sys: Any) -> dict:
    return {
        "trigger_at": params.get("trigger_at", {}),
        "label": params.get("label", "AND9 Reminder"),
        "events_sys": events_sys,
    }

def _call_mapper(params: dict, events_sys: Any) -> dict:
    return {
        "contact_name": params.get("contact_name"),
        "number": params.get("number"),
        "action_type": params.get("action_type", "contact"),
    }

def _sms_mapper(params: dict, events_sys: Any) -> dict:
    return {
        "contact_name": params.get("contact_name"),
        "number": params.get("number"),
        "message": params.get("message", ""),
    }

def _app_mapper(params: dict, events_sys: Any) -> dict:
    return {
        "app_name": params.get("app_name", "")
    }

def _youtube_search_mapper(params: dict, events_sys: Any) -> dict:
    return {"query": params.get("query", "")}

def _device_toggle_mapper(params: dict, events_sys: Any) -> dict:
    state = params.get("state")
    return {"q": "on" if state is True else "off" if state is False else ""}

# Registering skills
register_skill("set_alarm", "app.android.actions.alarm_actions", "execute_set_alarm", _alarm_mapper)
register_skill("set_timer", "app.android.actions.timer_actions", "execute_set_timer", _timer_mapper)
register_skill("set_reminder", "app.android.actions.reminder_actions", "execute_set_reminder", _reminder_mapper)
register_skill("call", "app.android.actions.call_actions", "execute_call", _call_mapper)
register_skill("send_sms", "app.android.actions.call_actions", "execute_message", _sms_mapper)
register_skill("open_app", "app.android.actions.app_actions", "execute_open_app", _app_mapper)
register_skill("close_app", "app.android.actions.app_actions", "execute_close_app", lambda p, e: {})
register_skill("youtube_search", "app.android.actions.youtube_actions", "execute_youtube_search", _youtube_search_mapper)
register_skill("youtube_play", "app.android.actions.youtube_actions", "execute_youtube_play", _youtube_search_mapper)
register_skill("flashlight", "app.android.actions.device_actions", "handle_flashlight", lambda p, e: {"query": f"flashlight {'on' if p.get('state') is True else 'off' if p.get('state') is False else ''}"})
register_skill("flashlight_on", "app.android.actions.device_actions", "handle_flashlight", lambda p, e: {"query": "flashlight on"})
register_skill("flashlight_off", "app.android.actions.device_actions", "handle_flashlight", lambda p, e: {"query": "flashlight off"})
register_skill("wifi", "app.android.actions.device_actions", "handle_wifi", lambda p, e: {"query": f"wifi {'on' if p.get('state') is True else 'off' if p.get('state') is False else ''}"})
register_skill("bluetooth", "app.android.actions.device_actions", "handle_bluetooth", lambda p, e: {"query": f"bluetooth {'on' if p.get('state') is True else 'off' if p.get('state') is False else ''}"})
register_skill("bluetooth_scan", "app.android.actions.bluetooth_actions", "handle_bluetooth_scan", lambda p, e: {"query": "bluetooth scan"})
register_skill("bluetooth_paired", "app.android.actions.bluetooth_actions", "handle_bluetooth_paired", lambda p, e: {"query": "bluetooth paired"})
register_skill("airplane_mode", "app.android.actions.device_actions", "handle_airplane_mode", lambda p, e: {"query": f"airplane_mode {'on' if p.get('state') is True else 'off' if p.get('state') is False else ''}"})
register_skill("open_camera", "app.android.actions.device_actions", "handle_camera", lambda p, e: {})
register_skill("go_home", "app.android.actions.device_actions", "handle_home", lambda p, e: {})
register_skill("volume_up", "app.android.actions.device_actions", "handle_volume", lambda p, e: {"query": "up"})
register_skill("volume_down", "app.android.actions.device_actions", "handle_volume", lambda p, e: {"query": "down"})
register_skill("volume_mute", "app.android.actions.device_actions", "handle_volume", lambda p, e: {"query": "mute"})
register_skill("volume_max", "app.android.actions.device_actions", "handle_volume", lambda p, e: {"query": "max"})
register_skill("chat", "app.android.actions.device_actions", "handle_chat", lambda p, e: {"query": p.get("query", "")})


def execute_skill(action_type: str, params: dict, events_sys: Any = None) -> dict:
    """Execute a skill from the registry.

    Args:
        action_type: Action type string.
        params: Parameters from the router.
        events_sys: EventSystem reference.

    Returns:
        Handler response dict.
    """
    if action_type not in _SKILL_REGISTRY:
        # Fallback for generic actions — return error dict instead of {}
        # so the caller doesn't mistake it for a successful execution.
        logger.warning("Action %s not in Skill Registry.", action_type)
        return {
            "response": f"Action '{action_type}' not configured in skill registry. 😕",
            "action": "ERROR",
            "payload": {},
            "metadata": {"failure_reason": "not_in_skill_registry"},
        }

    module_path, func_name, arg_mapper = _SKILL_REGISTRY[action_type]
    
    import importlib
    module = importlib.import_module(module_path)
    handler = getattr(module, func_name)
    
    kwargs = arg_mapper(params, events_sys)
    return handler(**kwargs)

def get_registered_skills():
    return list(_SKILL_REGISTRY.keys())
