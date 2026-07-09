"""
app/core/observability.py — Health + metrics for AND9

Exposes a /health endpoint with:
  - Kernel status
  - All service statuses
  - RAM + CPU snapshot
  - Task queue depth
  - Request counters
  - Error rates
"""

import logging
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.core.kernel import AND9Kernel

logger = logging.getLogger(__name__)
_request_count = 0
_error_count = 0


class Observability:
    def __init__(self, kernel: "AND9Kernel"):
        self._kernel = kernel

    def report(self) -> dict:
        """Full health report for /health endpoint."""
        global _request_count, _error_count
        kernel_health = self._kernel.health()
        return {
            "and9_version": "5.0",
            "status": "running",
            "requests_total": _request_count,
            "errors_total": _error_count,
            "error_rate": round(_error_count / max(_request_count, 1), 4),
            **kernel_health,
        }

    @staticmethod
    def record_request() -> None:
        global _request_count
        _request_count += 1

    @staticmethod
    def record_error() -> None:
        global _error_count
        _error_count += 1