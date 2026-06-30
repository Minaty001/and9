"""
Retry Handler.

Executes operations with exponential backoff retry logic.
"""

from __future__ import annotations

import time
import random
import logging
from typing import Any, Callable, Optional, Tuple

logger = logging.getLogger(__name__)


class RetryHandler:
    """Handles retry logic with exponential backoff and jitter.

    Usage:
        handler = RetryHandler()
        success, result, attempts = handler.execute_with_retry(operation)
    """

    def __init__(self, max_retries: int = 3, backoff_ms: int = 1000, backoff_multiplier: float = 2.0):
        self._max_retries = max_retries
        self._backoff_ms = backoff_ms
        self._backoff_multiplier = backoff_multiplier
        self._total_attempts = 0
        self._total_successes = 0
        self._total_failures = 0

    def execute_with_retry(
        self, operation: Callable, max_retries: Optional[int] = None, backoff_ms: Optional[int] = None
    ) -> Tuple[bool, Any, int]:
        max_retries = max_retries if max_retries is not None else self._max_retries
        backoff_ms = backoff_ms if backoff_ms is not None else self._backoff_ms
        last_exception = None

        for attempt in range(1, max_retries + 2):
            self._total_attempts += 1
            try:
                result = operation()
                self._total_successes += 1
                return True, result, attempt
            except Exception as e:
                last_exception = e
                self._total_failures += 1
                logger.debug("Retry attempt %d/%d failed: %s", attempt, max_retries + 1, e)

                if attempt <= max_retries:
                    sleep_ms = backoff_ms * (self._backoff_multiplier ** (attempt - 1))
                    jitter = random.uniform(0, sleep_ms * 0.1)
                    sleep_seconds = (sleep_ms + jitter) / 1000.0
                    logger.debug("Backing off %.2f seconds before retry", sleep_seconds)
                    time.sleep(sleep_seconds)

        return False, last_exception, max_retries + 1

    def get_stats(self) -> dict:
        return {
            "total_attempts": self._total_attempts,
            "total_successes": self._total_successes,
            "total_failures": self._total_failures,
            "success_rate": round(self._total_successes / max(self._total_attempts, 1) * 100, 1),
        }

    def reset_stats(self) -> None:
        self._total_attempts = 0
        self._total_successes = 0
        self._total_failures = 0
