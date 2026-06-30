"""
Fallback Handler.

Manages fallback chains for graceful degradation when operations fail.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ErrorContext:
    """Context information for an error."""

    def __init__(self, error: str, service_name: str = "", operation: str = "",
                 parameters: Optional[Dict] = None, error_type: str = "unknown",
                 severity: str = "medium", attempt_number: int = 1,
                 suggested_remedy: str = "", user_message: str = ""):
        self.error = error
        self.service_name = service_name
        self.operation = operation
        self.parameters = parameters or {}
        self.error_type = error_type
        self.severity = severity
        self.attempt_number = attempt_number
        self.suggested_remedy = suggested_remedy
        self.user_message = user_message


class FallbackHandler:
    """Handles fallback chains for graceful degradation.

    Usage:
        handler = FallbackHandler()
        result = handler.execute_with_fallback(
            primary_operation,
            [fallback1, fallback2]
        )
    """

    def __init__(self, max_fallback_depth: int = 3):
        self._max_fallback_depth = max_fallback_depth
        self._fallback_registry: Dict[str, List[Callable]] = {}

    def register_fallback(self, operation_name: str, fallback: Callable) -> None:
        if operation_name not in self._fallback_registry:
            self._fallback_registry[operation_name] = []
        self._fallback_registry[operation_name].append(fallback)
        logger.debug("Registered fallback for %s", operation_name)

    def find_fallback(self, operation_name: str, context: Optional[ErrorContext] = None) -> Optional[Callable]:
        fallbacks = self._fallback_registry.get(operation_name, [])
        if fallbacks:
            return fallbacks[0]
        return None

    def execute_with_fallback(
        self,
        operation: Callable,
        fallback_operations: Optional[List[Callable]] = None,
    ) -> Any:
        all_ops = [operation] + (fallback_operations or [])

        if len(all_ops) > self._max_fallback_depth + 1:
            all_ops = all_ops[: self._max_fallback_depth + 1]

        last_exception = None
        for i, op in enumerate(all_ops):
            try:
                result = op()
                logger.debug("Fallback chain: op %d succeeded", i)
                return result
            except Exception as e:
                last_exception = e
                logger.debug("Fallback chain: op %d failed: %s", i, e)

        raise last_exception  # type: ignore

    def clear(self) -> None:
        self._fallback_registry.clear()
