"""
AND9 — Contact Resolver (Phase 4 of Refactor).

Contact lookup system designed for Android's ContactsContract API.
Currently uses a hardcoded contact database as fallback for when
the device-side content provider is not accessible.

In production:
    Use ContactsContract.CommonDataKinds.Phone via Android API
    to query the device's contact database dynamically.

The resolver supports:
    - Exact name matching
    - Partial/fuzzy name matching
    - Relationship terms (mummy, papa, bhai, etc.)
"""
import logging
import re
from typing import Optional, Dict

logger = logging.getLogger(__name__)


# ── Hardcoded Contact Database ───────────────────────────────────
# Maps Hindi relationship terms and nicknames to phone numbers.
# Format: "name": "+91XXXXXXXXXX"
# Replace with ContactsContract query in production.
_CONTACTS: Dict[str, str] = {
    # Family
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

    # Friends
    "saif": "+919999990021",
    "saif ali": "+919999990021",
    "amit": "+919999990022",
    "amit kumar": "+919999990022",
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

    # Work
    "boss": "+919999990031",
    "sir": "+919999990031",

    # Generic
    "friend": "+919999990041",
    "dost": "+919999990041",
}


class ContactsResolver:
    """Resolve contact names to phone numbers.

    Supports exact, prefix, and fuzzy name matching against
    the contact database.

    Usage:
        resolver = ContactsResolver()
        result = resolver.resolve("mummy")
        # → {"name": "mummy", "number": "+919999990001", "display": "Mummy"}
    """

    def __init__(self):
        self._contacts = _CONTACTS

    def resolve(self, name: str) -> Optional[Dict[str, str]]:
        """Resolve a contact name to phone number and display info.

        Args:
            name: Contact name (e.g., "mummy", "saif ali", "+919876543210").

        Returns:
            Dict with keys: name, number, display.
            If name is a phone number, returns it directly.
            Returns None if no match found.
        """
        if not name or not name.strip():
            return None

        name_clean = name.lower().strip()

        # If it's already a phone number, return as-is
        if re.match(r'^\+?\d{7,15}$', name_clean):
            return {
                "name": name_clean,
                "number": name_clean,
                "display": name_clean,
            }

        # Exact match
        if name_clean in self._contacts:
            number = self._contacts[name_clean]
            return {
                "name": name_clean,
                "number": number,
                "display": name_clean.title(),
            }

        # Partial match — check if query contains a known name
        # or vice versa
        for contact_name, number in self._contacts.items():
            if name_clean in contact_name or contact_name in name_clean:
                return {
                    "name": contact_name,
                    "number": number,
                    "display": contact_name.title(),
                }

        # Custom name (not in database, not a number)
        if len(name_clean) > 1:
            return {
                "name": name_clean,
                "number": "",
                "display": name_clean.title(),
            }

        return None

    def list_contacts(self) -> Dict[str, str]:
        """Return the full contact database."""
        return dict(self._contacts)

    def add_contact(self, name: str, number: str) -> bool:
        """Add a contact to the database (in-memory only).

        Args:
            name: Contact name.
            number: Phone number.

        Returns:
            True if added successfully.
        """
        name_key = name.lower().strip()
        if name_key and number:
            self._contacts[name_key] = number
            return True
        return False
