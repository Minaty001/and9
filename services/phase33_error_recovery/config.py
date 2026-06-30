"""
Phase 33 — Error Recovery Configuration.
"""

from pydantic import Field
from services.base.config_base import BaseConfig


class ErrorRecoveryConfig(BaseConfig):
    """Configuration for the error recovery system."""

    service_name: str = Field(default="jarvis_error_recovery", description="Error recovery service name")
    enable_retry: bool = Field(default=True, description="Enable retry mechanism")
    enable_circuit_breaker: bool = Field(default=True, description="Enable circuit breaker")
    enable_fallback: bool = Field(default=True, description="Enable fallback mechanism")
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")
    retry_backoff_ms: int = Field(default=1000, ge=100, le=60000, description="Base backoff in ms")
    retry_backoff_multiplier: float = Field(default=2.0, ge=1.0, le=10.0, description="Backoff multiplier")
    circuit_breaker_threshold: int = Field(default=5, ge=1, le=100, description="Failures before open")
    circuit_breaker_reset_timeout: int = Field(default=30, ge=1, le=300, description="Seconds before half-open")
    max_fallback_depth: int = Field(default=3, ge=0, le=10, description="Max fallback chain depth")
    enable_state_recovery: bool = Field(default=True, description="Enable state recovery")

    model_config = {"env_prefix": "JARVIS_PHASE33_"}
