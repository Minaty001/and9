"""
AND9 — Contact Resolver (Phase 3 Rebuild).

Uses Android's ContactsContract.CommonDataKinds.Phone API for contact lookup.
The Python backend does NOT store or hardcode any phone numbers.

Flow:
    call mummy
        ↓
    ContactsResolver.resolve("mummy")
        ↓
    Returns: {"lookup_required": True, "contact_name": "mummy"}
        ↓
    Android client queries ContactsContract
        ↓
    Number found → dial
    Multiple matches → ask user: "Which contact?"
    Not found → inform user

The backend only handles routing logic.
All actual contact data lives on the Android device.
"""
import re
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

# Phone number pattern
_PHONE_PATTERN = re.compile(r'^\+?\d[\d\s\-()\+]{6,18}$')


class ContactsResolver:
    """Resolve contact names to lookup requests for the Android client.

    The resolver no longer holds any phone numbers or contact data.
    It acts as a validator/classifier for the contact field:
      - Direct numbers → return dial payload immediately
      - Names → return lookup_required payload for Android to resolve
        via ContactsContract.CommonDataKinds.Phone

    Usage:
        resolver = ContactsResolver()
        result = resolver.resolve("mummy")
        # → {"lookup_required": True, "contact_name": "mummy",
        #    "display": "Mummy", "number": None}

        result = resolver.resolve("9876543210")
        # → {"lookup_required": False, "number": "9876543210",
        #    "display": "9876543210", "contact_name": None}
    """

    def resolve(self, name: str) -> Optional[Dict]:
        """Resolve a contact name or phone number.

        For phone numbers: returns a direct-dial payload.
        For names: returns a lookup_required payload for Android.

        Args:
            name: Contact name (e.g., "mummy", "amit kumar")
                  or phone number (e.g., "+919876543210", "9876543210").

        Returns:
            Dict with resolution result, or None if name is empty.

        Examples:
            >>> r = ContactsResolver()
            >>> r.resolve("mummy")
            {'lookup_required': True, 'contact_name': 'mummy',
             'display': 'Mummy', 'number': None, 'action_type': 'contact'}

            >>> r.resolve("+919876543210")
            {'lookup_required': False, 'contact_name': None,
             'number': '+919876543210', 'display': '+919876543210',
             'action_type': 'dial'}
        """
        if not name or not name.strip():
            return None

        name_clean = name.strip()

        # ── Direct phone number ───────────────────────────────────
        if _PHONE_PATTERN.match(name_clean):
            return {
                "lookup_required": False,
                "contact_name": None,
                "number": name_clean,
                "display": name_clean,
                "action_type": "dial",
            }

        # ── Contact name → Android must resolve ───────────────────
        # Strip relational suffixes that are not part of the name
        clean_name = self._clean_name(name_clean)

        return {
            "lookup_required": True,
            "contact_name": clean_name.lower(),
            "display": clean_name.title(),
            "number": None,
            "action_type": "contact",
        }

    def _clean_name(self, name: str) -> str:
        """Strip trailing noise words from a contact name.

        Examples:
            "mummy ko" → "mummy"
            "amit kumar bhai" → "amit kumar bhai"  (preserved, might be real)
        """
        # Strip trailing "ko", "se", "ka", "ki" (Hinglish postpositions)
        name = re.sub(r'\s+(?:ko|se|ka|ki|ke|ne)\s*$', '', name, flags=re.IGNORECASE)
        return name.strip()

    def is_number(self, value: str) -> bool:
        """Check if a string looks like a phone number."""
        return bool(_PHONE_PATTERN.match(value.strip()))

    def build_lookup_payload(self, contact_name: str) -> dict:
        """Build the payload sent to Android for contact resolution.

        Android receives this and queries ContactsContract:
            ContactsContract.CommonDataKinds.Phone
                WHERE display_name LIKE '%{contact_name}%'

        Returns:
            Payload dict for the Android action layer.
        """
        return {
            "action": "CONTACTS_LOOKUP",
            "query": contact_name.lower().strip(),
            "android_api": "ContactsContract.CommonDataKinds.Phone",
        }
