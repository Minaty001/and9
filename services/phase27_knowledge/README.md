# Phase 27: Knowledge Base

## Overview

Structured Q&A, facts, user info, and domain knowledge with fast retrieval, import/export, tagging, and confidence scoring.

## Architecture

```
User Queries
     │
     ▼
┌─────────────────────┐
│   KnowledgeBase      │  ◄── Query/retrieve with confidence scoring
│                      │       Import/export, auto-linking
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│   KnowledgeStore     │  ◄── In-memory storage with tag/category indices
│                      │       Search by text, tag, category
└─────────────────────┘
```

## Components

- **KnowledgeStore**: In-memory storage with tag and category indexing, text search
- **KnowledgeBase**: High-level query, import/export, auto-linking between entries
- **KnowledgeBaseService**: ServiceBase wrapper

## Usage

```python
from services.phase27_knowledge import KnowledgeBaseService, KnowledgeQuery
svc = KnowledgeBaseService()
await svc.initialize()

# Add knowledge
await svc.add("What is Python?", "A programming language", "tech", ["python"])

# Query
result = await svc.query(KnowledgeQuery(query="Python", max_results=5))
for entry in result.entries:
    print(f"{entry.question}: {entry.answer}")

# Export
data = await svc.export_data()
```
