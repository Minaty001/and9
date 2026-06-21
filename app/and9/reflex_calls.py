"""
AND9 — Reflex Call & Message Handlers.

Manages phone call and SMS intent generation with Hindi contact name
resolution. Maps common Hindi relationship terms and nicknames to
phone numbers for quick dialing.

Contact resolution is currently backed by a hardcoded dictionary.
In production, this should be replaced with Android ContactsContract
content provider queries for dynamic contact lookup.

Supported contact categories:
  - Family: mummy, papa, bhai, didi, bhabhi, chacha, chachi, tauji,
            tai, nana, nani, dadi, dada
  - Friends: saif, amit, rahul, priya, ankit, neha
  - Work: boss, sachin, amit kumar
  - Generic: friend, dost
"""
import logging
import re
from typing import Optional, Dict, Tuple

logger = logging.getLogger(__name__)


# ── Hardcoded Contact Database ───────────────────────────────────
# Maps Hindi relationships and nicknames to phone numbers.
# In production, replace with Android ContactsContract query.
_CONTACTS: Dict[str, str] = {
    # ── Family ──────────────────────────────────────────────────
    "mummy": "+919999990001",
    "maa": "+919999990001",
    "mamma": "+919999990001",
    "papa": "+919999990002",
    "pita": "+919999990002",
    "bhai": "+919999990003",
    "bhaiya": "+919999990003",
    "didi": "+919999990004",
    "didi ji": "+919999990004",
    "bhabhi": "+919999990005",
    "bhabhi ji": "+919999990005",
    "chacha": "+919999990006",
    "chacha ji": "+919999990006",
    "chachi": "+919999990007",
    "chachi ji": "+919999990007",
    "tauji": "+919999990008",
    "tau": "+919999990008",
    "tai": "+919999990009",
    "tai ji": "+919999990009",
    "nana": "+919999990010",
    "nana ji": "+919999990010",
    "nani": "+919999990011",
    "nani ji": "+919999990011",
    "dada": "+919999990012",
    "dada ji": "+919999990012",
    "dadi": "+919999990013",
    "dadi ji": "+919999990013",

    # ── Friends ─────────────────────────────────────────────────
    "saif": "+919999990021",
    "saif ali": "+919999990021",
    "amit": "+919999990022",
    "amit ji": "+919999990022",
    "rahul": "+919999990023",
    "rahul bhai": "+919999990023",
    "priya": "+919999990024",
    "priya didi": "+919999990024",
    "ankit": "+919999990025",
    "ankit bhai": "+919999990025",
    "neha": "+919999990026",
    "neha didi": "+919999990026",
    "sachin": "+919999990027",
    "sachin bhai": "+919999990027",

    # ── Work ────────────────────────────────────────────────────
    "boss": "+919999990031",
    "sir": "+919999990031",
    "bisesh": "+919999990031",

    # ── Generic ─────────────────────────────────────────────────
    "friend": "+919999990041",
    "dost": "+919999990041",
    "dost ji": "+919999990041",
}

# Map of name → (number, display_name) for metadata
_CONTACT_INFO: Dict[str, Tuple[str, str]] = {
    name: (num, name.title())
    for name, num in _CONTACTS.items()
}


def resolve_contact(name: str) -> Optional[Dict[str, str]]:
    """Fuzzy-match a contact name against the contact database.

    Supports partial matching — if "saif" is typed and "saif ali"
    is in the database, it will match.

    Args:
        name: Contact name extracted from the query.

    Returns:
        Dict with keys "name", "number", and "display" for the
        matched contact. Returns None if no match found.
    """
    name_lower = name.lower().strip()

    # Exact match
    if name_lower in _CONTACTS:
        number = _CONTACTS[name_lower]
        return {
            "name": name_lower,
            "number": number,
            "display": name_lower.title(),
        }

    # Partial: check if any contact name contains the query
    for contact_name, number in _CONTACTS.items():
        if name_lower in contact_name or contact_name in name_lower:
            return {
                "name": contact_name,
                "number": number,
                "display": contact_name.title(),
            }

    # No match — check if it looks like a custom name
    # (not a number, not empty)
    if len(name_lower) > 1 and not re.match(r'^\+?\d+$', name_lower):
        return {
            "name": name_lower,
            "number": "",
            "display": name_lower.title(),
        }

    return None


def handle_call(query: str) -> dict:
    """Generate a CALL intent from a normalized query.

    Extracts the target (contact name or phone number) and prepares
    an Android ACTION_CALL intent.

    Priority: Phone number > Contact name.

    Args:
        query: Normalized user query (e.g., "call mummy" or
               "call 9876543210").

    Returns:
        Response dict with CALL action and tel: URI payload.
    """
    # Try to extract a phone number
    number = extract_phone_number(query)
    if number:
        return {
            "response": f"Call kar raha hoon {number}... 📞",
            "action": "CALL",
            "payload": {
                "action": "android.intent.action.CALL",
                "data": f"tel:{number}",
            },
        }

    # Fall back to contact resolution
    contact_name = extract_contact_name(query)
    if contact_name:
        contact = resolve_contact(contact_name)
        if contact and contact["number"]:
            return {
                "response": f"Call kar raha hoon {contact['display']} ko... 📞",
                "action": "CALL",
                "payload": {
                    "action": "android.intent.action.CALL",
                    "data": f"tel:{contact['number']}",
                },
                "metadata": {"contact": contact},
            }
        elif contact:
            return {
                "response": f"{contact['display']} ka number nahi hai mere paas. "
                            f"Kya aap number bata sakte hain? 📋",
                "action": "CALL",
                "payload": {"action": "android.intent.action.CALL", "data": ""},
                "metadata": {"contact": contact},
            }

    return {
        "response": "Kise call karna hai? Kripya naam ya number boliye! 📞",
        "action": "CALL",
        "payload": {"action": "android.intent.action.CALL", "data": ""},
    }


def handle_message(query: str) -> dict:
    """Generate a SEND_SMS intent from a normalized query.

    Extracts the recipient (contact name or phone number) and
    message text. Tries to extract message content after keywords
    like "message", "text", "say", "bolo".

    Args:
        query: Normalized user query (e.g., "message mummy mein
               ghar aa raha hoon").

    Returns:
        Response dict with SEND_SMS action and sms: URI payload.
    """
    # Try to extract phone number
    number = extract_phone_number(query)
    message = extract_message_text(query)

    if number:
        return {
            "response": f"Message bhej raha hoon {number} ko... 💬",
            "action": "SEND_SMS",
            "payload": {
                "action": "android.intent.action.SENDTO",
                "data": f"sms:{number}",
                "extra_text": message or "Hello!",
            },
            "metadata": {"number": number, "message": message},
        }

    # Contact-based messaging
    contact_name = extract_contact_name(query)
    if contact_name:
        contact = resolve_contact(contact_name)
        if contact and contact["number"]:
            return {
                "response": f"Message bhej raha hoon {contact['display']} ko... 💬",
                "action": "SEND_SMS",
                "payload": {
                    "action": "android.intent.action.SENDTO",
                    "data": f"sms:{contact['number']}",
                    "extra_text": message or "Hello!",
                },
                "metadata": {
                    "contact": contact,
                    "message": message or "Hello!",
                },
            }
        elif contact:
            return {
                "response": f"{contact['display']} ka number nahi hai. "
                            f"Kya aap number bata sakte hain? 📋",
                "action": "SEND_SMS",
                "payload": {},
                "metadata": {"contact": contact},
            }

    return {
        "response": "Kise message bhejna hai? Naam boliye! 💬",
        "action": "SEND_SMS",
        "payload": {},
    }


def extract_phone_number(query: str) -> Optional[str]:
    """Extract a phone number from query text.

    Args:
        query: Normalized query string.

    Returns:
        Clean phone number (digits only, with leading +), or None.
    """
    m = re.search(r'(\+?\d[\d\s\-().]{7,15}\d)', query)
    if m:
        cleaned = re.sub(r'[\s\-().]', '', m.group(1))
        if len(cleaned) >= 8:
            return cleaned
    return None


def extract_contact_name(query: str) -> Optional[str]:
    """Extract a contact name from a call/message command.

    Handles patterns like:
      "call mummy ko"         → "mummy"
      "call amit kumar"       → "amit kumar"
      "message rahul"         → "rahul"
      "call 9876543210"       → None (looks like a number)

    Args:
        query: Normalized query.

    Returns:
        Contact name string, or None if the target looks like a
        phone number.
    """
    m = re.search(
        r'\b(?:call|dial|phone|message|text|msg|sms)\s+'
        r'(.+?)(?:\s+(?:ko|ke|ka|par|pe))?$',
        query
    )
    if m:
        name = m.group(1).strip()
        # Exclude if it's a phone number
        if not re.match(r'^\+?\d+$', name):
            return name
    return None


def extract_message_text(query: str) -> Optional[str]:
    """Extract the message body from a messaging command.

    Tries to extract text that appears after keywords like
    "message", "text", "say", "bolo", "kaho".

    Args:
        query: Normalized query.

    Returns:
        Message text string, or None if no message content is
        detected.
    """
    # Pattern: "message <contact> <text>"
    # After removing the action word and contact, the rest is message
    m = re.search(
        r'\b(?:message|text|sms|msg|say|bolo|kaho)\s+'
        r'(?:\w+\s+)?(.*)',
        query
    )
    if m:
        text = m.group(1).strip()
        if len(text) > 2:
            return text
    return None
