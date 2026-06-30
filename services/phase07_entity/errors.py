"""
Phase 7 — Entity Extraction Errors.
"""

from typing import Any, Optional
from services.phase01_core.errors import ProcessingError


class EntityError(ProcessingError):
    """Base entity extraction error."""

    def __init__(self, message: str, code: str = "ENTITY_ERROR", details: Any = None):
        super().__init__(message, code, details)


class EntityValidationError(EntityError):
    """Raised when entity validation fails."""

    def __init__(self, entity_type: str, value: str, reason: str):
        super().__init__(
            f"Validation failed for '{entity_type}:{value}': {reason}",
            code="ENTITY_VALIDATION_ERROR",
            details={"type": entity_type, "value": value, "reason": reason},
        )


class AmbiguousEntityError(EntityError):
    """Raised when an entity cannot be resolved uniquely."""

    def __init__(self, entity_type: str, value: str, candidates: list):
        super().__init__(
            f"Ambiguous '{entity_type}': '{value}' has {len(candidates)} candidates",
            code="AMBIGUOUS_ENTITY",
            details={"type": entity_type, "value": value, "candidates": candidates},
        )
