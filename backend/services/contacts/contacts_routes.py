"""
AND9 — Contacts REST API.

Provides full CRUD for locally stored contacts, search, Android sync,
and direct call initiation.

All endpoints are under ``/api/contacts`` blueprint.

See Also:
    - contacts_db.py for the underlying SQLite storage
    - contacts_resolver.py for contact resolution logic
"""
import logging
from backend.utils._flask_compat import Blueprint, request, jsonify

from backend.services.contacts.contacts_db import ContactsDB

logger = logging.getLogger(__name__)

contacts_bp = Blueprint("contacts", __name__)

# Module-level singleton (lazy init)
_db = None


def get_db() -> ContactsDB:
    """Get or create the singleton ContactsDB instance.

    Lazy-initializes on first call and caches in the module-level
    ``_db`` variable.

    Returns:
        ContactsDB: The global contacts database instance.
    """
    global _db
    if _db is None:
        _db = ContactsDB()
    return _db


@contacts_bp.route("", methods=["GET"])
def list_contacts():
    """GET /api/contacts — List all contacts.

    Query params:
        search (str, optional): Filter contacts by name or phone.

    Returns:
        JSON dict with ``contacts`` list and ``count`` integer.
    """
    search = request.args.get("search", "").strip() or None
    contacts = get_db().get_all_contacts(search=search)
    return jsonify({"contacts": contacts, "count": len(contacts)})


@contacts_bp.route("/<int:contact_id>", methods=["GET"])
def get_contact(contact_id: int):
    """GET /api/contacts/<id> — Get a single contact by ID.

    Returns:
        JSON contact dict, or 404 if not found.
    """
    contact = get_db().get_contact(contact_id)
    if contact is None:
        return jsonify({"error": "contact not found"}), 404
    return jsonify(contact)


@contacts_bp.route("", methods=["POST"])
def add_contact():
    """POST /api/contacts — Add a new contact.

    Body JSON:
        name  (str)  — Contact name (required).
        phone (str)  — Phone number (optional).
        email (str)  — Email address (optional).
        lookup_key (str, optional) — Android lookup key.

    Returns:
        201 with the created contact, or 400 on validation error.
    """
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400

    contact = get_db().add_contact(
        name=name,
        phone=(data.get("phone") or "").strip(),
        email=(data.get("email") or "").strip(),
        lookup_key=(data.get("lookup_key") or "").strip(),
        photo_uri=(data.get("photo_uri") or "").strip(),
        metadata=data.get("metadata"),
    )
    if contact is None:
        return jsonify({"error": "failed to create contact"}), 500
    return jsonify(contact), 201


@contacts_bp.route("/<int:contact_id>", methods=["PUT"])
def update_contact(contact_id: int):
    """PUT /api/contacts/<id> — Update an existing contact.

    Body JSON with any of: ``name``, ``phone``, ``email``, etc.
    Only provided fields are updated.

    Returns:
        200 with updated contact, 404 if not found.
    """
    data = request.get_json(silent=True) or {}
    ok = get_db().update_contact(
        contact_id,
        name=data.get("name"),
        phone=data.get("phone"),
        email=data.get("email"),
        lookup_key=data.get("lookup_key"),
        photo_uri=data.get("photo_uri"),
        metadata=data.get("metadata"),
    )
    if not ok:
        return jsonify({"error": "contact not found"}), 404
    contact = get_db().get_contact(contact_id)
    return jsonify(contact)


@contacts_bp.route("/<int:contact_id>", methods=["DELETE"])
def delete_contact(contact_id: int):
    """DELETE /api/contacts/<id> — Delete a contact.

    Returns:
        200 with status, or 404 if not found.
    """
    ok = get_db().delete_contact(contact_id)
    if not ok:
        return jsonify({"error": "contact not found"}), 404
    return jsonify({"status": "deleted", "id": contact_id})


@contacts_bp.route("/search", methods=["GET"])
def search_contacts():
    """GET /api/contacts/search?q=<query> — Fuzzy search contacts.

    Query params:
        q (str) — Search query (required).

    Returns:
        JSON dict with ``results`` list and ``count``.
        400 if ``q`` parameter is missing.
    """
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "query parameter 'q' is required"}), 400
    limit = min(int(request.args.get("limit", 20)), 100)
    results = get_db().search_contacts(query, limit=limit)
    return jsonify({"results": results, "count": len(results), "query": query})


@contacts_bp.route("/sync", methods=["POST"])
def sync_contacts():
    """POST /api/contacts/sync — Bulk sync contacts from Android.

    Body JSON: Array of contact objects:
        ``[{"name": "...", "phone": "...", "lookup_key": "..."}, ...]``

    For each contact, if a contact with the same ``lookup_key`` already
    exists in the local DB, it is updated. Otherwise a new contact is
    inserted.

    Returns:
        JSON with ``synced`` count.
        400 if body is not a list.
    """
    data = request.get_json(silent=True)
    if not isinstance(data, list):
        return jsonify({"error": "Expected a JSON array of contacts"}), 400
    count = get_db().sync_from_android(data)
    return jsonify({"synced": count, "status": "ok"})


@contacts_bp.route("/call/<int:contact_id>", methods=["POST"])
def call_contact(contact_id: int):
    """POST /api/contacts/call/<id> — Initiate a call to a stored contact.

    Looks up the contact by ID, then delegates to the call action system
    to produce a CALL intent payload.

    Returns:
        JSON with ``response``, ``action``, ``payload`` for the Android
        client to execute. 404 if contact not found.
    """
    contact = get_db().get_contact(contact_id)
    if not contact:
        return jsonify({"error": "contact not found"}), 404

    from backend.skills.android.call_actions import execute_call

    result = execute_call(
        contact_name=contact["name"],
        number=contact["phone"],
        action_type="contact",
    )
    # Store the contact id in metadata for traceability
    if isinstance(result, dict) and "metadata" in result:
        if result["metadata"] is None:
            result["metadata"] = {}
        result["metadata"]["contact_id"] = contact_id
        result["metadata"]["contact_name"] = contact["name"]

    return jsonify(result)


@contacts_bp.route("/stats", methods=["GET"])
def contacts_stats():
    """GET /api/contacts/stats — Get contacts database statistics.

    Returns:
        JSON dict with ``total_contacts`` and ``recent_additions``.
    """
    return jsonify(get_db().get_stats())
