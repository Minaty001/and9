"""
AND9 — Contacts Database Service.

SQLite-backed contacts storage that manages phone contacts locally.
Supports full CRUD, fuzzy search, and Android ContactsContract sync.

The contacts table stores:
  - id:         Integer primary key (auto-increment)
  - name:       Contact display name
  - phone:      Primary phone number
  - email:      Optional email address
  - lookup_key: Android ContactsContract lookup key for sync dedup
  - photo_uri:  Android contact photo URI
  - created_at: ISO timestamp of creation
  - updated_at: ISO timestamp of last update
  - metadata:   JSON blob for extensible fields
"""
import json
import os
import sqlite3
import logging
import threading
from datetime import datetime
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

# Dynamic DB path resolution
if os.environ.get("RENDER") or os.path.exists("/app/.jarvis_data"):
    _default_db = "/app/.jarvis_data/contacts.db"
else:
    _default_db = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "contacts.db")
    )

DB_PATH = os.environ.get("AND9_CONTACTS_DB", _default_db)


def _ensure_dir(path: str):
    """Ensure the directory for a file path exists."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
    except Exception as e:
        logger.warning("Could not create directory '%s': %s", os.path.dirname(path), e)


class ContactsDB:
    """SQLite-backed contacts database with thread-safe CRUD.

    Usage:
        db = ContactsDB()
        db.add_contact("Mummy", "+919876543210")
        db.add_contact("Papa", "+919876543211")
        all_contacts = db.get_all_contacts()
        results = db.search_contacts("mummy")
        db.delete_contact(1)
    """

    def __init__(self, db_path: str = DB_PATH):
        self._db_path = db_path
        self._lock = threading.Lock()
        _ensure_dir(self._db_path)
        self.init_db()

    # ── Schema ────────────────────────────────────────────────────────

    def init_db(self):
        """Create the contacts table if it does not exist."""
        with self._lock:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS contacts (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    name        TEXT    NOT NULL,
                    phone       TEXT,
                    email       TEXT    DEFAULT '',
                    lookup_key  TEXT    DEFAULT '',
                    photo_uri   TEXT    DEFAULT '',
                    created_at  TEXT    NOT NULL,
                    updated_at  TEXT    NOT NULL,
                    metadata    TEXT    DEFAULT '{}'
                )
            """)
            # Index for fast name search
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_contacts_name ON contacts(name)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_contacts_phone ON contacts(phone)"
            )
            conn.commit()
            conn.close()
            logger.info("ContactsDB initialized at %s", self._db_path)

    # ── Internal helpers ──────────────────────────────────────────────

    def _connect(self) -> sqlite3.Connection:
        """Open a new connection (thread-safe via lock)."""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _row_to_dict(self, row: sqlite3.Row) -> dict:
        """Convert a sqlite3.Row to a plain dict with JSON metadata parsing."""
        d = dict(row)
        try:
            d["metadata"] = json.loads(d.get("metadata", "{}"))
        except (json.JSONDecodeError, TypeError):
            d["metadata"] = {}
        return d

    def _now(self) -> str:
        return datetime.now().isoformat()

    # ── CRUD Operations ───────────────────────────────────────────────

    def add_contact(
        self,
        name: str,
        phone: str = "",
        email: str = "",
        lookup_key: str = "",
        photo_uri: str = "",
        metadata: dict = None,
    ) -> Optional[dict]:
        """Add a new contact to the database.

        Args:
            name: Contact display name (required).
            phone: Phone number (optional).
            email: Email address (optional).
            lookup_key: Android ContactsContract lookup key (optional).
            photo_uri: Contact photo URI (optional).
            metadata: Optional dict of extra data.

        Returns:
            The newly created contact dict, or None if name is empty.
        """
        name = name.strip()
        if not name:
            return None

        now = self._now()
        meta_json = json.dumps(metadata or {})

        with self._lock:
            conn = self._connect()
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO contacts
                   (name, phone, email, lookup_key, photo_uri, created_at, updated_at, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (name, phone, email, lookup_key, photo_uri, now, now, meta_json),
            )
            conn.commit()
            new_id = cursor.lastrowid
            cursor.execute("SELECT * FROM contacts WHERE id = ?", (new_id,))
            row = cursor.fetchone()
            conn.close()

        contact = self._row_to_dict(row) if row else None
        if contact:
            logger.info("ContactsDB: Added contact '%s' (id=%s, phone=%s)", name, new_id, phone)
        return contact

    def get_contact(self, contact_id: int) -> Optional[dict]:
        """Get a single contact by its integer ID."""
        with self._lock:
            conn = self._connect()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM contacts WHERE id = ?", (contact_id,))
            row = cursor.fetchone()
            conn.close()
        return self._row_to_dict(row) if row else None

    def get_contact_by_name(self, name: str) -> Optional[dict]:
        """Get the first contact matching a name (case-insensitive)."""
        with self._lock:
            conn = self._connect()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM contacts WHERE LOWER(name) = LOWER(?) LIMIT 1",
                (name.strip(),),
            )
            row = cursor.fetchone()
            conn.close()
        return self._row_to_dict(row) if row else None

    def get_contact_by_phone(self, phone: str) -> Optional[dict]:
        """Get the first contact matching a phone number (exact match)."""
        clean_phone = phone.strip()
        with self._lock:
            conn = self._connect()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM contacts WHERE phone = ? LIMIT 1", (clean_phone,)
            )
            row = cursor.fetchone()
            conn.close()
        return self._row_to_dict(row) if row else None

    def get_all_contacts(self, search: str = None) -> List[dict]:
        """Get all contacts, optionally filtered by a search string.

        Args:
            search: If provided, filters contacts whose name or phone
                    contains the search term (case-insensitive).

        Returns:
            List of contact dicts sorted by name.
        """
        with self._lock:
            conn = self._connect()
            cursor = conn.cursor()
            if search:
                pattern = f"%{search.strip()}%"
                cursor.execute(
                    """SELECT * FROM contacts
                       WHERE name LIKE ? OR phone LIKE ?
                       ORDER BY name ASC""",
                    (pattern, pattern),
                )
            else:
                cursor.execute("SELECT * FROM contacts ORDER BY name ASC")
            rows = cursor.fetchall()
            conn.close()
        return [self._row_to_dict(r) for r in rows]

    def update_contact(
        self,
        contact_id: int,
        name: str = None,
        phone: str = None,
        email: str = None,
        lookup_key: str = None,
        photo_uri: str = None,
        metadata: dict = None,
    ) -> bool:
        """Update an existing contact. Only provided fields are changed.

        Args:
            contact_id: The contact's integer ID.
            name: New display name (optional).
            phone: New phone number (optional).
            email: New email (optional).
            lookup_key: New lookup key (optional).
            photo_uri: New photo URI (optional).
            metadata: New metadata dict (replaces existing).

        Returns:
            True if the contact was found and updated, False otherwise.
        """
        existing = self.get_contact(contact_id)
        if not existing:
            return False

        now = self._now()
        fields = {}
        if name is not None:
            fields["name"] = name.strip()
        if phone is not None:
            fields["phone"] = phone.strip()
        if email is not None:
            fields["email"] = email.strip()
        if lookup_key is not None:
            fields["lookup_key"] = lookup_key.strip()
        if photo_uri is not None:
            fields["photo_uri"] = photo_uri.strip()
        if metadata is not None:
            fields["metadata"] = json.dumps(metadata)

        if not fields:
            return True  # Nothing to update

        fields["updated_at"] = now

        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [contact_id]

        with self._lock:
            conn = self._connect()
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE contacts SET {set_clause} WHERE id = ?", values
            )
            conn.commit()
            conn.close()

        logger.info("ContactsDB: Updated contact id=%s", contact_id)
        return True

    def delete_contact(self, contact_id: int) -> bool:
        """Delete a contact by ID.

        Args:
            contact_id: The contact's integer ID.

        Returns:
            True if a row was deleted, False if not found.
        """
        with self._lock:
            conn = self._connect()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
            conn.close()
        if deleted:
            logger.info("ContactsDB: Deleted contact id=%s", contact_id)
        return deleted

    def delete_contact_by_name(self, name: str) -> bool:
        """Delete a contact by name (case-insensitive). Deletes all matching contacts.

        Args:
            name: Contact name to delete.

        Returns:
            True if at least one row was deleted, False if not found.
        """
        with self._lock:
            conn = self._connect()
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM contacts WHERE LOWER(name) LIKE LOWER(?)",
                (f"%{name.strip()}%",),
            )
            deleted = cursor.rowcount > 0
            conn.commit()
            conn.close()
        if deleted:
            logger.info("ContactsDB: Deleted contact(s) matching name='%s'", name)
        return deleted

    # ── Search & Sync ─────────────────────────────────────────────────

    def search_contacts(self, query: str, limit: int = 20) -> List[dict]:
        """Fuzzy search contacts by name or phone number.

        Performs a LIKE-based search on both name and phone columns,
        returning up to ``limit`` results sorted by relevance (name
        match first, then phone match).

        Args:
            query: Search string.
            limit: Maximum results to return (default 20).

        Returns:
            List of matching contact dicts.
        """
        q = query.strip().lower()
        if not q:
            return []

        with self._lock:
            conn = self._connect()
            cursor = conn.cursor()
            pattern = f"%{q}%"
            cursor.execute(
                """SELECT *, 
                          CASE 
                              WHEN LOWER(name) LIKE ? THEN 1
                              ELSE 2
                          END AS rank
                   FROM contacts
                   WHERE LOWER(name) LIKE ? OR LOWER(phone) LIKE ?
                   ORDER BY rank, name ASC
                   LIMIT ?""",
                (pattern, pattern, pattern, limit),
            )
            rows = cursor.fetchall()
            conn.close()

        results = []
        for row in rows:
            d = self._row_to_dict(row)
            d.pop("rank", None)
            results.append(d)
        return results

    def sync_from_android(self, contacts_list: List[dict]) -> int:
        """Bulk sync contacts from Android device.

        For each contact in the list, if a contact with the same
        ``lookup_key`` exists, it is updated. Otherwise a new contact
        is inserted.

        Args:
            contacts_list: List of dicts with keys ``name``, ``phone``,
                ``lookup_key``, and optionally ``email``, ``photo_uri``.

        Returns:
            Number of contacts added or updated during sync.
        """
        count = 0
        for entry in contacts_list:
            name = (entry.get("name") or "").strip()
            phone = (entry.get("phone") or "").strip()
            lookup_key = (entry.get("lookup_key") or "").strip()

            if not name:
                continue

            # Check if already exists by lookup_key
            existing = None
            if lookup_key:
                with self._lock:
                    conn = self._connect()
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT * FROM contacts WHERE lookup_key = ? LIMIT 1",
                        (lookup_key,),
                    )
                    row = cursor.fetchone()
                    conn.close()
                    if row:
                        existing = self._row_to_dict(row)

            if existing:
                self.update_contact(
                    existing["id"],
                    name=name,
                    phone=phone or existing.get("phone", ""),
                    email=entry.get("email", existing.get("email", "")),
                    lookup_key=lookup_key,
                    photo_uri=entry.get("photo_uri", existing.get("photo_uri", "")),
                )
            else:
                self.add_contact(
                    name=name,
                    phone=phone,
                    email=entry.get("email", ""),
                    lookup_key=lookup_key,
                    photo_uri=entry.get("photo_uri", ""),
                )
            count += 1

        logger.info("ContactsDB: Synced %d contacts from Android", count)
        return count

    # ── Stats ─────────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        """Return database statistics.

        Returns:
            Dict with keys: total_contacts, last_added.
        """
        with self._lock:
            conn = self._connect()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM contacts")
            total = cursor.fetchone()[0]
            cursor.execute(
                "SELECT name, created_at FROM contacts ORDER BY created_at DESC LIMIT 3"
            )
            recent = [{"name": r[0], "added_at": r[1]} for r in cursor.fetchall()]
            conn.close()
        return {
            "total_contacts": total,
            "recent_additions": recent,
        }

    def clear_all(self) -> int:
        """Delete all contacts from the database. Returns count of deleted rows.

        Use with caution — this is primarily for testing.
        """
        with self._lock:
            conn = self._connect()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM contacts")
            deleted = cursor.rowcount
            conn.commit()
            conn.close()
        logger.warning("ContactsDB: Cleared all %d contacts", deleted)
        return deleted
