"""
Phase 23 — Voice System Configuration.
"""

from pydantic import Field
from services.base.config_base import BaseConfig


class VoiceConfig(BaseConfig):
    """Configuration for the Voice System."""

    service_name: str = Field(default="jarvis_voice", description="Voice service name")
    stt_provider: str = Field(default="mock", description="STT provider name")
    tts_provider: str = Field(default="mock", description="TTS provider name")
    default_language: str = Field(default="en-IN", description="Default speech language")
    enable_streaming: bool = Field(default=True, description="Enable audio streaming")
    enable_interruption: bool = Field(default=True, description="Enable interruption handling")
    mic_sample_rate: int = Field(default=16000, ge=8000, le=48000, description="Microphone sample rate")
    vad_threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="VAD threshold")
    max_speech_duration_seconds: int = Field(default=30, ge=1, le=300, description="Max speech duration")

    model_config = {"env_prefix": "JARVIS_PHASE23_"}
