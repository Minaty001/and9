"""
Phase 19 — YouTube Controller Models.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class YouTubeVideo(BaseModel):
    """Represents a YouTube video."""

    id: str = Field(..., description="Unique video identifier")
    title: str = Field(..., description="Video title")
    url: str = Field(..., description="Video URL")
    duration_seconds: int = Field(default=0, ge=0, description="Video duration in seconds")
    channel: str = Field(default="", description="Channel name")
    thumbnail_url: str = Field(default="", description="URL of video thumbnail")
    description: str = Field(default="", description="Video description")
    view_count: int = Field(default=0, ge=0, description="Number of views")
    published_at: str = Field(default="", description="Publication date string")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class YouTubePlaybackState(BaseModel):
    """Represents the current playback state."""

    status: str = Field(default="stopped", description="Playback status: stopped/playing/paused/buffering")
    current_video: Optional[YouTubeVideo] = Field(default=None, description="Currently playing video")
    position_seconds: float = Field(default=0.0, ge=0.0, description="Current position in seconds")
    quality: str = Field(default="auto", description="Current quality setting")
    volume: int = Field(default=50, ge=0, le=100, description="Volume level 0-100")
    playlist: List[YouTubeVideo] = Field(default_factory=list, description="Current playlist")
    autoplay: bool = Field(default=False, description="Whether autoplay is enabled")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
