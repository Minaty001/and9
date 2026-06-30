"""
Phase 7 — Entity Extraction
=============================

Extract apps, contacts, songs, websites, dates, times, locations.
Validate entities before execution.
Resolve ambiguities using context.

Extractors:
    - AppExtractor: App/package name extraction
    - ContactExtractor: Contact name extraction
    - TimeExtractor: Date/time/duration extraction
    - LocationExtractor: Location/city extraction
    - MediaExtractor: Song/video/media extraction
"""

from .extractors import AppExtractor, ContactExtractor, TimeExtractor, LocationExtractor, MediaExtractor
from .validator import EntityValidator
from .service import EntityExtractionService
from .config import EntityConfig
from .models import Entity, EntityResult

__all__ = [
    "AppExtractor",
    "ContactExtractor",
    "TimeExtractor",
    "LocationExtractor",
    "MediaExtractor",
    "EntityValidator",
    "EntityExtractionService",
    "EntityConfig",
    "Entity",
    "EntityResult",
]
