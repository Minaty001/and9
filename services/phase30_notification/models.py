"""
Phase 30 — Notification Manager Models.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Notification(BaseModel):
    """A single notification message."""

    id: str = Field(..., description="Unique notification identifier")
    type: str = Field(..., description="Type: info/warning/error/success/reminder/alert")
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message body")
    priority: str = Field(default="normal", description="Priority: critical/high/normal/low")
    channel: str = Field(default="general", description="Notification channel")
    source: str = Field(default="system", description="Source service")
    data: Dict[str, Any] = Field(default_factory=dict, description="Additional data payload")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = Field(default=None, description="Expiration time")
    is_read: bool = Field(default=False, description="Whether notification has been read")
    is_grouped: bool = Field(default=False, description="Whether notification is grouped")
    group_key: str = Field(default="", description="Grouping key")


class NotificationTemplate(BaseModel):
    """A notification template for rendering."""

    id: str = Field(..., description="Unique template identifier")
    name: str = Field(..., description="Template name")
    title_template: str = Field(..., description="Title template string")
    message_template: str = Field(..., description="Message template string")
    default_priority: str = Field(default="normal", description="Default priority")
    default_channel: str = Field(default="general", description="Default channel")
    variables: List[str] = Field(default_factory=list, description="Expected variable names")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class NotificationChannel(BaseModel):
    """A notification channel configuration."""

    id: str = Field(..., description="Unique channel identifier")
    name: str = Field(..., description="Channel name")
    type: str = Field(..., description="Channel type: in-app/push/toast/log")
    enabled: bool = Field(default=True, description="Whether channel is enabled")
    config: Dict[str, Any] = Field(default_factory=dict, description="Channel-specific configuration")
