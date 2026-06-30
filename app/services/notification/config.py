"""
Notification Manager Configuration.
"""

from pydantic import BaseModel, Field


class NotificationConfig(BaseModel):
    """Configuration for the notification manager."""

    service_name: str = Field(default="jarvis_notification", description="Notification service name")
    default_priority: str = Field(default="normal", description="Default notification priority")
    max_notifications_per_minute: int = Field(default=30, ge=1, le=1000, description="Max notifications per minute")
    enable_sound: bool = Field(default=True, description="Enable sound on notifications")
    enable_vibration: bool = Field(default=True, description="Enable vibration")
    enable_grouping: bool = Field(default=True, description="Enable notification grouping")
    enable_templates: bool = Field(default=True, description="Enable notification templates")
    retention_hours: int = Field(default=72, ge=1, le=720, description="Hours to retain notifications")
    default_channel: str = Field(default="general", description="Default notification channel")

    model_config = {"env_prefix": "JARVIS_PHASE30_"}
