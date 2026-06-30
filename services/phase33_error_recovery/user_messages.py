"""
Phase 33 — User Message Generator.

Generates user-facing error messages from error context,
with severity-based prefix mapping.
"""

from __future__ import annotations

from typing import Optional

from .models import ErrorContext

# Templates for each classified error type
ERROR_TYPE_TEMPLATES = {
    "timeout": "The operation is taking longer than expected. Please try again.",
    "resource": "A system resource is unavailable right now.",
    "validation": "There was an issue with the input provided.",
    "auth": "You don't have permission to do that.",
    "system": "Something went wrong on our end. Please try again.",
    "unknown": "An unexpected error occurred.",
}

# Severity → user-facing prefix mapping
SEVERITY_PREFIXES = {
    "low": "Info: ",
    "medium": "Warning: ",
    "high": "Error: ",
    "critical": "Alert: ",
}


class UserMessageGenerator:
    """Generates user-facing messages from ErrorContext.

    Usage:
        generator = UserMessageGenerator()
        msg = generator.generate(context)
    """

    def generate(self, context: ErrorContext) -> str:
        """Produce a user-facing message from an error context.

        Args:
            context: The ErrorContext describing the error.

        Returns:
            A user-friendly message string.
        """
        error_type = context.error_type or "unknown"
        template = ERROR_TYPE_TEMPLATES.get(error_type, ERROR_TYPE_TEMPLATES["unknown"])
        prefix = SEVERITY_PREFIXES.get(context.severity, "")
        return prefix + template

    def get_template(self, error_type: str) -> str:
        """Get the message template for a given error type.

        Args:
            error_type: The error type string.

        Returns:
            The template string.
        """
        return ERROR_TYPE_TEMPLATES.get(error_type, ERROR_TYPE_TEMPLATES["unknown"])
