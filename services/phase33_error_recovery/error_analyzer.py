"""
Phase 33 — Error Analyzer.

Classifies errors, suggests remedies, and assesses severity.
"""

from __future__ import annotations

import re
import logging
from typing import Dict, Optional

from .config import ErrorRecoveryConfig
from .models import ErrorContext

logger = logging.getLogger(__name__)

# Patterns for error classification
TIMEOUT_PATTERNS = [
    re.compile(r"timeout", re.IGNORECASE),
    re.compile(r"timed?\s*out", re.IGNORECASE),
    re.compile(r"connection\s+timed?\s*out", re.IGNORECASE),
]

RESOURCE_PATTERNS = [
    re.compile(r"memory", re.IGNORECASE),
    re.compile(r"disk", re.IGNORECASE),
    re.compile(r"storage", re.IGNORECASE),
    re.compile(r"quota", re.IGNORECASE),
    re.compile(r"resource\s+exhausted", re.IGNORECASE),
    re.compile(r"too\s+many", re.IGNORECASE),
    re.compile(r"no\s+space", re.IGNORECASE),
]

VALIDATION_PATTERNS = [
    re.compile(r"invalid", re.IGNORECASE),
    re.compile(r"validation", re.IGNORECASE),
    re.compile(r"malformed", re.IGNORECASE),
    re.compile(r"bad\s+request", re.IGNORECASE),
    re.compile(r"unexpected\s+input", re.IGNORECASE),
    re.compile(r"ValueError", re.IGNORECASE),
    re.compile(r"TypeError", re.IGNORECASE),
]

AUTH_PATTERNS = [
    re.compile(r"unauthorized", re.IGNORECASE),
    re.compile(r"forbidden", re.IGNORECASE),
    re.compile(r"authenti", re.IGNORECASE),
    re.compile(r"permission", re.IGNORECASE),
    re.compile(r"access\s+denied", re.IGNORECASE),
    re.compile(r"403", re.IGNORECASE),
    re.compile(r"401", re.IGNORECASE),
]

SYSTEM_PATTERNS = [
    re.compile(r"system", re.IGNORECASE),
    re.compile(r"internal", re.IGNORECASE),
    re.compile(r"runtime", re.IGNORECASE),
    re.compile(r"crash", re.IGNORECASE),
    re.compile(r"segfault", re.IGNORECASE),
    re.compile(r"OSError", re.IGNORECASE),
    re.compile(r"RuntimeError", re.IGNORECASE),
]


class ErrorAnalyzer:
    """Analyzes errors to classify, assess severity, and suggest remedies.

    Usage:
        analyzer = ErrorAnalyzer(config)
        error_type = analyzer.classify(exception)
        remedy = analyzer.suggest_remedy(context)
        severity = analyzer.severity(context)
    """

    def __init__(self, config: Optional[ErrorRecoveryConfig] = None):
        self.config = config or ErrorRecoveryConfig()

    # ── Classification ───────────────────────────────────────────

    def classify(self, error: Exception) -> str:
        """Classify an error into a type category.

        Args:
            error: The exception to classify.

        Returns:
            Error type string: timeout/resource/validation/auth/system/unknown.
        """
        error_str = f"{error.__class__.__name__}: {str(error)}"

        for pattern in TIMEOUT_PATTERNS:
            if pattern.search(error_str):
                return "timeout"
        for pattern in RESOURCE_PATTERNS:
            if pattern.search(error_str):
                return "resource"
        for pattern in VALIDATION_PATTERNS:
            if pattern.search(error_str):
                return "validation"
        for pattern in AUTH_PATTERNS:
            if pattern.search(error_str):
                return "auth"
        for pattern in SYSTEM_PATTERNS:
            if pattern.search(error_str):
                return "system"

        return "unknown"

    # ── Severity Assessment ──────────────────────────────────────

    def severity(self, error_context: ErrorContext) -> str:
        """Assess the severity of an error.

        Args:
            error_context: The error context.

        Returns:
            Severity level: low/medium/high/critical.
        """
        error_type = error_context.error_type or self.classify(
            Exception(error_context.error)
        )

        # Critical
        if error_type == "system":
            if error_context.attempt_number > 1:
                return "critical"
            return "high"

        # High
        if error_type == "auth":
            return "high" if error_context.attempt_number > 2 else "medium"
        if error_type == "resource":
            return "high"

        # Medium
        if error_type == "timeout":
            return "medium"
        if error_type == "validation":
            return "medium"

        # Default
        return "low"

    # ── Remedy Suggestion ────────────────────────────────────────

    def suggest_remedy(self, error_context: ErrorContext) -> str:
        """Suggest a remedy for an error.

        Args:
            error_context: The error context.

        Returns:
            Suggested remedy string.
        """
        error_type = error_context.error_type or self.classify(
            Exception(error_context.error)
        )

        remedies = {
            "timeout": "Increase timeout duration or reduce load. Consider retrying with backoff.",
            "resource": "Free up system resources or increase capacity. Check memory, disk, and quotas.",
            "validation": "Check input format and constraints. Ensure all required fields are provided.",
            "auth": "Verify credentials and permissions. Ensure token is valid and not expired.",
            "system": "Restart the service or check system health. Investigate logs for root cause.",
            "unknown": "Check logs for details. Retry the operation. If persists, escalate to support.",
        }

        return remedies.get(error_type, "No specific remedy available.")

    # ── Context Extraction ───────────────────────────────────────

    def extract_context(self, error: Exception) -> dict:
        """Extract context information from an error.

        Args:
            error: The exception.

        Returns:
            Dict with error details.
        """
        return {
            "error_type": error.__class__.__name__,
            "error_message": str(error),
            "module": getattr(error, "__module__", ""),
            "args": list(error.args) if hasattr(error, "args") else [],
        }

    def analyze(self, exception: Exception, operation: str = "", attempt: int = 1) -> ErrorContext:
        """Full analysis of an exception into an ErrorContext.

        Args:
            exception: The exception to analyze.
            operation: The operation being performed.
            attempt: Current attempt number.

        Returns:
            ErrorContext with classification, severity, and remedy.
        """
        error_context = ErrorContext(
            error=str(exception),
            operation=operation,
            error_type=self.classify(exception),
            attempt_number=attempt,
        )
        error_context.severity = self.severity(error_context)
        error_context.suggested_remedy = self.suggest_remedy(error_context)
        return error_context
