"""
AND9 — Contacts Service.

SQLite-backed contacts storage, REST API, and enhanced resolution
for phone calls. Provides local contact management with Android
ContactsContract sync support.

Components:
    - ContactsDB:     SQLite database with full CRUD, search, sync
    - contacts_bp:    Flask Blueprint for /api/contacts REST API
"""
from backend.services.contacts.contacts_db import ContactsDB, DB_PATH
from backend.services.contacts.contacts_routes import contacts_bp

__all__ = ["ContactsDB", "contacts_bp", "DB_PATH"]
