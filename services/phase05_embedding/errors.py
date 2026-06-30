"""
Phase 5 — Embedding Error Definitions.
"""

from typing import Any, Optional
from services.phase01_core.errors import ProcessingError


class EmbeddingError(ProcessingError):
    """Base embedding error."""

    def __init__(self, message: str, code: str = "EMBEDDING_ERROR", details: Any = None):
        super().__init__(message, code, details)


class DimensionMismatchError(EmbeddingError):
    """Raised when vector dimensions don't match."""

    def __init__(self, expected: int, actual: int):
        super().__init__(
            f"Dimension mismatch: expected {expected}, got {actual}",
            code="DIMENSION_MISMATCH",
            details={"expected": expected, "actual": actual},
        )


class EmbeddingCacheError(EmbeddingError):
    """Raised when cache operations fail."""

    def __init__(self, message: str, details: Any = None):
        super().__init__(message, "CACHE_ERROR", details)
