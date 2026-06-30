"""
App/package name entity extractor.

Extracts application names from user queries, mapping to known
package names for Android execution.

Based on existing patterns from backend/cognition/planner/entity_extractor.py
"""

import re
from typing import Dict, List, Optional, Tuple

from services.phase07_entity.models import Entity


class AppExtractor:
    """Extract app/package names from queries.

    Maps common app names and Hindi variants to Android package names.

    Usage:
        extractor = AppExtractor()
        entities = extractor.extract("open whatsapp")
        # [Entity(type="app", value="com.whatsapp", original="whatsapp", ...)]
    """

    # Known app mapping: display name → package name
    KNOWN_APPS: Dict[str, str] = {
        "whatsapp": "com.whatsapp",
        "youtube": "com.google.android.youtube",
        "chrome": "com.android.chrome",
        "telegram": "org.telegram.messenger",
        "instagram": "com.instagram.android",
        "gmail": "com.google.android.gm",
        "maps": "com.google.android.apps.maps",
        "camera": "com.android.camera2",
        "phone": "com.android.dialer",
        "contacts": "com.android.contacts",
        "gallery": "com.android.gallery3d",
        "settings": "com.android.settings",
        "calculator": "com.android.calculator2",
        "calendar": "com.android.calendar",
        "clock": "com.android.deskclock",
        "alarm": "com.android.deskclock",
        "play store": "com.android.vending",
        "playstore": "com.android.vending",
        "spotify": "com.spotify.music",
        "files": "com.android.documentsui",
        "messages": "com.android.messaging",
        "twitter": "com.twitter.android",
        "x": "com.twitter.android",
        "facebook": "com.facebook.katana",
        "linkedin": "com.linkedin.android",
        "netflix": "com.netflix.mediaclient",
        "prime video": "com.amazon.avod.thirdpartyclient",
        "hotstar": "in.startv.hotstar",
        "zomato": "com.application.zomato",
        "swiggy": "in.swiggy.android",
        "uber": "com.ubercab",
        "ola": "com.olacabs.customer",
        "flipkart": "com.flipkart.android",
        "amazon": "in.amazon.mShop.android.shopping",
        "myntra": "com.myntra.android",
    }

    # Hindi name variants
    HINDI_VARIANTS: Dict[str, str] = {
        "व्हाट्सएप": "whatsapp",
        "यूट्यूब": "youtube",
        "क्रोम": "chrome",
        "कैमरा": "camera",
        "फ़ोन": "phone",
        "सेटिंग": "settings",
        "गैलरी": "gallery",
        "मैसेज": "messages",
        "कैलकुलेटर": "calculator",
        "कैलेंडर": "calendar",
        "घड़ी": "clock",
        "मैप": "maps",
    }

    # Trigger patterns for app-related queries
    TRIGGER_PATTERNS = [
        r"(?:open|launch|start|run|kholo|chalao|खोलो|चलाओ)\s+(\w+(?:\s+\w+)?)",
        r"(?:go to|jump to|switch to)\s+(\w+(?:\s+\w+)?)",
        r"(?:close|exit|band|kill)\s+(\w+(?:\s+\w+)?)",
        r"(\w+(?:\s+\w+)?)\s+(?:app|application|program)",
        r"(?:app|application|program)\s+(\w+(?:\s+\w+)?)",
    ]

    def extract(self, text: str) -> List[Entity]:
        """Extract app names from query text.

        Args:
            text: The query text.

        Returns:
            List of Entity objects for each detected app.
        """
        if not text:
            return []

        entities: List[Entity] = []
        text_lower = text.lower().strip()
        seen: set = set()

        # 1. Direct match on known apps
        for name in sorted(self.KNOWN_APPS.keys(), key=len, reverse=True):
            if name in text_lower and name not in seen:
                seen.add(name)
                pkg = self.KNOWN_APPS[name]
                idx = text_lower.find(name)
                entities.append(Entity(
                    type="app",
                    value=pkg,
                    original=name,
                    confidence=0.95,
                    start=idx,
                    end=idx + len(name),
                    normalized=name,
                    metadata={"app_name": name, "package": pkg},
                ))

        # 2. Pattern-based extraction for generic app names
        for pattern in self.TRIGGER_PATTERNS:
            for match in re.finditer(pattern, text_lower):
                app_name = match.group(1)
                if app_name not in seen and app_name not in ("the", "an", "app", "application"):
                    seen.add(app_name)
                    entities.append(Entity(
                        type="app",
                        value=app_name,
                        original=app_name,
                        confidence=0.7,
                        start=match.start(1),
                        end=match.end(1),
                        normalized=app_name,
                        metadata={"app_name": app_name, "package": None},
                    ))

        return entities

    def resolve_package(self, app_name: str) -> Optional[str]:
        """Resolve an app name to a known package name.

        Args:
            app_name: Display name of the app.

        Returns:
            Package name string, or None if unknown.
        """
        return self.KNOWN_APPS.get(app_name.lower().strip())
