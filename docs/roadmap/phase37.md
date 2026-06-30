# Phase 37: Database

## Purpose
Database layer with domain schemas, migrations, repositories, and SQLite backend. The `app/database/` package provides a structured data access layer with model definitions, repository patterns for data access, migration management for schema evolution, and a SQLite implementation. Also includes a MongoDB adapter (`app/core/mongodb.py`) and an activity database (`app/core/activity_db.py`) for logging interactions.

## Architecture
```
app/database/
  ├── models/ — domain model definitions (empty init, models defined in consuming packages)
  ├── repositories/ — data access repositories (empty init, repository pattern)
  ├── migrations/ — database schema migration management
  └── sqlite/ — SQLite backend implementation

app/core/
  ├── mongodb.py — MongoDB adapter for document storage
  └── activity_db.py — Activity log database for tracking user interactions

app/services/reminder/and9_db.py — Reminder SQLite persistence layer
```

## Code
```python
# Database package structure provides:
# - Schema definitions in models/
# - Repository pattern for CRUD operations
# - Migration management for versioned schema changes
# - SQLite backend with connection pooling

# app/core/mongodb.py — MongoDB adapter
# app/core/activity_db.py — Activity logging
```

## Location
`app/database/` — models, repositories, migrations, SQLite backend; `app/core/mongodb.py` and `app/core/activity_db.py`
