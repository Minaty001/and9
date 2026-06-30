"""
Media entity extractor (songs, videos, albums).

Extracts media-related entities from queries.
"""

import re
from typing import List

from services.phase07_entity.models import Entity


class MediaExtractor:
    """Extract media entities (songs, videos, albums) from queries.

    Usage:
        extractor = MediaExtractor()
        entities = extractor.extract("play despacito on youtube")
        # [Entity(type="media", value="despacito", original="despacito", ...)]
    """

    TRIGGER_PATTERNS = [
        # Play specific media with type keyword
        r"(?:play|bajao|chalao)\s+(?:the\s+)?(?:song|music|gaana|video|track|album)\s+(.+?)(?:\s+(?:on|from|by|please|pls|karo))?\s*$",
        # Play + name + media type keyword
        r"(?:play|bajao|chalao)\s+(.+?)\s+(?:song|music|gaana|video|track|album)(?:\s+(?:on|from|by|please|pls))?\s*$",
        # Simple "play X" (fallback — lower confidence)
        r"(?:play|bajao|chalao)\s+(.+?)\s*$",
        # Search for media
        r"(?:search|find|dhoondho|search karo)\s+(?:for\s+)?(?:song|music|video|gaana)\s+(.+?)(?:\s*(?:on|from|by))?\s*$",
        # Youtube-specific
        r"(?:search|find|dhoondho)\s+(?:on\s+)?youtube\s+(.+?)(?:\s*(?:video|song))?\s*$",
        r"youtube\s+(?:pe\s+)?(?:search|dhoondho)\s+(.+?)\s*$",
    ]

    # Known media platforms
    PLATFORMS = {"youtube", "spotify", "gaana", "wynk", "jiosaavn", "amazon music"}

    def extract(self, text: str) -> List[Entity]:
        """Extract media names from query text.

        Args:
            text: The query text.

        Returns:
            List of Entity objects for each detected media entity.
        """
        if not text:
            return []

        entities: List[Entity] = []
        text_lower = text.lower().strip()
        seen: set = set()

        # Pattern-based extraction
        for pattern in self.TRIGGER_PATTERNS:
            for match in re.finditer(pattern, text_lower):
                candidate = match.group(1).strip().rstrip(".")
                if not candidate or candidate in seen:
                    continue
                if candidate in self.PLATFORMS:
                    continue
                if len(candidate) > 100:
                    continue

                seen.add(candidate)

                # Detect platform if mentioned
                platform = None
                text_after = text_lower[match.end():]
                for p in self.PLATFORMS:
                    if p in text_after:
                        platform = p
                        break

                confidence = 0.85 if platform else 0.7
                entities.append(Entity(
                    type="media",
                    value=candidate,
                    original=candidate,
                    confidence=confidence,
                    start=match.start(1),
                    end=match.end(1),
                    metadata={"media_type": "song", "platform": platform},
                ))

        return entities
