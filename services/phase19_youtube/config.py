"""
Phase 19 — YouTube Controller Configuration.
"""

from typing import List
from pydantic import Field
from services.base.config_base import BaseConfig


class YouTubeConfig(BaseConfig):
    """Configuration for YouTube controller."""

    service_name: str = Field(default="jarvis_youtube", description="YouTube controller service name")
    api_key_env: str = Field(default="JARVIS_YOUTUBE_API_KEY", description="Environment variable for YouTube API key")
    max_search_results: int = Field(default=10, ge=1, le=50, description="Maximum number of search results")
    enable_history: bool = Field(default=True, description="Enable playback history tracking")
    max_history: int = Field(default=100, ge=1, le=1000, description="Maximum history entries")
    enable_autoplay: bool = Field(default=False, description="Enable autoplay of next video")
    default_quality: str = Field(default="auto", description="Default video quality")
    supported_qualities: List[str] = Field(
        default=["auto", "144p", "360p", "480p", "720p", "1080p"],
        description="Supported video quality levels",
    )

    model_config = {"env_prefix": "JARVIS_PHASE19_"}
