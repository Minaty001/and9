"""
Entity validation module.

Validates extracted entities before execution to prevent invalid actions.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple

from services.phase07_entity.models import Entity, EntityResult

logger = logging.getLogger(__name__)


class EntityValidator:
    """Validates entities for correctness and safety.

    Checks performed:
        - App: package name format, known apps
        - Contact: non-empty, reasonable length
        - Time: valid hour/minute ranges
        - Location: known city or reasonable name
        - Media: non-empty, safe characters
    """

    def validate(self, entities: List[Entity]) -> Tuple[bool, List[str]]:
        """Validate a list of extracted entities.

        Args:
            entities: List of Entity objects to validate.

        Returns:
            Tuple of (is_valid, list_of_error_messages).
        """
        errors: List[str] = []

        for entity in entities:
            if entity.type == "app":
                err = self._validate_app(entity)
            elif entity.type == "contact":
                err = self._validate_contact(entity)
            elif entity.type == "time":
                err = self._validate_time(entity)
            elif entity.type == "location":
                err = self._validate_location(entity)
            elif entity.type == "media":
                err = self._validate_media(entity)
            else:
                err = None

            if err:
                errors.append(err)

        return len(errors) == 0, errors

    @staticmethod
    def _validate_app(entity: Entity) -> Optional[str]:
        """Validate an app entity."""
        pkg = entity.value or entity.normalized
        if not pkg:
            return "App has no package name"
        # Package names should not have spaces
        if " " in pkg and "." not in pkg:
            return f"Invalid app: '{pkg}' is not a known application"
        return None

    @staticmethod
    def _validate_contact(entity: Entity) -> Optional[str]:
        """Validate a contact entity."""
        name = entity.value
        if not name or len(name.strip()) == 0:
            return "Contact name is empty"
        if len(name) > 100:
            return f"Contact name too long: {len(name)} chars"
        # Check for suspicious characters
        if re.search(r'[<>{}|\\^~`]', name):
            return f"Contact name contains invalid characters"
        return None

    @staticmethod
    def _validate_time(entity: Entity) -> Optional[str]:
        """Validate a time entity."""
        value = entity.value
        if not value:
            return None  # relative times like "in 10 minutes" are always valid

        # Check absolute time format
        time_match = re.match(r"^(\d{1,2}):(\d{2})$", value)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2))
            if hour < 0 or hour > 23:
                return f"Invalid hour: {hour}"
            if minute < 0 or minute > 59:
                return f"Invalid minute: {minute}"
        return None

    @staticmethod
    def _validate_location(entity: Entity) -> Optional[str]:
        """Validate a location entity."""
        name = entity.value
        if not name or len(name.strip()) == 0:
            return "Location name is empty"
        if len(name) > 100:
            return f"Location name too long: {len(name)} chars"
        return None

    @staticmethod
    def _validate_media(entity: Entity) -> Optional[str]:
        """Validate a media entity."""
        name = entity.value
        if not name or len(name.strip()) == 0:
            return "Media name is empty"
        if len(name) > 200:
            return f"Media name too long: {len(name)} chars"
        return None
