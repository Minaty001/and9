"""
Phase 36 — Database Design Configuration.
"""

from pydantic import Field
from services.base.config_base import BaseConfig


class DatabaseConfig(BaseConfig):
    """Configuration for the in-memory database service."""

    service_name: str = Field(default="jarvis_database", description="Database service name")
    storage_type: str = Field(default="memory", description="Storage backend type")
    enable_indexing: bool = Field(default=True, description="Enable automatic indexing")
    enable_relationships: bool = Field(default=True, description="Enable relationship tracking")
    enable_schema_validation: bool = Field(default=True, description="Validate documents against schema")
    enable_migration: bool = Field(default=True, description="Enable migration support")
    max_collections: int = Field(default=20, ge=1, le=100, description="Maximum number of collections")
    max_documents_per_collection: int = Field(default=10000, ge=100, le=1000000, description="Max documents per collection")
    auto_backup_interval_minutes: int = Field(default=0, ge=0, le=1440, description="Auto-backup interval (0=disabled)")
    storage_path: str = Field(default="", description="Path for persistent storage")

    model_config = {"env_prefix": "JARVIS_PHASE36_"}
