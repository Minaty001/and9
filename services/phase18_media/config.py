"""
Phase 18 — Media Controller Configuration.
"""

from typing import List
from pydantic import Field
from services.base.config_base import BaseConfig


class MediaConfig(BaseConfig):
    """Configuration for the media controller service."""

    service_name: str = Field(default="jarvis_media", description="Media controller service name")
    supported_services: List[str] = Field(
        default=["local", "spotify", "youtube_music"],
        description="List of supported media services",
    )
    default_volume: int = Field(default=50, ge=0, le=100, description="Default volume level")
    max_queue_size: int = Field(default=100, description="Maximum queue size")
    enable_crossfade: bool = Field(default=False, description="Enable crossfade between tracks")
    enable_eq: bool = Field(default=False, description="Enable equalizer")
    history_size: int = Field(default=50, description="Max playback history entries")

    model_config = {"env_prefix": "JARVIS_PHASE18_"}
