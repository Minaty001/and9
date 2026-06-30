"""
Date/time entity extractor.

Extracts dates, times, durations, and reminders from queries.
"""

import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from services.phase07_entity.models import Entity


class TimeExtractor:
    """Extract date, time, and duration entities from queries.

    Usage:
        extractor = TimeExtractor()
        entities = extractor.extract("set alarm for 7am")
        entities = extractor.extract("remind me in 10 minutes")
    """

    # Time patterns
    TIME_PATTERNS = {
        "absolute": [
            r"(\d{1,2}):(\d{2})\s*(am|pm|a\.m\.|p\.m\.)?",
            r"(\d{1,2})\s*(am|pm|a\.m\.|p\.m\.)(?:\s*:?\s*(\d{2}))?",
            r"at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)?",
        ],
        "relative": [
            r"(?:in|after)\s+(\d+)\s*(minute|minutes|min|mins|hour|hours|sec|secs|second|seconds)",
            r"(?:after|in)\s+(?:an?\s+)?(hour|minute|second)",
            r"(\d+)\s*(?:min|mins)\s+(?:later|after)",
        ],
        "named": {
            "morning": "06:00",
            "afternoon": "12:00",
            "evening": "18:00",
            "night": "21:00",
            "midnight": "00:00",
            "noon": "12:00",
            "today": None,  # dynamic
            "tomorrow": None,  # dynamic
            "day after tomorrow": None,  # dynamic
        },
    }

    # Date patterns
    DATE_PATTERNS = [
        r"(today|tomorrow|day after tomorrow|day after|parson)",
        r"(this|next|coming)\s+(week|month|year|monday|tuesday|wednesday|thursday|friday|saturday|sunday)",
        r"(\d{1,2})(?:st|nd|rd|th)?\s+(january|february|march|april|may|june|july|august|september|october|november|december)",
        r"(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2})(?:st|nd|rd|th)?",
        r"(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?",
    ]

    # Duration patterns
    DURATION_PATTERNS = [
        r"(\d+)\s*(minute|minutes|min|mins)",
        r"(\d+)\s*(hour|hours|hr|hrs)",
        r"(\d+)\s*(second|seconds|sec|secs)",
        r"(\d+)\s*(day|days)",
        r"(?:a|an)\s+(hour|minute|second|day)",
    ]

    def extract(self, text: str) -> List[Entity]:
        """Extract time/date entities from query text.

        Args:
            text: The query text.

        Returns:
            List of Entity objects for each detected time entity.
        """
        if not text:
            return []

        entities: List[Entity] = []
        text_lower = text.lower().strip()

        # Absolute time
        for pattern in self.TIME_PATTERNS["absolute"]:
            for match in re.finditer(pattern, text_lower):
                value = self._normalize_time(match)
                entities.append(Entity(
                    type="time",
                    value=value if value else match.group(0),
                    original=match.group(0),
                    confidence=0.9,
                    start=match.start(),
                    end=match.end(),
                    metadata={"time_type": "absolute"},
                ))

        # Relative time
        for pattern in self.TIME_PATTERNS["relative"]:
            for match in re.finditer(pattern, text_lower):
                entities.append(Entity(
                    type="time",
                    value=match.group(0),
                    original=match.group(0),
                    confidence=0.85,
                    start=match.start(),
                    end=match.end(),
                    metadata={"time_type": "relative", "duration": match.group(1), "unit": match.group(2)},
                ))

        # Named times
        for name, time_val in self.TIME_PATTERNS["named"].items():
            if name in text_lower:
                idx = text_lower.find(name)
                entities.append(Entity(
                    type="time",
                    value=time_val or name,
                    original=name,
                    confidence=0.8,
                    start=idx,
                    end=idx + len(name),
                    metadata={"time_type": "named", "name": name},
                ))

        # Dates
        for pattern in self.DATE_PATTERNS:
            for match in re.finditer(pattern, text_lower):
                entities.append(Entity(
                    type="date",
                    value=match.group(0),
                    original=match.group(0),
                    confidence=0.85,
                    start=match.start(),
                    end=match.end(),
                    metadata={"date_type": "parsed"},
                ))

        # Durations
        for pattern in self.DURATION_PATTERNS:
            for match in re.finditer(pattern, text_lower):
                entities.append(Entity(
                    type="duration",
                    value=match.group(0),
                    original=match.group(0),
                    confidence=0.85,
                    start=match.start(),
                    end=match.end(),
                    metadata={"duration_type": "parsed"},
                ))

        return entities

    @staticmethod
    def _normalize_time(match: re.Match) -> str:
        """Normalize a time match to HH:MM format.

        Handles multiple group layouts from the three absolute-time patterns:
        - Pattern 1: (hour, minute, meridiem?)
        - Pattern 2: (hour, meridiem, minute?)   ← meridiem in groups[1]
        - Pattern 3: (hour, minute?, meridiem?)
        """
        groups = match.groups()
        if not groups:
            return ""

        hour = int(groups[0]) if groups[0] else 0
        meridiem = ""
        minute = 0

        if len(groups) >= 3 and groups[2] and groups[2].lower().replace(".", "").strip() in ("am", "pm"):
            # Pattern 1 or 3: (hour, minute, meridiem)
            minute = int(groups[1]) if groups[1] else 0
            meridiem = groups[2].lower().replace(".", "").strip()
        elif len(groups) >= 2 and groups[1] and groups[1].lower().replace(".", "").strip() in ("am", "pm"):
            # Pattern 2: (hour, meridiem, minute?)
            meridiem = groups[1].lower().replace(".", "").strip()
            minute = int(groups[2]) if len(groups) > 2 and groups[2] else 0
        elif len(groups) >= 2 and groups[1]:
            # (hour, minute) without meridiem
            try:
                minute = int(groups[1])
            except ValueError:
                pass

        if meridiem == "pm" and hour < 12:
            hour += 12
        elif meridiem == "am" and hour == 12:
            hour = 0

        return f"{hour:02d}:{minute:02d}"
