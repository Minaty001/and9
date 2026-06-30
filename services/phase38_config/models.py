"""
Phase 38 — Configuration System Models.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ConfigEntry(BaseModel):
    """A single configuration entry."""

    key: str = Field(..., description="Configuration key")
    value: Any = Field(..., description="Configuration value")
    source: str = Field(default="memory", description="Source of this config value")
    profile: str = Field(default="default", description="Profile this entry belongs to")
    description: str = Field(default="", description="Human-readable description")
    value_type: str = Field(default="str", description="Expected type string")
    is_secret: bool = Field(default=False, description="Whether this value is secret")
    is_immutable: bool = Field(default=False, description="Whether this value can be changed")
    validation_rules: str = Field(default="", description="JSON-encoded validation rules")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConfigSource(BaseModel):
    """A configuration source definition."""

    type: str = Field(..., description="Source type: memory/file/env")
    priority: int = Field(default=100, description="Priority (lower = higher priority)")
    is_writable: bool = Field(default=False, description="Whether this source can be written to")


class ValidationError(BaseModel):
    """A validation error for a config value."""

    key: str = Field(..., description="Config key that failed validation")
    value: Any = Field(default=None, description="The invalid value")
    expected_type: str = Field(default="", description="Expected type")
    rule: str = Field(default="", description="Validation rule that failed")
    message: str = Field(default="", description="Human-readable error message")
