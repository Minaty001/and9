"""
Phase 36 — Database Design
===========================

In-memory database abstraction with collections, indexes, relationships.
Schema definitions, CRUD, query filtering, migration.

Components:
    - DocumentStore: In-memory document storage with CRUD, indexing, query filtering
    - SchemaField / CollectionSchema: Schema definition models
    - QueryFilter / QueryResult: Query models
    - IndexManager: Index creation, drop, list, optimization
    - MigrationManager: Migration lifecycle
    - DatabaseService: ServiceBase wrapper
"""

from .config import DatabaseConfig
from .models import SchemaField, CollectionSchema, QueryFilter, QueryResult, MigrateAction
from .document_store import DocumentStore
from .index_manager import IndexManager
from .migration_manager import MigrationManager
from .backup_manager import BackupManager
from .schemas import (
    MEMORY_SCHEMA,
    CONVERSATION_SCHEMA,
    SKILL_SCHEMA,
    SETTINGS_SCHEMA,
    TELEMETRY_SCHEMA,
    ALL_DOMAIN_SCHEMAS,
    seed_schemas,
)
from .service import DatabaseService

__all__ = [
    "DatabaseConfig",
    "SchemaField",
    "CollectionSchema",
    "QueryFilter",
    "QueryResult",
    "MigrateAction",
    "DocumentStore",
    "IndexManager",
    "MigrationManager",
    "BackupManager",
    "MEMORY_SCHEMA",
    "CONVERSATION_SCHEMA",
    "SKILL_SCHEMA",
    "SETTINGS_SCHEMA",
    "TELEMETRY_SCHEMA",
    "ALL_DOMAIN_SCHEMAS",
    "seed_schemas",
    "DatabaseService",
]
