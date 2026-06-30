"""
Phase 4 — Tokenizer Error Definitions.
"""

from typing import Any, Optional
from services.phase01_core.errors import ProcessingError


class TokenizerError(ProcessingError):
    """Base tokenizer error."""

    def __init__(self, message: str, code: str = "TOKENIZER_ERROR", details: Any = None):
        super().__init__(message, code, details)


class InputTooLongError(TokenizerError):
    """Raised when input exceeds maximum length."""

    def __init__(self, length: int, max_length: int):
        super().__init__(
            f"Input too long: {length} chars (max {max_length})",
            code="INPUT_TOO_LONG",
            details={"length": length, "max_length": max_length},
        )


class EmptyInputError(TokenizerError):
    """Raised when input is empty."""

    def __init__(self):
        super().__init__("Empty input provided", code="EMPTY_INPUT")


class NormalizationError(TokenizerError):
    """Raised when text normalization fails."""

    def __init__(self, message: str, details: Any = None):
        super().__init__(message, "NORMALIZATION_ERROR", details)
