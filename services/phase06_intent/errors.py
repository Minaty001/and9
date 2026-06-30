"""
Phase 6 — Intent Detection Error Definitions.
"""

from typing import Any, Optional
from services.phase01_core.errors import ProcessingError


class IntentError(ProcessingError):
    """Base intent detection error."""

    def __init__(self, message: str, code: str = "INTENT_ERROR", details: Any = None):
        super().__init__(message, code, details)


class ModelLoadError(IntentError):
    """Raised when model weights fail to load."""

    def __init__(self, path: str, reason: str = ""):
        msg = f"Failed to load model from '{path}'"
        if reason:
            msg += f": {reason}"
        super().__init__(msg, "MODEL_LOAD_ERROR", {"path": path})


class InferenceError(IntentError):
    """Raised when neural network inference fails."""

    def __init__(self, message: str, details: Any = None):
        super().__init__(message, "INFERENCE_ERROR", details)
