"""
AND9 — Android Executor (Phase 14/17 Refactor).

Single entry point for all Android action execution.
All device actions must pass through this executor.
No action may be executed outside this file.

The executor:
    1. Looks up the action in the ActionRegistry
    2. Validates parameters
    3. Runs Chrome Firewall check (Phase 14)
    4. Calls the registered handler function
    5. Returns a BrainResult-compatible dict

Chrome Firewall Rule (Phase 17 — Final Rule):
    Only SEARCH/NEWS/WEB_LOOKUP may open Chrome.
    All device actions (CALL, ALARM, TIMER, YOUTUBE, etc.)
    are blocked from opening Chrome.
"""
import logging
from typing import Any, Dict

from backend.skills.android.action_registry import (
    get_action,
)
from backend.skills.android.chrome_firewall import assert_not_chrome, ChromeFirewallError

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
        result = _call_handler(handler_path, action_type, params, events_sys)

        # —— Chrome Firewall Check (Phase 14/17) —————————————————————
        # Every payload is checked AFTER execution, before returning.
        # If a non-search action tried to open Chrome, block it.
        payload = result.get("payload", {})
        try:
            assert_not_chrome(action_type, payload)
        except ChromeFirewallError as cfe:
            logger.error("Chrome firewall blocked action '%s': %s", action_type, cfe)
            return {
                "response": "This action cannot open Chrome. Only Search can. 🚫",
                "action": "CHROME_FIREWALL_BLOCKED",
                "payload": {"blocked_action": action_type, "reason": str(cfe)},
                "metadata": {"failure_reason": "chrome_firewall_blocked"},
            }

        return result

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
    """Dynamically route and execute via the Skill Registry.

    Args:
        handler_path: Module path (legacy, ignored).
        action_type: Original action type.
        params: Parameters to pass to handler.
        events_sys: Optional EventSystem.

    Returns:
        Handler result dict.
    """
    from backend.skills.android.skill_registry import execute_skill
    return execute_skill(action_type, params, events_sys)
