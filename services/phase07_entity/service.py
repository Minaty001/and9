"""
Phase 7 — Entity Extraction Service.

Wraps all extractors and the validator in a ServiceBase.
"""

import time
import logging
from typing import Any, Dict, List, Optional

from services.base.service_base import ServiceBase
from .config import EntityConfig
from .models import Entity, EntityResult
from .extractors import AppExtractor, ContactExtractor, TimeExtractor, LocationExtractor, MediaExtractor
from .validator import EntityValidator

logger = logging.getLogger(__name__)


class EntityExtractionService(ServiceBase):
    """Entity extraction service combining all extractors."""

    def __init__(self, config: Optional[EntityConfig] = None):
        super().__init__(name="jarvis_entity", version="1.0.0")
        self.config = config or EntityConfig()
        self.app_extractor = AppExtractor() if config is None or config.enable_app_extraction else None
        self.contact_extractor = ContactExtractor() if config is None or config.enable_contact_extraction else None
        self.time_extractor = TimeExtractor() if config is None or config.enable_time_extraction else None
        self.location_extractor = LocationExtractor() if config is None or config.enable_location_extraction else None
        self.media_extractor = MediaExtractor() if config is None or config.enable_media_extraction else None
        self.validator = EntityValidator()
        self._start_time = 0.0

    async def initialize(self) -> bool:
        """Initialize the entity extraction service."""
        self._start_time = time.time()
        try:
            self._metrics.reset()
            self._initialized = True
            elapsed = (time.time() - self._start_time) * 1000
            logger.info("EntityExtractionService initialized in %.0fms", elapsed)
            return True
        except Exception as e:
            logger.error("EntityExtractionService init failed: %s", e)
            return False

    async def shutdown(self) -> None:
        """Shut down the service."""
        logger.info("EntityExtractionService shutting down...")
        self._initialized = False

    async def extract(self, text: str, intent: str = "") -> EntityResult:
        """Extract entities from query text.

        Args:
            text: The query text.
            intent: Optional detected intent name for focused extraction.

        Returns:
            EntityResult with extracted entities, grouped by type.
        """
        t0 = time.perf_counter()

        all_entities: List[Entity] = []

        # Run all enabled extractors
        if self.app_extractor:
            all_entities.extend(self.app_extractor.extract(text))
        if self.contact_extractor:
            all_entities.extend(self.contact_extractor.extract(text))
        if self.time_extractor:
            all_entities.extend(self.time_extractor.extract(text))
        if self.location_extractor:
            all_entities.extend(self.location_extractor.extract(text))
        if self.media_extractor:
            all_entities.extend(self.media_extractor.extract(text))

        # Validate
        is_valid, errors = self.validator.validate(all_entities)

        # Group by type
        grouped: Dict[str, List[Entity]] = {}
        for entity in all_entities:
            t = entity.type
            if t not in grouped:
                grouped[t] = []
            grouped[t].append(entity)

        elapsed = (time.perf_counter() - t0) * 1000

        self._metrics.counter("entities_extracted", len(all_entities))
        self._metrics.histogram("extraction_time_ms", elapsed)

        return EntityResult(
            entities=all_entities,
            grouped=grouped,
            validated=self.config.require_validation and is_valid,
            validation_errors=errors,
            time_ms=round(elapsed, 2),
        )

    async def extract_for_intent(self, text: str, intent: str) -> EntityResult:
        """Extract entities relevant to a specific intent.

        This focuses extraction on entity types relevant to the intent,
        saving computation.

        Args:
            text: The query text.
            intent: The detected intent name.

        Returns:
            EntityResult with relevant entities.
        """
        # For now, just run full extraction
        # Optimization: could skip extractors based on intent
        return await self.extract(text, intent)

    async def health(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "service_name": self.name,
            "version": self.version,
            "initialized": self._initialized,
            "uptime_seconds": round(uptime, 1),
            "extractors": {
                "app": self.app_extractor is not None,
                "contact": self.contact_extractor is not None,
                "time": self.time_extractor is not None,
                "location": self.location_extractor is not None,
                "media": self.media_extractor is not None,
            },
        }

    async def stats(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        return {
            "service": self.name,
            "version": self.version,
            "uptime_seconds": round(uptime, 1),
            "metrics": self._metrics.snapshot(),
        }
