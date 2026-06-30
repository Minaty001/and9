"""
AND9 — Contacts Management Actions.

Standalone handler functions for contact management skills
(list, add, delete, search contacts) that wrap the local ContactsDB.
"""
import logging
from typing import Optional

from app.services.contacts.contacts_db import ContactsDB

logger = logging.getLogger(__name__)

_db_instance = None


def _get_db() -> ContactsDB:
    """Get or create the singleton ContactsDB instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = ContactsDB()
    return _db_instance


def execute_list_contacts() -> dict:
    """List all local contacts.
    
    Returns:
        {"success": bool, "contacts": list, "count": int}
    """
    try:
        db = _get_db()
        contacts = db.get_all_contacts()
        return {
            "success": True,
            "contacts": contacts,
            "count": len(contacts),
        }
    except Exception as e:
        logger.error("Failed to list contacts: %s", e)
        return {"success": False, "contacts": [], "count": 0, "error": str(e)}


def execute_add_contact(name: str, phone: str = "", email: str = "") -> dict:
    """Add a new contact to the local database.
    
    Args:
        name: Contact name (required).
        phone: Phone number (optional, can be added later).
        email: Email address (optional).
    
    Returns:
        {"success": bool, "contact": dict | None, "error": str | None}
    """
    try:
        if not name or not name.strip():
            return {"success": False, "contact": None, "error": "Contact name is required"}
        db = _get_db()
        contact = db.add_contact(name=name.strip(), phone=phone.strip(), email=email.strip())
        return {"success": True, "contact": contact, "error": None}
    except Exception as e:
        logger.error("Failed to add contact '%s': %s", name, e)
        return {"success": False, "contact": None, "error": str(e)}


def execute_delete_contact(contact_name: str) -> dict:
    """Delete a contact by name from the local database.
    
    Args:
        contact_name: Name of the contact to delete.
    
    Returns:
        {"success": bool, "deleted": bool, "error": str | None}
    """
    try:
        if not contact_name or not contact_name.strip():
            return {"success": False, "deleted": False, "error": "Contact name is required"}
        db = _get_db()
        deleted = db.delete_contact_by_name(contact_name.strip())
        return {"success": True, "deleted": deleted, "error": None}
    except Exception as e:
        logger.error("Failed to delete contact '%s': %s", contact_name, e)
        return {"success": False, "deleted": False, "error": str(e)}


def execute_search_contacts(query: str) -> dict:
    """Search contacts by name or phone number.
    
    Args:
        query: Search string.
    
    Returns:
        {"success": bool, "contacts": list, "count": int, "error": str | None}
    """
    try:
        if not query or not query.strip():
            return {"success": False, "contacts": [], "count": 0, "error": "Search query is required"}
        db = _get_db()
        contacts = db.search_contacts(query.strip())
        return {"success": True, "contacts": contacts, "count": len(contacts), "error": None}
    except Exception as e:
        logger.error("Failed to search contacts for '%s': %s", query, e)
        return {"success": False, "contacts": [], "count": 0, "error": str(e)}
