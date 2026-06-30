"""
Phase 33 — Error Recovery
==========================

Graceful degradation, retry policies, circuit breaker,
fallback mechanisms, and exception categorization.

Components:
    - CircuitBreaker: State machine (closed/open/half-open) with auto-recovery
    - RetryHandler: Exponential backoff with jitter
    - FallbackHandler: Fallback chain with graceful degradation
    - ErrorAnalyzer: Classify, suggest remedy, assess severity
    - ErrorRecoveryService: ServiceBase wrapper
"""

from .config import ErrorRecoveryConfig
from .models import ErrorContext, RecoveryStrategy
from .circuit_breaker import CircuitBreaker
from .retry_handler import RetryHandler
from .fallback_handler import FallbackHandler
from .error_analyzer import ErrorAnalyzer
from .user_messages import UserMessageGenerator
from .rollback_manager import RollbackManager
from .recovery_workflow import RecoveryWorkflow, StepState, RetryPolicy
from .service import ErrorRecoveryService

__all__ = [
    "ErrorRecoveryConfig",
    "ErrorContext",
    "RecoveryStrategy",
    "CircuitBreaker",
    "RetryHandler",
    "FallbackHandler",
    "ErrorAnalyzer",
    "UserMessageGenerator",
    "RollbackManager",
    "RecoveryWorkflow",
    "StepState",
    "RetryPolicy",
    "ErrorRecoveryService",
]
