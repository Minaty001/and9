# Phase 36: Database Design

## Overview

In-memory database abstraction with collections, indexes, and relationships. Provides schema definitions, CRUD operations, query filtering, and migration management.

## Architecture

```
CollectionSchema
     │
     ▼
┌─────────────────────┐
│   DocumentStore      │  ◄── In-memory document storage
│                      │       Schema validation, CRUD, filtering
│   ┌───────────────┐  │
│   │ Document Dict  │  │  Collection name → {id → document}
│   └───────────────┘  │
└─────────┬───────────┘
          │
     ┌────┴────┐
     ▼         ▼
IndexManager  MigrationManager
     │              │
     ▼              ▼
  Indexes       Migration
  (field        lifecycle
   lookup)      (create/apply/
                rollback)
```

## Components

- **DocumentStore**: In-memory document storage with schema validation, CRUD, AND-filter queries
- **SchemaField / CollectionSchema**: Schema definition models with type validation, defaults, uniqueness
- **QueryFilter / QueryResult**: Query models supporting eq/ne/gt/gte/lt/lte/in/contains/regex operators
- **IndexManager**: Create, drop, list, and optimize indexes on collection fields
- **MigrationManager**: Create, apply, rollback, and list migrations
- **DatabaseService**: ServiceBase wrapper exposing all operations with metrics

## Usage

```python
from services.phase36_database import DatabaseService, CollectionSchema, SchemaField, QueryFilter

svc = DatabaseService()
await svc.initialize()

# Create a collection
schema = CollectionSchema(
    name="users",
    fields={"name": SchemaField(name="name", field_type="str", required=True)},
)
svc.create_collection(schema)

# Insert documents
user_id = svc.insert("users", {"name": "Alice", "age": 30})

# Query with filters
filters = [QueryFilter(field="age", operator="gt", value=25)]
results = svc.find("users", filters)

# Migrations
mid = svc.create_migration("add_email")
svc.apply_migration(mid)
```
