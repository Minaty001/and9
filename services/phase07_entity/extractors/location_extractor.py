"""
Location/city entity extractor.

Extracts location and city names from queries.
"""

import re
from typing import Dict, List, Optional

from services.phase07_entity.models import Entity


class LocationExtractor:
    """Extract location and city names from queries.

    Usage:
        extractor = LocationExtractor()
        entities = extractor.extract("weather in delhi")
        # [Entity(type="location", value="delhi", original="delhi", ...)]
    """

    # Known cities (sample — extensible via config)
    KNOWN_CITIES: Dict[str, str] = {
        "mumbai": "Mumbai, India",
        "delhi": "Delhi, India",
        "bangalore": "Bangalore, India",
        "bengaluru": "Bangalore, India",
        "hyderabad": "Hyderabad, India",
        "ahmedabad": "Ahmedabad, India",
        "chennai": "Chennai, India",
        "kolkata": "Kolkata, India",
        "pune": "Pune, India",
        "jaipur": "Jaipur, India",
        "lucknow": "Lucknow, India",
        "new york": "New York, USA",
        "london": "London, UK",
        "paris": "Paris, France",
        "tokyo": "Tokyo, Japan",
        "dubai": "Dubai, UAE",
        "singapore": "Singapore",
        "sydney": "Sydney, Australia",
        "toronto": "Toronto, Canada",
        "berlin": "Berlin, Germany",
    }

    # Hindi city names
    HINDI_CITIES: Dict[str, str] = {
        "मुंबई": "mumbai",
        "दिल्ली": "delhi",
        "बंगलौर": "bangalore",
        "हैदराबाद": "hyderabad",
        "अहमदाबाद": "ahmedabad",
        "चेन्नई": "chennai",
        "कोलकाता": "kolkata",
        "पुणे": "pune",
        "जयपुर": "jaipur",
        "लखनऊ": "lucknow",
    }

    TRIGGER_PATTERNS = [
        r"(?:weather|temperature|mausam)\s+(?:in|of|for|ka|ki)\s+(\w+(?:\s+\w+)?)",
        r"(?:time|samay)\s+(?:in|of|for|ka)\s+(\w+(?:\s+\w+)?)",
        r"(?:location|place|city)\s+(?:of|for|ka)\s+(\w+(?:\s+\w+)?)",
        r"(?:near|nearby|around|paas)\s+(\w+(?:\s+\w+)?)",
        r"in\s+(\w+(?:\s+\w+)?)(?:\s*(?:city|town|area))?",
    ]

    def extract(self, text: str) -> List[Entity]:
        """Extract location/city names from query text.

        Args:
            text: The query text.

        Returns:
            List of Entity objects for each detected location.
        """
        if not text:
            return []

        entities: List[Entity] = []
        text_lower = text.lower().strip()
        seen: set = set()

        # 1. Direct city name match
        for city_name in sorted(self.KNOWN_CITIES.keys(), key=len, reverse=True):
            if city_name in text_lower and city_name not in seen:
                seen.add(city_name)
                idx = text_lower.find(city_name)
                full_name = self.KNOWN_CITIES[city_name]
                entities.append(Entity(
                    type="location",
                    value=full_name,
                    original=city_name,
                    confidence=0.95,
                    start=idx,
                    end=idx + len(city_name),
                    normalized=city_name.title(),
                    metadata={"city": city_name, "full_name": full_name},
                ))

        # 2. Pattern-based extraction
        for pattern in self.TRIGGER_PATTERNS:
            for match in re.finditer(pattern, text_lower):
                candidate = match.group(1).strip()
                if candidate in seen:
                    continue
                if len(candidate) < 2 or len(candidate) > 30:
                    continue
                if candidate in ("the", "a", "an", "my", "your", "this", "that"):
                    continue

                seen.add(candidate)
                entities.append(Entity(
                    type="location",
                    value=candidate,
                    original=candidate,
                    confidence=0.7,
                    start=match.start(1),
                    end=match.end(1),
                    normalized=candidate.title(),
                    metadata={"location": candidate},
                ))

        return entities

    def resolve_city(self, name: str) -> Optional[str]:
        """Resolve a city name to its full location string.

        Args:
            name: City name.

        Returns:
            Full location string or None.
        """
        return self.KNOWN_CITIES.get(name.lower().strip())
