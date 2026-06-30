# Phase 37: File Manager

## Overview

Virtual file system with read/write, directory navigation, file metadata, search, and trash/recovery.

## Architecture

```
File Operations
     │
     ▼
┌─────────────────────┐
│  VirtualFileSystem   │  ◄── In-memory virtual filesystem
│                      │       CRUD, copy, move, directory listing
└─────────┬───────────┘
          │
     ┌────┴────┐
     ▼         ▼
FileSearch   TrashManager
Engine           │
     │           ▼
     ▼        Trash
  Search      (retention
  Indexing    & recovery)
```

## Components

- **VirtualFileSystem**: In-memory filesystem with create/read/write/delete/copy/move operations
- **FileSearchEngine**: Index and search files by name, content, tags, and metadata
- **TrashManager**: Move to trash, restore, empty trash, cleanup expired items
- **FileManagerService**: ServiceBase wrapper with metrics

## Usage

```python
from services.phase37_file_manager import FileManagerService

svc = FileManagerService()
await svc.initialize()

# Create and write files
svc.create_file("/notes/hello.txt", "Hello, world!")
svc.write_file("/notes/hello.txt", "Updated content")

# Read files
result = svc.read_file("/notes/hello.txt")

# List directory
entry = svc.list_directory("/notes")
print(f"Found {entry.entry_count} files")

# Search
results = svc.search("hello")

# Delete (moves to trash)
svc.delete_file("/notes/hello.txt")
trash = svc.list_trash()
```
