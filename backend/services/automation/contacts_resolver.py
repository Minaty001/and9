"""
AND9 — Contact Resolver (Phase 3 Rebuild + Contacts Enhancement).

Resolves contact names by first checking the local ContactsDB,
then falling back to Android's ContactsContract.CommonDataKinds.Phone API.

Flow:
    call mummy
        ↓
    ContactsResolver.resolve("mummy")
        ↓
    1. Check local ContactsDB for "mummy"
       ├─ Found: return number directly (no Android lookup needed)
       └─ Not found: fall back to Android ContactsContract

    Android client queries ContactsContract
        ↓
    Number found → dial
    Multiple matches → ask user: "Which contact?"
    Not found → inform user
"""
import re
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

# Phone number pattern
_PHONE_PATTERN = re.compile(r'^\+?\d[\d\s\-()\+]{6,18}$')


class ContactsResolver:
    """Resolve contact names to phone numbers.

    First checks the local ContactsDB for a match. If not found locally,
    returns a lookup_required payload for the Android client to resolve
    via ContactsContract.CommonDataKinds.Phone.

    Usage:
        resolver = ContactsResolver()
        result = resolver.resolve("mummy")
        # → {"lookup_required": True, "contact_name": "mummy",
        #    "display": "Mummy", "number": None}
        # OR if found locally:
        # → {"lookup_required": False, "contact_name": "mummy",
        #    "display": "Mummy", "number": "+919876543210"}

        result = resolver.resolve("9876543210")
        # → {"lookup_required": False, "number": "9876543210",
        #    "display": "9876543210", "contact_name": None}
    """

    def __init__(self):
        self._db = None

    def _get_db(self):
        """Lazy import and instantiate the local ContactsDB."""
        if self._db is None:
            try:
                from backend.services.contacts.contacts_db import ContactsDB
                self._db = ContactsDB()
            except Exception as e:
                logger.warning("Local ContactsDB not available: %s", e)
        return self._db

    def resolve(self, name: str) -> Optional[Dict]:
        """Resolve a contact name or phone number.

        For phone numbers: returns a direct-dial payload.
        For names: checks local ContactsDB first; if not found,
                   returns a lookup_required payload for Android.

        Args:
            name: Contact name (e.g., "mummy", "amit kumar")
                  or phone number (e.g., "+919876543210", "9876543210").

        Returns:
            Dict with resolution result, or None if name is empty.
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

        # ── Strip relational suffixes that are not part of the name ──
        clean_name = self._clean_name(name_clean)

        # ── Check local ContactsDB first ──────────────────────────
        db = self._get_db()
        if db:
            try:
                local_contact = db.get_contact_by_name(clean_name)
                if not local_contact:
                    # Try fuzzy search
                    results = db.search_contacts(clean_name, limit=1)
                    if results:
                        local_contact = results[0]

                if local_contact and local_contact.get("phone"):
                    number = local_contact["phone"]
                    logger.info(
                        "Local DB resolved '%s' → %s", clean_name, number
                    )
                    return {
                        "lookup_required": False,
                        "contact_name": local_contact["name"],
                        "number": number,
                        "display": local_contact["name"],
                        "action_type": "contact",
                        "source": "local_db",
                    }
            except Exception as e:
                logger.error("Local DB lookup failed for '%s': %s", clean_name, e)

        # ── Not found locally → Android must resolve ───────────────
        return {
            "lookup_required": True,
            "contact_name": clean_name.lower(),
            "display": clean_name.title(),
            "number": None,
            "action_type": "contact",
            "source": "android_contacts",
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
