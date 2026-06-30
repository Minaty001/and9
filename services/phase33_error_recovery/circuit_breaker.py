"""
Phase 33 — Circuit Breaker.

State machine with closed/open/half-open states that prevents
calls to a failing operation and auto-recovers after a timeout.
"""

from __future__ import annotations

import time
import logging
from typing import Any, Callable, Optional

from .config import ErrorRecoveryConfig

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Circuit breaker with three states: closed, open, half-open.

    Usage:
        cb = CircuitBreaker(config)
        result = cb.call(operation, fallback=lambda: "default")
    """

    def __init__(self, name: str = "default", config: Optional[ErrorRecoveryConfig] = None):
        self.name = name
        self.config = config or ErrorRecoveryConfig()
        self.state = "closed"  # closed, open, half-open
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.threshold = self.config.circuit_breaker_threshold
        self.reset_timeout = self.config.circuit_breaker_reset_timeout

    def call(self, operation: Callable, fallback: Optional[Callable] = None) -> Any:
        """Execute an operation with circuit breaker protection.

        Args:
            operation: The operation to execute.
            fallback: Optional fallback if circuit is open.

        Returns:
            Operation result or fallback result.

        Raises:
            Exception: If circuit is open and no fallback.
        """
        if self.state == "open":
            if time.time() - self.last_failure_time >= self.reset_timeout:
                logger.debug("Circuit %s: open -> half-open", self.name)
                self.state = "half-open"
            else:
                logger.debug("Circuit %s: open, using fallback", self.name)
                if fallback:
                    self._record_metrics("circuit_open_fallback")
                    return fallback()
                raise Exception(f"Circuit breaker '{self.name}' is open")

        try:
            result = operation()
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            if fallback:
                logger.debug("Circuit %s: operation failed, using fallback", self.name)
                self._record_metrics("circuit_fallback")
                return fallback()
            raise

    def _on_success(self) -> None:
        """Handle a successful operation."""
        if self.state == "half-open":
            logger.info("Circuit %s: half-open -> closed (success)", self.name)
            self.state = "closed"
        self.failure_count = 0
        self._record_metrics("circuit_success")

    def _on_failure(self) -> None:
        """Handle a failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == "half-open":
            logger.warning("Circuit %s: half-open -> open (failure)", self.name)
            self.state = "open"
        elif self.failure_count >= self.threshold and self.state == "closed":
            logger.warning(
                "Circuit %s: closed -> open (%d failures)",
                self.name, self.failure_count,
            )
            self.state = "open"

        self._record_metrics("circuit_failure")

    def _record_metrics(self, event: str) -> None:
        """Record a circuit breaker event."""
        logger.debug("Circuit %s: %s (state=%s, failures=%d)", self.name, event, self.state, self.failure_count)

    def reset(self) -> None:
        """Reset the circuit breaker to closed state."""
        self.state = "closed"
        self.failure_count = 0
        self.last_failure_time = 0.0
        logger.info("Circuit %s: reset to closed", self.name)

    def get_status(self) -> dict:
        """Get current circuit breaker status.

        Returns:
            Dict with state, failure_count, etc.
        """
        return {
            "name": self.name,
            "state": self.state,
            "failure_count": self.failure_count,
            "threshold": self.threshold,
            "reset_timeout": self.reset_timeout,
            "last_failure_time": self.last_failure_time,
        }

    def is_available(self) -> bool:
        """Check if the circuit breaker allows calls.

        Returns:
            True if state is closed or half-open.
        """
        if self.state == "open":
            if self.last_failure_time > 0 and time.time() - self.last_failure_time >= self.reset_timeout:
                return True
            return False
        return True

    def __repr__(self) -> str:
        return f"CircuitBreaker(name={self.name}, state={self.state}, failures={self.failure_count})"
