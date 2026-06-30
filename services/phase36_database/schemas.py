"""
Phase 36 — Domain Schemas.

Predefined collection schemas for common use cases.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .models import SchemaField, CollectionSchema

logger = logging.getLogger(__name__)

# ── Predefined Schema Fields ──────────────────────────────────────────────

MEMORY_SCHEMA = CollectionSchema(
    name="memory",
    fields={
        "key": SchemaField(
            name="key",
            field_type="str",
            required=True,
            indexed=True,
            description="Unique memory key",
        ),
        "value": SchemaField(
            name="value",
            field_type="str",
            required=True,
            description="Memory value content",
        ),
        "type": SchemaField(
            name="type",
            field_type="str",
            required=True,
            indexed=True,
            description="Memory type (e.g. fact, preference, context)",
        ),
        "importance": SchemaField(
            name="importance",
            field_type="float",
            required=False,
            default_value=0.5,
            description="Importance score 0.0-1.0",
        ),
        "tags": SchemaField(
            name="tags",
            field_type="list",
            required=False,
            default_value=[],
            description="Tags for categorization",
        ),
        "created_at": SchemaField(
            name="created_at",
            field_type="datetime",
            required=False,
            description="Timestamp when created",
        ),
        "accessed_at": SchemaField(
            name="accessed_at",
            field_type="datetime",
            required=False,
            description="Timestamp when last accessed",
        ),
        "context": SchemaField(
            name="context",
            field_type="dict",
            required=False,
            default_value={},
            description="Contextual metadata",
        ),
        "source": SchemaField(
            name="source",
            field_type="str",
            required=False,
            description="Source of the memory (e.g. user, system)",
        ),
    },
    indexes=["key", "type"],
    timestamps=True,
    strict=False,
)

CONVERSATION_SCHEMA = CollectionSchema(
    name="conversation",
    fields={
        "session_id": SchemaField(
            name="session_id",
            field_type="str",
            required=True,
            indexed=True,
            description="Unique session identifier",
        ),
        "turn_number": SchemaField(
            name="turn_number",
            field_type="int",
            required=True,
            description="Turn index within the session",
        ),
        "query": SchemaField(
            name="query",
            field_type="str",
            required=True,
            description="User query text",
        ),
        "intent": SchemaField(
            name="intent",
            field_type="str",
            required=False,
            indexed=True,
            description="Detected intent",
        ),
        "entities": SchemaField(
            name="entities",
            field_type="dict",
            required=False,
            default_value={},
            description="Extracted entities",
        ),
        "response": SchemaField(
            name="response",
            field_type="str",
            required=False,
            description="System response text",
        ),
        "confidence": SchemaField(
            name="confidence",
            field_type="float",
            required=False,
            default_value=0.0,
            description="Confidence score 0.0-1.0",
        ),
        "duration_ms": SchemaField(
            name="duration_ms",
            field_type="int",
            required=False,
            default_value=0,
            description="Processing duration in milliseconds",
        ),
        "timestamp": SchemaField(
            name="timestamp",
            field_type="datetime",
            required=False,
            description="Timestamp of the turn",
        ),
    },
    indexes=["session_id", "intent"],
    timestamps=False,
    strict=False,
)

SKILL_SCHEMA = CollectionSchema(
    name="skill",
    fields={
        "skill_id": SchemaField(
            name="skill_id",
            field_type="str",
            required=True,
            indexed=True,
            description="Unique skill identifier",
        ),
        "name": SchemaField(
            name="name",
            field_type="str",
            required=True,
            description="Human-readable skill name",
        ),
        "version": SchemaField(
            name="version",
            field_type="str",
            required=True,
            description="Semantic version string",
        ),
        "description": SchemaField(
            name="description",
            field_type="str",
            required=False,
            default_value="",
            description="Skill description",
        ),
        "enabled": SchemaField(
            name="enabled",
            field_type="bool",
            required=False,
            default_value=True,
            description="Whether the skill is enabled",
        ),
        "permissions": SchemaField(
            name="permissions",
            field_type="list",
            required=False,
            default_value=[],
            description="Required permission scopes",
        ),
        "config": SchemaField(
            name="config",
            field_type="dict",
            required=False,
            default_value={},
            description="Skill-specific configuration",
        ),
        "created_at": SchemaField(
            name="created_at",
            field_type="datetime",
            required=False,
            description="Timestamp when created",
        ),
        "updated_at": SchemaField(
            name="updated_at",
            field_type="datetime",
            required=False,
            description="Timestamp when last updated",
        ),
    },
    indexes=["skill_id", "enabled"],
    timestamps=True,
    strict=False,
)

SETTINGS_SCHEMA = CollectionSchema(
    name="settings",
    fields={
        "key": SchemaField(
            name="key",
            field_type="str",
            required=True,
            indexed=True,
            description="Setting key",
        ),
        "value": SchemaField(
            name="value",
            field_type="str",
            required=True,
            description="Setting value",
        ),
        "type": SchemaField(
            name="type",
            field_type="str",
            required=False,
            default_value="str",
            description="Value type string",
        ),
        "category": SchemaField(
            name="category",
            field_type="str",
            required=False,
            indexed=True,
            default_value="general",
            description="Setting category",
        ),
        "description": SchemaField(
            name="description",
            field_type="str",
            required=False,
            default_value="",
            description="Human-readable description",
        ),
        "updated_at": SchemaField(
            name="updated_at",
            field_type="datetime",
            required=False,
            description="Timestamp when last updated",
        ),
    },
    indexes=["key", "category"],
    timestamps=False,
    strict=False,
)

TELEMETRY_SCHEMA = CollectionSchema(
    name="telemetry",
    fields={
        "event_type": SchemaField(
            name="event_type",
            field_type="str",
            required=True,
            indexed=True,
            description="Type of telemetry event",
        ),
        "service": SchemaField(
            name="service",
            field_type="str",
            required=True,
            indexed=True,
            description="Service that emitted the event",
        ),
        "duration_ms": SchemaField(
            name="duration_ms",
            field_type="int",
            required=False,
            default_value=0,
            description="Operation duration in milliseconds",
        ),
        "success": SchemaField(
            name="success",
            field_type="bool",
            required=False,
            default_value=True,
            description="Whether the operation succeeded",
        ),
        "error": SchemaField(
            name="error",
            field_type="str",
            required=False,
            description="Error message if any",
        ),
        "metadata": SchemaField(
            name="metadata",
            field_type="dict",
            required=False,
            default_value={},
            description="Additional event metadata",
        ),
        "timestamp": SchemaField(
            name="timestamp",
            field_type="datetime",
            required=False,
            description="Timestamp of the event",
        ),
    },
    indexes=["event_type", "service", "success"],
    timestamps=False,
    strict=False,
)

# ── Collection of all domain schemas ──────────────────────────────────────

ALL_DOMAIN_SCHEMAS: Dict[str, CollectionSchema] = {
    "memory": MEMORY_SCHEMA,
    "conversation": CONVERSATION_SCHEMA,
    "skill": SKILL_SCHEMA,
    "settings": SETTINGS_SCHEMA,
    "telemetry": TELEMETRY_SCHEMA,
}


def seed_schemas(store) -> int:
    """Create all 5 domain collections with their predefined schemas.

    Args:
        store: A DocumentStore instance.

    Returns:
        Number of collections created.
    """
    created = 0
    for name, schema in ALL_DOMAIN_SCHEMAS.items():
        if store.create_collection(schema):
            logger.info("Created domain collection '%s'", name)
            created += 1
        else:
            logger.debug("Domain collection '%s' already exists", name)
    return created
