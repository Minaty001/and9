"""
Phase 31 — Security Models.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SecurityEvent(BaseModel):
    """A security event entry for audit logging."""

    event_type: str = Field(..., description="Type: auth/sanitization/validation/encryption/audit")
    severity: str = Field(default="low", description="Severity: low/medium/high/critical")
    source: str = Field(default="", description="Source component")
    details: dict = Field(default_factory=dict, description="Event details")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: str = Field(default="", description="Associated user ID")
    ip_address: str = Field(default="", description="Source IP address")
    blocked: bool = Field(default=False, description="Whether action was blocked")


class ValidationResult(BaseModel):
    """Result of input validation."""

    is_valid: bool = Field(default=True, description="Whether input is valid")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    sanitized_input: str = Field(default="", description="Sanitized version of input")
    risk_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Risk score 0-1")
    blocked_chars_found: list = Field(default_factory=list, description="Blocked characters found")
    warnings: list = Field(default_factory=list, description="Warning messages")
    prompt_injection_detected: bool = Field(default=False, description="Whether prompt injection was detected")
    prompt_injection_patterns: list = Field(default_factory=list, description="Detected prompt injection patterns")
