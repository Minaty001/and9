"""
Rollback Manager.

Manages compensating actions for operations, executing rollbacks
in LIFO order with full history tracking.
"""

from __future__ import annotations

import time
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class RollbackManager:
    """Manages compensating actions (rollbacks) for operations.

    Operations can register a compensation function that undoes the
    operation. Rollbacks execute in LIFO (last-in-first-out) order.

    Usage:
        mgr = RollbackManager()
        mgr.register_compensation("op1", lambda: print("undo op1"))
        mgr.register_compensation("op2", lambda: print("undo op2"))
        mgr.rollback("op2")
        mgr.rollback_all()
    """

    def __init__(self):
        self._compensations: Dict[str, List[Tuple[Callable, tuple, dict]]] = {}
        self._execution_order: List[str] = []
        self._history: List[dict] = []

    def register_compensation(
        self,
        operation_id: str,
        compensation_func: Callable,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        if operation_id not in self._compensations:
            self._compensations[operation_id] = []
            self._execution_order.append(operation_id)
        self._compensations[operation_id].append((compensation_func, args, kwargs))
        logger.debug("Registered compensation for %s", operation_id)

    def rollback(self, operation_id: str) -> bool:
        compensations = self._compensations.get(operation_id)
        if not compensations:
            logger.warning("No compensations registered for %s", operation_id)
            return False

        all_success = True
        for func, args, kwargs in reversed(compensations):
            try:
                t0 = time.perf_counter()
                func(*args, **kwargs)
                elapsed = (time.perf_counter() - t0) * 1000
                self._history.append({
                    "operation_id": operation_id,
                    "status": "success",
                    "duration_ms": round(elapsed, 2),
                    "timestamp": time.time(),
                })
                logger.debug("Rollback of %s succeeded", operation_id)
            except Exception as e:
                t0_local = time.perf_counter()
                elapsed = (time.perf_counter() - t0_local) * 1000
                self._history.append({
                    "operation_id": operation_id,
                    "status": "failed",
                    "error": str(e),
                    "duration_ms": round(elapsed, 2),
                    "timestamp": time.time(),
                })
                logger.error("Rollback of %s failed: %s", operation_id, e)
                all_success = False

        if operation_id in self._compensations:
            del self._compensations[operation_id]
        if operation_id in self._execution_order:
            self._execution_order.remove(operation_id)

        return all_success

    def rollback_all(self) -> int:
        count = 0
        errors = 0
        for operation_id in reversed(list(self._execution_order)):
            success = self.rollback(operation_id)
            count += 1
            if not success:
                errors += 1
        logger.info("Rollback_all: %d operations processed, %d errors", count, errors)
        return count

    def get_history(self) -> List[dict]:
        return list(self._history)

    def get_registered_count(self) -> int:
        return len(self._compensations)

    def has_compensation(self, operation_id: str) -> bool:
        return operation_id in self._compensations

    def clear(self) -> None:
        self._compensations.clear()
        self._execution_order.clear()
        self._history.clear()
