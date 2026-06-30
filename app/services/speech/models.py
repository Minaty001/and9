"""
app/services/speech/models.py — Voice System Models.

Data models for speech recognition, synthesis, and voice state.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class VoiceState(BaseModel):
    """Current state of the voice system."""

    status: str = Field(default="idle", description="System status: idle/listening/processing/speaking")
    mic_active: bool = Field(default=False, description="Whether microphone is active")
    language: str = Field(default="en-IN", description="Current language setting")
    current_transcript: str = Field(default="", description="Current transcript text")
    noise_level: float = Field(default=0.0, ge=0.0, le=1.0, description="Current noise level")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class STTResult(BaseModel):
    """Speech-to-text recognition result."""

    transcript: str = Field(..., description="Recognized text")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Recognition confidence")
    language: str = Field(default="en-IN", description="Detected language")
    duration_seconds: float = Field(default=0.0, ge=0.0, description="Audio duration")
    is_final: bool = Field(default=True, description="Whether this is a final result")
    words: List[Dict[str, Any]] = Field(default_factory=list, description="Word-level timings")


class TTSResult(BaseModel):
    """Text-to-speech synthesis result."""

    audio_data: str = Field(..., description="Base64-encoded audio data")
    format: str = Field(default="wav", description="Audio format")
    duration_seconds: float = Field(default=0.0, ge=0.0, description="Audio duration in seconds")
    text_synthesized: str = Field(..., description="The text that was synthesized")
