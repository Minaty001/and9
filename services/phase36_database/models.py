"""
Phase 36 — Database Design Models.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class SchemaField(BaseModel):
    """Definition of a single field in a collection schema."""

    name: str = Field(..., description="Field name")
    field_type: str = Field(..., description="Field type: str/int/float/bool/dict/list/datetime")
    required: bool = Field(default=False, description="Whether the field is required")
    unique: bool = Field(default=False, description="Whether the field value must be unique")
    indexed: bool = Field(default=False, description="Whether to index this field")
    default_value: Any = Field(default=None, description="Default value if not provided")
    validation_rules: Dict[str, Any] = Field(default_factory=dict, description="Validation rules")
    description: str = Field(default="", description="Human-readable description")


class CollectionSchema(BaseModel):
    """Schema definition for a collection."""

    name: str = Field(..., description="Collection name")
    fields: Dict[str, SchemaField] = Field(default_factory=dict, description="Field definitions keyed by name")
    relationships: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Relationship definitions")
    indexes: List[str] = Field(default_factory=list, description="List of indexed field names")
    timestamps: bool = Field(default=True, description="Auto-add created_at/updated_at")
    strict: bool = Field(default=True, description="Reject fields not in schema")


class QueryFilter(BaseModel):
    """A single query filter condition."""

    field: str = Field(..., description="Field name to filter on")
    operator: str = Field(..., description="Operator: eq/ne/gt/gte/lt/lte/in/contains/regex")
    value: Any = Field(..., description="Value to compare against")


class QueryResult(BaseModel):
    """Result of a query operation."""

    documents: List[Dict[str, Any]] = Field(default_factory=list, description="Matching documents")
    total_found: int = Field(default=0, description="Total matching documents (before pagination)")
    query_time_ms: float = Field(default=0.0, description="Query execution time in milliseconds")
    page: int = Field(default=1, description="Current page number")
    page_size: int = Field(default=20, description="Items per page")
    has_more: bool = Field(default=False, description="Whether there are more results")


class MigrateAction(BaseModel):
    """A migration action descriptor."""

    action: str = Field(..., description="Action type: add_field/remove_field/rename_field/update_values")
    collection: str = Field(..., description="Target collection")
    params: Dict[str, Any] = Field(default_factory=dict, description="Action parameters")
