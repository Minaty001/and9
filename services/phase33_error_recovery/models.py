"""
Phase 33 — Error Recovery Models.
"""

from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field


class ErrorContext(BaseModel):
    """Context information for an error."""

    error: str = Field(..., description="Error message")
    service_name: str = Field(default="", description="Service where error occurred")
    operation: str = Field(default="", description="Operation being performed")
    parameters: dict = Field(default_factory=dict, description="Operation parameters")
    error_type: str = Field(default="unknown", description="Classified error type")
    severity: str = Field(default="medium", description="Severity: low/medium/high/critical")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    attempt_number: int = Field(default=1, description="Current attempt number")
    suggested_remedy: str = Field(default="", description="Suggested remedy")
    user_message: str = Field(default="", description="User-facing message")

    def __getitem__(self, key):
        """Support dict-like access for backward compatibility."""
        return getattr(self, key)

    def __contains__(self, key):
        """Support 'in' operator for backward compatibility."""
        return hasattr(self, key) and key in self.model_fields


class RecoveryStrategy(BaseModel):
    """A recovery strategy definition."""

    strategy_type: str = Field(..., description="retry/circuit_breaker/fallback/degrade/ignore")
    is_applicable: Callable = Field(default=lambda ctx: True, description="Check if applicable")
    priority: int = Field(default=0, description="Priority (higher = tried first)")
    description: str = Field(default="", description="Strategy description")

    class Config:
        arbitrary_types_allowed = True
