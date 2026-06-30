"""
Contact name entity extractor.

Extracts contact names from call/message queries.
"""

import re
from typing import List, Optional

from services.phase07_entity.models import Entity


class ContactExtractor:
    """Extract contact names from call/message queries.

    Usage:
        extractor = ContactExtractor()
        entities = extractor.extract("call mom")
        # [Entity(type="contact", value="mom", original="mom", ...)]
    """

    # Relationship terms that often precede names
    RELATIONSHIPS = {
        "mom", "mother", "maa", "dad", "father", "papa", "brother", "bhai",
        "sister", "didi", "bhabhi", "uncle", "aunt", "aunty", "grandma",
        "grandpa", "friend", "dost", "boss", "sir", "madam",
        "wife", "patni", "husband", "pati", "son", "beta", "daughter", "beti",
    }

    # Trigger patterns for contact-related queries
    TRIGGER_PATTERNS = [
        r"(?:call|phone|dial|phone karo|call karo)\s+(.+?)(?:\s*(?:now|please|pls|ko|karo|kar do))?\s*$",
        r"(?:message|text|sms|msg|message bhejo|text karo)\s+(.+?)(?:\s*(?:now|please|pls))?\s*$",
        r"(?:send|bhejo)\s+(?:message|text|msg)\s+(?:to|ko)\s+(.+?)\s*$",
        r"(?:contact|number)\s+(?:of|for|ka|ki)\s+(.+?)\s*$",
    ]

    def extract(self, text: str) -> List[Entity]:
        """Extract contact names from query text.

        Args:
            text: The query text.

        Returns:
            List of Entity objects for each detected contact.
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
                if len(candidate) > 50:
                    continue

                # Filter out generic words
                if candidate.lower() in {"it", "him", "her", "them", "someone", "somebody"}:
                    continue

                seen.add(candidate)
                confidence = 0.95 if candidate.lower() in self.RELATIONSHIPS else 0.8
                entities.append(Entity(
                    type="contact",
                    value=candidate,
                    original=candidate,
                    confidence=confidence,
                    start=match.start(1),
                    end=match.end(1),
                    metadata={"contact_name": candidate},
                ))

        return entities

    def is_relationship(self, name: str) -> bool:
        """Check if a name is a known relationship term.

        Args:
            name: The name to check.

        Returns:
            True if it's a relationship term.
        """
        return name.lower().replace(" ", "") in self.RELATIONSHIPS
