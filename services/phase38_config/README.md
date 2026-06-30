# Phase 38: Configuration System

## Overview

Centralized configuration management with multi-source support (memory, file, env), profiles, overrides, and validation.

## Architecture

```
Config Sources
(memory / file / env)
     │
     ▼
┌─────────────────────┐
│    ConfigStore       │  ◄── Key-value storage per profile
│                      │       Source priority resolution
└─────────┬───────────┘
          │
     ┌────┴────┐
     ▼         ▼
ProfileManager  ConfigValidator
     │              │
     ▼              ▼
  Profiles      Type/range/
  (create/      regex/value
   delete/      validation
   clone)
```

## Components

- **ConfigStore**: Key-value config storage with profile isolation and source priority resolution
- **ProfileManager**: Create, delete, rename, activate, and clone configuration profiles
- **ConfigValidator**: Validate types, allowed values, min/max, range, regex, min/max length
- **ConfigService**: ServiceBase wrapper with export/import capabilities

## Usage

```python
from services.phase38_config import ConfigService

svc = ConfigService()
await svc.initialize()

# Set and get config
svc.set("db.host", "localhost", description="Database host")
svc.set("db.port", 5432, description="Database port")
host = svc.get("db.host")

# Profiles
svc.create_profile("production")
svc.activate_profile("production")
svc.set("db.host", "prod.example.com")

# Export/Import
exported = svc.export_config()
svc.import_config('{"new.key": "new_value"}')

# Validation
errors = svc.validate("port", "bad_value", {"type": "int"})
```
