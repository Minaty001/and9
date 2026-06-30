"""
app/core/errors/ — Error Recovery

Graceful degradation, retry policies, circuit breaker,
fallback mechanisms, and exception categorization.
"""

from .circuit_breaker import CircuitBreaker
from .retry_handler import RetryHandler
from .fallback_handler import FallbackHandler
from .error_analyzer import ErrorAnalyzer
from .user_messages import UserMessageGenerator
from .rollback_manager import RollbackManager
from .recovery_workflow import RecoveryWorkflow, StepState, RetryPolicy

__all__ = [
    "CircuitBreaker",
    "RetryHandler",
    "FallbackHandler",
    "ErrorAnalyzer",
    "UserMessageGenerator",
    "RollbackManager",
    "RecoveryWorkflow",
    "StepState",
    "RetryPolicy",
]
