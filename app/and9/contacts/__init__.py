"""AND9 — Contacts Resolver.

Resolves contact names (including Hinglish names like "mummy", "papa")
to phone numbers using fuzzy matching.
"""

from .resolver import ContactsResolver

__all__ = ["ContactsResolver"]
