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
    """Default argument mapper: passes parameters through unchanged.

    Args:
        params: Input parameters dict.
        events_sys: EventSystem reference (unused).

    Returns:
        The params dict unchanged.
    """
    return params

def _alarm_mapper(params: dict, events_sys: Any) -> dict:
    """Map parameters for set_alarm skill.

    Args:
        params: Parameters dict with optional keys hour, minute, label.
        events_sys: EventSystem reference (unused).

    Returns:
        Dict with hour, minute, and label keys for alarm execution.
    """
    return {
        "hour": params.get("hour", 7),
        "minute": params.get("minute", 0),
        "label": params.get("label"),
    }

def _timer_mapper(params: dict, events_sys: Any) -> dict:
    """Map parameters for set_timer skill.

    Args:
        params: Parameters dict with optional keys duration_seconds, label.
        events_sys: EventSystem reference (unused).

    Returns:
        Dict with duration_seconds and label keys for timer execution.
    """
    return {
        "duration_seconds": params.get("duration_seconds", 60),
        "label": params.get("label", "AND9 Timer"),
    }

def _reminder_mapper(params: dict, events_sys: Any) -> dict:
    """Map parameters for set_reminder skill, forwarding the events system.

    Args:
        params: Parameters dict with optional keys trigger_at, label.
        events_sys: EventSystem reference passed through for reminder scheduling.

    Returns:
        Dict with trigger_at, label, and events_sys keys.
    """
    return {
        "trigger_at": params.get("trigger_at", {}),
        "label": params.get("label", "AND9 Reminder"),
        "events_sys": events_sys,
    }

def _call_mapper(params: dict, events_sys: Any) -> dict:
    """Map parameters for call skill.

    Args:
        params: Parameters dict with optional keys contact_name, number, action_type.
        events_sys: EventSystem reference (unused).

    Returns:
        Dict with contact_name, number, and action_type keys for call execution.
    """
    return {
        "contact_name": params.get("contact_name"),
        "number": params.get("number"),
        "action_type": params.get("action_type", "contact"),
    }

def _sms_mapper(params: dict, events_sys: Any) -> dict:
    """Map parameters for send_sms skill.

    Args:
        params: Parameters dict with optional keys contact_name, number, message.
        events_sys: EventSystem reference (unused).

    Returns:
        Dict with contact_name, number, and message keys for SMS execution.
    """
    return {
        "contact_name": params.get("contact_name"),
        "number": params.get("number"),
        "message": params.get("message", ""),
    }

def _app_mapper(params: dict, events_sys: Any) -> dict:
    """Map parameters for open_app skill.

    Args:
        params: Parameters dict with optional key app_name.
        events_sys: EventSystem reference (unused).

    Returns:
        Dict with app_name key for app launch execution.
    """
    return {
        "app_name": params.get("app_name", "")
    }

def _youtube_search_mapper(params: dict, events_sys: Any) -> dict:
    """Map parameters for youtube_search / youtube_play skills.

    Args:
        params: Parameters dict with optional key query.
        events_sys: EventSystem reference (unused).

    Returns:
        Dict with query key for YouTube search execution.
    """
    return {"query": params.get("query", "")}

def _device_toggle_mapper(params: dict, events_sys: Any) -> dict:
    """Map parameters for device toggle actions (wifi/bluetooth/airplane_mode).

    Converts boolean state to 'on'/'off' string, or empty string if state is None.

    Args:
        params: Parameters dict with optional key state (bool or None).
        events_sys: EventSystem reference (unused).

    Returns:
        Dict with a 'q' key containing the toggle command string.
    """
    state = params.get("state")
    return {"q": "on" if state is True else "off" if state is False else ""}

# Registering skills
register_skill("set_alarm", "app.and9.actions.alarm_actions", "execute_set_alarm", _alarm_mapper)
register_skill("set_timer", "app.and9.actions.timer_actions", "execute_set_timer", _timer_mapper)
register_skill("set_reminder", "app.and9.actions.reminder_actions", "execute_set_reminder", _reminder_mapper)
register_skill("call", "app.and9.actions.call_actions", "execute_call", _call_mapper)
register_skill("send_sms", "app.and9.actions.call_actions", "execute_message", _sms_mapper)
register_skill("open_app", "app.and9.actions.app_actions", "execute_open_app", _app_mapper)
register_skill("close_app", "app.and9.actions.app_actions", "execute_close_app", lambda p, e: {})
register_skill("youtube_search", "app.and9.actions.youtube_actions", "execute_youtube_search", _youtube_search_mapper)
register_skill("youtube_play", "app.and9.actions.youtube_actions", "execute_youtube_play", _youtube_search_mapper)
register_skill("flashlight", "app.and9.actions.device_actions", "handle_flashlight", lambda p, e: {"q": f"flashlight {'on' if p.get('state') is True else 'off' if p.get('state') is False else ''}"})
register_skill("flashlight_on", "app.and9.actions.device_actions", "handle_flashlight", lambda p, e: {"q": "flashlight on"})
register_skill("flashlight_off", "app.and9.actions.device_actions", "handle_flashlight", lambda p, e: {"q": "flashlight off"})
register_skill("wifi", "app.and9.actions.device_actions", "handle_wifi", lambda p, e: {"q": f"wifi {'on' if p.get('state') is True else 'off' if p.get('state') is False else ''}"})
register_skill("bluetooth", "app.and9.actions.device_actions", "handle_bluetooth", lambda p, e: {"q": f"bluetooth {'on' if p.get('state') is True else 'off' if p.get('state') is False else ''}"})
register_skill("airplane_mode", "app.and9.actions.device_actions", "handle_airplane_mode", lambda p, e: {"q": f"airplane_mode {'on' if p.get('state') is True else 'off' if p.get('state') is False else ''}"})
register_skill("open_camera", "app.and9.actions.device_actions", "handle_camera", lambda p, e: {})
register_skill("go_home", "app.and9.actions.device_actions", "handle_home", lambda p, e: {})
register_skill("volume_up", "app.and9.actions.device_actions", "handle_volume", lambda p, e: {"keyword": "up"})
register_skill("volume_down", "app.and9.actions.device_actions", "handle_volume", lambda p, e: {"keyword": "down"})
register_skill("volume_mute", "app.and9.actions.device_actions", "handle_volume", lambda p, e: {"keyword": "mute"})
register_skill("volume_max", "app.and9.actions.device_actions", "handle_volume", lambda p, e: {"keyword": "max"})
register_skill("search", "app.and9.actions.device_actions", "handle_search", lambda p, e: {"query": p.get("query", "")})


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
        # Fallback for generic actions
        logger.warning("Action %s not in Skill Registry, falling back to dynamic import.", action_type)
        return {}

    module_path, func_name, arg_mapper = _SKILL_REGISTRY[action_type]
    
    import importlib
    module = importlib.import_module(module_path)
    handler = getattr(module, func_name)
    
    kwargs = arg_mapper(params, events_sys)
    return handler(**kwargs)

def get_registered_skills():
    """Return a list of all registered action type keys.

    Returns:
        List of action type strings registered in the skill registry.
    """
    return list(_SKILL_REGISTRY.keys())
