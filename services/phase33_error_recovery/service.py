"""
Phase 33 — Error Recovery Service.

ServiceBase wrapper for the Error Recovery system.
"""

from __future__ import annotations

import time
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

from services.base.service_base import ServiceBase
from .config import ErrorRecoveryConfig
from .models import ErrorContext, RecoveryStrategy
from .circuit_breaker import CircuitBreaker
from .retry_handler import RetryHandler
from .fallback_handler import FallbackHandler
from .error_analyzer import ErrorAnalyzer
from .user_messages import UserMessageGenerator
from .rollback_manager import RollbackManager
from .recovery_workflow import RecoveryWorkflow

logger = logging.getLogger(__name__)


class ErrorRecoveryService(ServiceBase):
    """Error recovery service with retry, circuit breaker, fallback, and analysis.

    Usage:
        svc = ErrorRecoveryService()
        await svc.initialize()
        success, result, ctx = await svc.execute_with_recovery(
            "my_operation", lambda: risky_call(),
        )
    """

    def __init__(self, config: Optional[ErrorRecoveryConfig] = None):
        super().__init__(name="jarvis_error_recovery", version="1.0.0")
        self.config = config or ErrorRecoveryConfig()
        self.retry_handler: Optional[RetryHandler] = None
        self.circuit_breaker: Optional[CircuitBreaker] = None
        self.fallback_handler: Optional[FallbackHandler] = None
        self.error_analyzer: Optional[ErrorAnalyzer] = None
        self.user_message_generator: Optional[UserMessageGenerator] = None
        self.rollback_manager: Optional[RollbackManager] = None
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._start_time = 0.0

    async def initialize(self) -> bool:
        self._start_time = time.time()
        try:
            self.retry_handler = RetryHandler(self.config)
            self.circuit_breaker = CircuitBreaker("default", self.config)
            self.fallback_handler = FallbackHandler(self.config)
            self.error_analyzer = ErrorAnalyzer(self.config)
            self.user_message_generator = UserMessageGenerator()
            self.rollback_manager = RollbackManager()
            self._metrics.reset()
            self._initialized = True
            logger.info("ErrorRecoveryService initialized")
            return True
        except Exception as e:
            logger.error("ErrorRecoveryService init failed: %s", e)
            return False

    async def shutdown(self) -> None:
        logger.info("ErrorRecoveryService shutting down...")
        # Execute any pending rollbacks
        if self.rollback_manager:
            self.rollback_manager.rollback_all()
        self._initialized = False

    async def execute_with_recovery(
        self,
        first_arg,
        second_arg=None,
        *,
        service_name: str = "",
        operation: str = "",
        fallback_operations: Optional[List[Callable]] = None,
        max_retries: Optional[int] = None,
    ) -> Tuple[bool, Any, str]:
        """Execute an operation with full recovery support.

        Supports two calling conventions:
          1) execute_with_recovery(operation_name: str, operation: Callable, ...)
          2) execute_with_recovery(operation: Callable, service_name=..., operation=...)

        Applies circuit breaker + retry + fallback chain.

        Returns:
            Tuple of (success, result, action_taken).
        """
        if not self.error_analyzer:
            raise RuntimeError("ErrorRecoveryService not initialized")

        # Determine operation_name and operation callable
        if callable(first_arg):
            operation_callable = first_arg
            operation_name = operation or service_name or "unknown"
        else:
            operation_name = first_arg or "unknown"
            operation_callable = second_arg

        # Track action taken for return
        action_taken = "none"

        error_context = ErrorContext(error="", operation=operation_name, service_name=service_name)
        t0 = time.perf_counter()

        try:
            # Circuit breaker check
            cb = self._get_circuit_breaker(operation_name)
            if self.config.enable_circuit_breaker:
                if not cb.is_available():
                    # Try fallback
                    if fallback_operations and self.config.enable_fallback:
                        fb_result = await self._execute_fallback(operation_name, fallback_operations)
                        elapsed = (time.perf_counter() - t0) * 1000
                        self._metrics.histogram("recovery_time_ms", elapsed)
                        return True, fb_result, "fallback"

                    self._metrics.counter("circuit_open_rejections", 1)
                    return False, None, "degrade"

            # Retry logic
            if self.config.enable_retry and self.retry_handler:
                max_r = max_retries if max_retries is not None else self.config.max_retries

                for attempt in range(1, max_r + 2):
                    try:
                        result = operation_callable()
                        elapsed = (time.perf_counter() - t0) * 1000
                        cb._on_success()
                        self._metrics.counter("recoveries_success", 1)
                        self._metrics.histogram("recovery_time_ms", elapsed)
                        return True, result, "retry"
                    except Exception as e:
                        error_context = self.error_analyzer.analyze(e, operation_name, attempt)
                        cb._on_failure()
                        if attempt <= max_r:
                            # Backoff and retry
                            backoff_ms = self.config.retry_backoff_ms * (
                                self.config.retry_backoff_multiplier ** (attempt - 1)
                            )
                            time.sleep(backoff_ms / 1000.0)
                            continue
                        raise
                raise Exception("Max retries exceeded")
            else:
                # No retry, just try once
                result = operation_callable()
                elapsed = (time.perf_counter() - t0) * 1000
                self._metrics.counter("recoveries_success", 1)
                self._metrics.histogram("recovery_time_ms", elapsed)
                return True, result, "retry"

        except Exception as e:
            # Final fallback attempt
            elapsed = (time.perf_counter() - t0) * 1000
            self._metrics.histogram("recovery_time_ms", elapsed)
            self._metrics.counter("recoveries_failed", 1)

            if fallback_operations and self.config.enable_fallback:
                try:
                    fb_result = await self._execute_fallback(operation_name, fallback_operations)
                    return True, fb_result, "fallback"
                except Exception:
                    pass

            return False, e, "degrade"

    async def _execute_fallback(
        self, operation_name: str, fallback_operations: List[Callable]
    ) -> Any:
        """Execute fallback chain."""
        if not self.fallback_handler:
            raise RuntimeError("FallbackHandler not initialized")
        return self.fallback_handler.execute_with_fallback(
            fallback_operations[0], fallback_operations[1:]
        )

    async def analyze_error(self, error: Exception, operation: str = "") -> ErrorContext:
        """Analyze an error and return context with classification, severity, remedy.

        Args:
            error: The exception.
            operation: The operation name.

        Returns:
            ErrorContext.
        """
        if not self.error_analyzer:
            raise RuntimeError("ErrorRecoveryService not initialized")
        return self.error_analyzer.analyze(error, operation)

    async def get_circuit_breaker_status(self, name: str = "default") -> dict:
        """Get circuit breaker status.

        Args:
            name: Circuit breaker name.

        Returns:
            Status dict.
        """
        cb = self._get_circuit_breaker(name)
        return cb.get_status()

    async def reset_circuit_breaker(self, name: str = "default") -> bool:
        """Reset a circuit breaker.

        Args:
            name: Circuit breaker name.

        Returns:
            True if reset.
        """
        cb = self._get_circuit_breaker(name)
        cb.reset()
        self._metrics.counter("circuit_breaker_resets", 1)
        return True

    async def get_retry_stats(self) -> dict:
        """Get retry handler statistics.

        Returns:
            Dict with stats.
        """
        if not self.retry_handler:
            raise RuntimeError("ErrorRecoveryService not initialized")
        return self.retry_handler.get_stats()

    # ── User Message Generation ───────────────────────────────────

    async def generate_user_message(self, context: ErrorContext) -> str:
        """Generate a user-facing message from error context.

        Args:
            context: The ErrorContext.

        Returns:
            User-friendly message string.
        """
        if not self.user_message_generator:
            raise RuntimeError("ErrorRecoveryService not initialized")
        message = self.user_message_generator.generate(context)
        # Store on the context
        context.user_message = message
        return message

    async def generate_user_message_for_error(
        self, error: Exception, operation: str = "",
    ) -> str:
        """Convenience: analyze error and generate user message in one call.

        Args:
            error: The exception.
            operation: The operation name.

        Returns:
            User-friendly message string.
        """
        if not self.error_analyzer or not self.user_message_generator:
            raise RuntimeError("ErrorRecoveryService not initialized")
        context = self.error_analyzer.analyze(error, operation)
        return await self.generate_user_message(context)

    # ── Rollback Management ───────────────────────────────────────

    async def register_compensation(
        self,
        operation_id: str,
        compensation_func: Callable,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Register a compensating action for an operation.

        Args:
            operation_id: Unique operation identifier.
            compensation_func: Callable to undo the operation.
            *args: Positional args for the compensation function.
            **kwargs: Keyword args for the compensation function.
        """
        if not self.rollback_manager:
            raise RuntimeError("ErrorRecoveryService not initialized")
        self.rollback_manager.register_compensation(
            operation_id, compensation_func, *args, **kwargs,
        )

    async def rollback(self, operation_id: str) -> bool:
        """Roll back a specific operation.

        Args:
            operation_id: The operation to roll back.

        Returns:
            True if all compensations succeeded.
        """
        if not self.rollback_manager:
            raise RuntimeError("ErrorRecoveryService not initialized")
        return self.rollback_manager.rollback(operation_id)

    async def rollback_all(self) -> int:
        """Roll back all registered operations in LIFO order.

        Returns:
            Number of operations rolled back.
        """
        if not self.rollback_manager:
            raise RuntimeError("ErrorRecoveryService not initialized")
        return self.rollback_manager.rollback_all()

    async def get_rollback_history(self) -> list:
        """Get rollback execution history.

        Returns:
            List of rollback history dicts.
        """
        if not self.rollback_manager:
            raise RuntimeError("ErrorRecoveryService not initialized")
        return self.rollback_manager.get_history()

    # ── Recovery Workflow ─────────────────────────────────────────

    async def create_recovery_workflow(self, name: str = "default") -> RecoveryWorkflow:
        """Create a new recovery workflow.

        Args:
            name: Workflow name.

        Returns:
            A new RecoveryWorkflow instance.
        """
        if not self.rollback_manager:
            raise RuntimeError("ErrorRecoveryService not initialized")
        return RecoveryWorkflow(name=name, rollback_manager=self.rollback_manager)

    async def execute_recovery_workflow(
        self, workflow: RecoveryWorkflow, context: ErrorContext,
    ) -> tuple:
        """Execute a recovery workflow.

        Args:
            workflow: The RecoveryWorkflow to execute.
            context: The ErrorContext.

        Returns:
            Tuple of (success, context).
        """
        return workflow.execute(context)

    async def get_workflow_progress(self, workflow: RecoveryWorkflow) -> dict:
        """Get progress of a recovery workflow.

        Args:
            workflow: The RecoveryWorkflow.

        Returns:
            Dict with progress details.
        """
        return workflow.get_progress()

    def _get_circuit_breaker(self, name: str) -> CircuitBreaker:
        """Get or create a circuit breaker by name."""
        if name not in self._circuit_breakers:
            self._circuit_breakers[name] = CircuitBreaker(name, self.config)
        return self._circuit_breakers[name]

    async def health(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        cb_status = {
            name: cb.state
            for name, cb in self._circuit_breakers.items()
        } if self._circuit_breakers else {"default": "closed"}
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "service_name": self.name,
            "version": self.version,
            "initialized": self._initialized,
            "uptime_seconds": round(uptime, 1),
            "circuit_breakers": cb_status,
        }

    async def stats(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        return {
            "service": self.name,
            "version": self.version,
            "uptime_seconds": round(uptime, 1),
            "circuit_breakers": {
                name: cb.get_status()
                for name, cb in self._circuit_breakers.items()
            },
            "retry_stats": self.retry_handler.get_stats() if self.retry_handler else {},
            "metrics": self._metrics.snapshot(),
        }
