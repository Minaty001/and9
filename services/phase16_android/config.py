"""
Phase 16 — Android Controller Configuration.

Uses Pydantic v2 model_config style (not old class Config).
"""

from pydantic import Field
from typing import List
from services.base.config_base import BaseConfig


class AndroidConfig(BaseConfig):
    """Configuration for the Android Controller service."""

    service_name: str = Field(default="jarvis_android", description="Android Controller service name")
    enable_permission_check: bool = Field(default=True, description="Check permissions before actions")
    default_action_timeout_ms: int = Field(default=5000, description="Default timeout for actions in ms")
    supported_apps: List[str] = Field(
        default=[
            "chrome", "youtube", "gmail", "maps", "camera", "gallery",
            "settings", "calculator", "calendar", "clock", "contacts",
            "dialer", "messages", "photos", "playstore", "spotify",
            "whatsapp", "telegram", "twitter", "instagram", "facebook",
            "linkedin", "netflix", "drive", "docs", "sheets", "slides",
            "meet", "clock", "alarms", "file_manager",
        ],
        description="List of supported app names",
    )
    enable_hardware_control: bool = Field(default=True, description="Enable hardware control (volume/brightness)")
    enable_notification_access: bool = Field(default=True, description="Enable notification access")

    model_config = {"env_prefix": "JARVIS_PHASE16_"}
