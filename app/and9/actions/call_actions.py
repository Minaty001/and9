"""
AND9 — Call Actions (Phase 5 of Refactor).

Executes phone calls with contact resolution. Always resolves
contact names to phone numbers before dialing — never dials
string names directly.

Supports:
    call mummy          → resolve "mummy" → dial number
    call amit kumar     → resolve "amit kumar" → dial number
    dial 9876543210     → dial number directly
    phone +919876543210 → dial number directly
"""
import logging
import re
from typing import Optional

from app.and9.contacts.resolver import ContactsResolver
from app.skills.intent_executor import IntentExecutor

logger = logging.getLogger(__name__)


def execute_call(contact: Optional[str] = None,
                 number: Optional[str] = None,
                 action_type: str = "contact") -> dict:
    """Execute a phone call via IntentExecutor.

    Args:
        contact: Contact name to resolve (e.g., "mummy", "amit kumar").
        number: Direct phone number to dial.
        action_type: "contact" or "dial".

    Returns:
        Dict with response, action, payload, and optional metadata.
    """
    # If we have a number already, use it directly
    if number:
        try:
            result = IntentExecutor.make_call(number)
        except Exception as e:
            logger.error("IntentExecutor.make_call failed: %s", e)
            result = None

        return {
            "response": f"Call kar raha hoon {number}... 📞",
            "action": "CALL",
            "payload": result or _build_call_payload(number),
            "metadata": {"number": number},
        }

    # Resolve contact name
    if contact:
        resolver = ContactsResolver()
        resolved = resolver.resolve(contact)

        if resolved and resolved.get("number"):
            number = resolved["number"]
            display = resolved["display"]
            try:
                result = IntentExecutor.make_call(number)
            except Exception as e:
                logger.error("IntentExecutor.make_call failed: %s", e)
                result = None

            return {
                "response": f"Call kar raha hoon {display} ko... 📞",
                "action": "CALL",
                "payload": result or _build_call_payload(number),
                "metadata": {"contact": resolved},
            }
        elif resolved and not resolved.get("number"):
            return {
                "response": f"{resolved['display']} ka number nahi hai mere paas. Kya aap number bata sakte hain? 📋",
                "action": "CALL",
                "payload": {"action": "android.intent.action.CALL", "data": ""},
                "metadata": {"contact": resolved},
            }

    return {
        "response": "Kise call karna hai? Kripya naam ya number boliye! 📞",
        "action": "CALL",
        "payload": {"action": "android.intent.action.CALL", "data": ""},
    }


def _build_call_payload(number: str) -> dict:
    """Build a standard Android CALL intent payload."""
    return {
        "action": "android.intent.action.CALL",
        "data": f"tel:{number}",
    }


def execute_message(contact: Optional[str] = None,
                    number: Optional[str] = None,
                    message: str = "") -> dict:
    """Execute sending an SMS via Android intent.

    Args:
        contact: Contact name to resolve.
        number: Direct phone number.
        message: Message text content.

    Returns:
        Dict with response, action, payload.
    """
    if number:
        payload = {
            "action": "android.intent.action.SENDTO",
            "data": f"sms:{number}",
            "extra_text": message or "Hello!",
        }
        return {
            "response": f"Message bhej raha hoon {number} ko... 💬",
            "action": "SEND_SMS",
            "payload": payload,
            "metadata": {"number": number, "message": message},
        }

    if contact:
        resolver = ContactsResolver()
        resolved = resolver.resolve(contact)
        if resolved and resolved.get("number"):
            payload = {
                "action": "android.intent.action.SENDTO",
                "data": f"sms:{resolved['number']}",
                "extra_text": message or "Hello!",
            }
            return {
                "response": f"Message bhej raha hoon {resolved['display']} ko... 💬",
                "action": "SEND_SMS",
                "payload": payload,
                "metadata": {"contact": resolved, "message": message},
            }

    return {
        "response": "Kise message bhejna hai? Naam boliye! 💬",
        "action": "SEND_SMS",
        "payload": {},
    }
