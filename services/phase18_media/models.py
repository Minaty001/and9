"""
Phase 18 — Media Controller Models.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Track(BaseModel):
    """A media track with metadata."""

    id: str = Field(..., description="Unique track identifier")
    title: str = Field(..., description="Track title")
    artist: str = Field(default="Unknown Artist", description="Artist name")
    album: Optional[str] = Field(default=None, description="Album name")
    duration_seconds: float = Field(default=0.0, ge=0.0, description="Track duration in seconds")
    url: Optional[str] = Field(default=None, description="Track URL")
    service: str = Field(default="local", description="Source service (local, spotify, youtube_music)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional track metadata")


class PlaybackState(BaseModel):
    """Current playback state of the media controller."""

    status: str = Field(default="stopped", description="Playback status: stopped, playing, paused")
    current_track: Optional[Track] = Field(default=None, description="Currently playing track")
    position_seconds: float = Field(default=0.0, ge=0.0, description="Current playback position in seconds")
    volume: int = Field(default=50, ge=0, le=100, description="Current volume level (0-100)")
    queue: List[Track] = Field(default_factory=list, description="Current playback queue")
    shuffle: bool = Field(default=False, description="Whether shuffle is enabled")
    repeat_mode: str = Field(default="off", description="Repeat mode: off, one, all")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="State timestamp")
