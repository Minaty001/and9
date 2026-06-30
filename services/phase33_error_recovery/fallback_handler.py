"""
Phase 33 — Fallback Handler.

Manages fallback chains for graceful degradation when operations fail.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

from .config import ErrorRecoveryConfig
from .models import ErrorContext

logger = logging.getLogger(__name__)


class FallbackHandler:
    """Handles fallback chains for graceful degradation.

    Usage:
        handler = FallbackHandler(config)
        result = handler.execute_with_fallback(
            primary_operation,
            [fallback1, fallback2]
        )
    """

    def __init__(self, config: Optional[ErrorRecoveryConfig] = None):
        self.config = config or ErrorRecoveryConfig()
        self._fallback_registry: Dict[str, List[Callable]] = {}

    def register_fallback(self, operation_name: str, fallback: Callable) -> None:
        """Register a fallback for a named operation.

        Args:
            operation_name: Name of the operation.
            fallback: Fallback callable.
        """
        if operation_name not in self._fallback_registry:
            self._fallback_registry[operation_name] = []
        self._fallback_registry[operation_name].append(fallback)
        logger.debug("Registered fallback for %s", operation_name)

    def find_fallback(self, operation_name: str, context: Optional[ErrorContext] = None) -> Optional[Callable]:
        """Find a suitable fallback for an operation.

        Args:
            operation_name: The operation name.
            context: Error context for context-aware fallbacks.

        Returns:
            A fallback callable or None.
        """
        fallbacks = self._fallback_registry.get(operation_name, [])
        if fallbacks:
            return fallbacks[0]
        return None

    def execute_with_fallback(
        self,
        operation: Callable,
        fallback_operations: Optional[List[Callable]] = None,
    ) -> Any:
        """Execute an operation with fallback chain.

        Tries each fallback in sequence if the primary fails.

        Args:
            operation: Primary operation.
            fallback_operations: List of fallback callables.

        Returns:
            Result from the first successful callable.

        Raises:
            Exception: If all operations fail.
        """
        all_ops = [operation] + (fallback_operations or [])

        if len(all_ops) > self.config.max_fallback_depth + 1:
            all_ops = all_ops[: self.config.max_fallback_depth + 1]

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
        """Clear all registered fallbacks."""
        self._fallback_registry.clear()
