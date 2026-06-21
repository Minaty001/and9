"""
AND9 — Call Actions (Phase 11 Rebuild).

Executes phone calls via Android ContactsContract + direct dial.

Flow for contact names:
    call mummy
        ↓
    extract_entities("call", query) → contact_name="mummy"
        ↓
    ContactsResolver.resolve("mummy")
        ↓
    lookup_required: True → emit CONTACTS_LOOKUP to Android
        ↓
    Android: ContactsContract.CommonDataKinds.Phone query
        ↓
    Number found → CALL intent with tel:number
    Multiple matches → Android asks user
    Not found → inform user

Supported commands (all patterns in command_dictionary.py):
    call mummy / call papa / call bhai / call amit kumar
    mummy ko call karo / amit ko phone lagao
    phone lagao mummy / dial mummy
    call 9876543210 / phone +919876543210 / dial 9876543210
"""
import logging
import re
from typing import Optional

from app.and9.contacts.resolver import ContactsResolver

logger = logging.getLogger(__name__)

_resolver = ContactsResolver()

# Android intent constants
_ACTION_CALL = "android.intent.action.CALL"
_ACTION_DIAL = "android.intent.action.DIAL"
_ACTION_SENDTO = "android.intent.action.SENDTO"
_ACTION_CONTACTS_LOOKUP = "CONTACTS_LOOKUP"


def execute_call(
    contact: Optional[str] = None,
    number: Optional[str] = None,
    contact_name: Optional[str] = None,
    action_type: str = "contact",
    lookup_required: bool = False,
    **kwargs,
) -> dict:
    """Execute a phone call or contact lookup.

    Accepts both old-style (contact=, number=) and new entity_extractor
    style (contact_name=, lookup_required=) parameters.

    Args:
        contact:         Contact name (old style, backwards compat).
        number:          Phone number for direct dial.
        contact_name:    Contact name (new style from entity_extractor).
        action_type:     "contact" | "dial".
        lookup_required: If True, Android must resolve via ContactsContract.

    Returns:
        Dict with response, action, payload.
    """
    # ── Normalize parameters (support both old and new style) ─────
    effective_name = contact_name or contact
    effective_number = number

    # ── Direct number dial ────────────────────────────────────────
    if effective_number and _resolver.is_number(effective_number):
        clean_number = re.sub(r'[\s\-()]', '', effective_number)
        return {
            "response": f"Call kar raha hoon {effective_number}... 📞",
            "action": "CALL",
            "payload": {
                "action": _ACTION_CALL,
                "data": f"tel:{clean_number}",
            },
            "metadata": {"number": clean_number, "type": "direct_dial"},
        }

    # ── Contact name → Android resolves via ContactsContract ──────
    if effective_name:
        resolved = _resolver.resolve(effective_name)

        if resolved is None:
            return {
                "response": "Kise call karna hai? Kripya naam ya number boliye! 📞",
                "action": "CALL",
                "payload": {},
            }

        if resolved.get("action_type") == "dial":
            # Name turned out to be a number
            return execute_call(number=resolved["number"])

        if resolved.get("lookup_required"):
            # Emit CONTACTS_LOOKUP — Android resolves
            contact_disp = resolved["display"]
            lookup_payload = _resolver.build_lookup_payload(resolved["contact_name"])
            return {
                "response": f"{contact_disp} ko call kar raha hoon... 📞",
                "action": "CALL",
                "payload": {
                    "action": _ACTION_CONTACTS_LOOKUP,
                    "contact_query": resolved["contact_name"],
                    "display": contact_disp,
                    "on_resolve": {
                        "action": _ACTION_CALL,
                        "data_template": "tel:{number}",
                    },
                    "android_api": "ContactsContract.CommonDataKinds.Phone",
                },
                "metadata": {"contact_name": resolved["contact_name"]},
            }

    # ── No name and no number ─────────────────────────────────────
    return {
        "response": "Kise call karna hai? Kripya naam ya number boliye! 📞",
        "action": "CALL",
        "payload": {},
    }


def execute_message(
    contact: Optional[str] = None,
    number: Optional[str] = None,
    contact_name: Optional[str] = None,
    message: str = "",
    lookup_required: bool = False,
    **kwargs,
) -> dict:
    """Send an SMS message via Android intent.

    For contact names → emits CONTACTS_LOOKUP first.
    For direct numbers → sends immediately.

    Args:
        contact:      Contact name (backwards compat).
        number:       Direct phone number.
        contact_name: Contact name (new style).
        message:      SMS text content.

    Returns:
        Dict with response, action, payload.
    """
    effective_name = contact_name or contact
    effective_number = number

    # ── Direct number SMS ─────────────────────────────────────────
    if effective_number and _resolver.is_number(effective_number):
        clean_number = re.sub(r'[\s\-()]', '', effective_number)
        return {
            "response": f"Message bhej raha hoon {effective_number} ko... 💬",
            "action": "SEND_SMS",
            "payload": {
                "action": _ACTION_SENDTO,
                "data": f"sms:{clean_number}",
                "extra_text": message or "",
            },
            "metadata": {"number": clean_number, "message": message},
        }

    # ── Contact name SMS ─────────────────────────────────────────
    if effective_name:
        resolved = _resolver.resolve(effective_name)

        if resolved and resolved.get("lookup_required"):
            contact_disp = resolved["display"]
            return {
                "response": f"{contact_disp} ko message bhej raha hoon... 💬",
                "action": "SEND_SMS",
                "payload": {
                    "action": _ACTION_CONTACTS_LOOKUP,
                    "contact_query": resolved["contact_name"],
                    "display": contact_disp,
                    "on_resolve": {
                        "action": _ACTION_SENDTO,
                        "data_template": "sms:{number}",
                        "extra_text": message or "",
                    },
                    "android_api": "ContactsContract.CommonDataKinds.Phone",
                },
                "metadata": {"contact_name": resolved["contact_name"], "message": message},
            }

    return {
        "response": "Kise message bhejna hai? Naam boliye! 💬",
        "action": "SEND_SMS",
        "payload": {},
    }
