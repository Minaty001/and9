"""
AND9 — Android Executor (Phase 12 of Refactor).

Single entry point for all Android action execution.
All device actions must pass through this executor.
No action may be executed outside this file.

The executor:
    1. Looks up the action in the ActionRegistry
    2. Validates parameters
    3. Calls the registered handler function
    4. Returns a BrainResult-compatible dict

Every action type must be registered in action_registry.py
before it can be executed.
"""
import logging
from typing import Any, Dict, Optional

from app.and9.android.action_registry import (
    REGISTRY,
    get_action,
    is_whitelisted,
)

logger = logging.getLogger(__name__)


def execute(action_type: str, params: Dict[str, Any] = None,
            events_sys=None) -> Dict[str, Any]:
    """Execute an Android action through the registry.

    This is the single entry point for all Android actions.
    No action may be executed outside this function.

    Args:
        action_type: Registered action type (e.g., "call", "open_app").
        params: Parameters dict for the action handler.
        events_sys: Optional EventSystem (needed for reminders).

    Returns:
        Dict with keys: response, action, payload, metadata.
        If action is not registered, returns an error dict.

    Example:
        >>> execute("call", {"number": "+919999990001"})
        {'response': 'Call kar raha hoon... 📞', 'action': 'CALL', 'payload': {...}}

        >>> execute("open_camera", {})
        {'response': 'Camera khol raha hoon! 📸', 'action': 'OPEN_CAMERA', 'payload': {...}}
    """
    params = params or {}

    # Look up action in registry
    action_info = get_action(action_type)
    if not action_info:
        logger.error("Unknown action type: %s", action_type)
        return {
            "response": f"Action '{action_type}' samajh nahi aaya. 😕",
            "action": "ERROR",
            "payload": {},
        }

    handler_path = action_info.get("handler")
    if not handler_path:
        return {
            "response": "Action registered but no handler defined. 😕",
            "action": action_type.upper(),
            "payload": {},
        }

    # Import and call the handler
    try:
        return _call_handler(handler_path, action_type, params, events_sys)
    except Exception as e:
        logger.error("Handler '%s' failed: %s", handler_path, e, exc_info=True)
        return {
            "response": f"Action '{action_type}' failed: {str(e)} 😅",
            "action": "ERROR",
            "payload": {},
            "metadata": {"error": str(e)},
        }


def _call_handler(handler_path: str, action_type: str,
                  params: dict, events_sys=None) -> dict:
    """Dynamically import and call a handler function.

    Args:
        handler_path: Module path (e.g., "actions.call_actions.execute_call").
        action_type: Original action type for context.
        params: Parameters to pass to handler.
        events_sys: Optional EventSystem.

    Returns:
        Handler result dict.
    """
    # Parse handler path: "actions.call_actions.execute_call"
    parts = handler_path.split(".")
    if len(parts) < 2:
        raise ValueError(f"Invalid handler path: {handler_path}")

    module_path = "app.and9." + ".".join(parts[:-1])
    func_name = parts[-1]

    import importlib
    module = importlib.import_module(module_path)
    handler = getattr(module, func_name)

    # Build kwargs based on handler signature and params
    if action_type in ("set_alarm",):
        return handler(
            hour=params.get("hour", 7),
            minute=params.get("minute", 0),
            label=params.get("label"),
        )
    elif action_type == "set_timer":
        return handler(
            duration_seconds=params.get("duration_seconds", 60),
            label=params.get("label", "AND9 Timer"),
        )
    elif action_type == "set_reminder":
        return handler(
            trigger_at=params.get("trigger_at", {}),
            label=params.get("label", "AND9 Reminder"),
            events_sys=events_sys,
        )
    elif action_type == "call":
        return handler(
            contact=params.get("contact"),
            number=params.get("number"),
            action_type=params.get("action_type", "contact"),
        )
    elif action_type == "send_sms":
        return handler(
            contact=params.get("contact"),
            number=params.get("number"),
            message=params.get("message", ""),
        )
    elif action_type == "open_app":
        return handler(app_name=params.get("app_name", ""))
    elif action_type in ("youtube_search", "youtube_play"):
        if action_type == "youtube_search":
            from app.and9.actions.youtube_actions import execute_youtube_search
            return execute_youtube_search(query=params.get("query", ""))
        else:
            from app.and9.actions.youtube_actions import execute_youtube_play
            return execute_youtube_play(query=params.get("query", ""))
    elif action_type in ("flashlight", "wifi", "bluetooth", "airplane_mode"):
        from app.and9.actions.device_actions import (
            handle_flashlight, handle_wifi, handle_bluetooth, handle_airplane_mode
        )
        q = f"{action_type} {'on' if params.get('state') is True else 'off' if params.get('state') is False else ''}"
        handlers = {
            "flashlight": handle_flashlight,
            "wifi": handle_wifi,
            "bluetooth": handle_bluetooth,
            "airplane_mode": handle_airplane_mode,
        }
        return handlers[action_type](q)
    elif action_type == "open_camera":
        from app.and9.actions.device_actions import handle_camera
        return handle_camera()
    elif action_type == "go_home":
        from app.and9.actions.device_actions import handle_home
        return handle_home()
    elif action_type in ("volume_up", "volume_down", "volume_mute", "volume_max"):
        from app.and9.actions.device_actions import handle_volume
        keywords = {
            "volume_up": "up",
            "volume_down": "down",
            "volume_mute": "mute",
            "volume_max": "max",
        }
        return handle_volume(keywords.get(action_type, "up"))
    elif action_type == "close_app":
        from app.and9.actions.app_actions import execute_close_app
        return execute_close_app()
    else:
        # Generic call with kwargs
        return handler(**params)
