"""
AND9 — Intent Validator (Priority 7).

Validates extracted parameters for specific intents before execution.
Ensures that we don't try to execute an action (like setting an alarm or timer)
if critical parameters (like the time or duration) are missing from the query.

If validation fails, returns False and a helpful conversational prompt asking
the user for the missing information.
"""
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


def validate_intent(intent_name: str, params: dict, action_type: str = "") -> Tuple[bool, str]:
    """Validate if the extracted parameters are sufficient for the intent.

    Args:
        intent_name: The detected intent string (e.g., 'alarm', 'timer', 'call').
        params: The extracted entities dict.
        action_type: The detected action type string (e.g., 'set_reminder', 'list_reminders').

    Returns:
        (is_valid, error_message):
            is_valid: True if OK to execute, False if missing required params.
            error_message: User-facing prompt if invalid (empty string if valid).
    """
    if not intent_name or intent_name == "chat":
        return True, ""

    if intent_name == "alarm":
        # Alarm needs a valid time (either hour/minute for absolute, or seconds for relative)
        if params.get("type") == "unknown" or (params.get("hour") is None and params.get("seconds") is None):
            return False, "Alarm kitne baje ka lagana hai? Time batao please. ⏰"

    elif intent_name == "timer":
        # Timer needs a duration
        if not params.get("duration_seconds"):
            return False, "Timer kitne time ka lagana hai? Jaise '5 minutes' ya '10 seconds'. ⏱️"

    elif intent_name == "reminder":
        # Reminder needs a valid time only when setting a reminder
        if action_type == "set_reminder":
            trigger_at = params.get("trigger_at", {})
            if trigger_at.get("type") == "unknown" or (trigger_at.get("hour") is None and trigger_at.get("seconds") is None):
                return False, "Reminder ka time samajh nahi aaya. Kab yaad dilana hai? 📅"

    elif intent_name == "call":
        # Call needs a target (number or contact)
        if not params.get("number") and not params.get("contact_name"):
            return False, "Kisko call karna hai? Naam ya number bataiye. 📞"

    elif intent_name == "message":
        # Message needs a target
        if not params.get("number") and not params.get("contact_name"):
            return False, "Kisko message bhejna hai? Naam bataiye. ✉️"

    elif intent_name == "open_app":
        # App open needs an app name
        if not params.get("app_name"):
            return False, "Kaunsi app kholni hai? Naam bataiye. 📱"

    elif intent_name == "search":
        # Search needs a query
        if not params.get("query"):
            return False, "Kya search karna hai? Topic bataiye. 🔍"

    return True, ""
