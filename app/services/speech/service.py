"""
app/services/speech/service.py — Voice Controller Service.

Service wrapper for voice (speech recognition and synthesis) with
initialize/shutdown/health/stats lifecycle.
"""

from __future__ import annotations

import time
import logging
from typing import Any, Dict, Optional

from .models import VoiceState, STTResult, TTSResult
from .speech import SpeechRecognizer, SpeechSynthesizer

logger = logging.getLogger(__name__)


class VoiceControllerService:
    """Voice controller service managing speech recognition and synthesis.

    Wraps SpeechRecognizer (STT) and SpeechSynthesizer (TTS) with a
    unified service lifecycle.

    Usage:
        svc = VoiceControllerService()
        await svc.initialize()
        result = await svc.recognize("hello")
    """

    def __init__(self, default_language: str = "en-IN", enable_streaming: bool = True):
        self._default_language = default_language
        self._enable_streaming = enable_streaming
        self.recognizer: Optional[SpeechRecognizer] = None
        self.synthesizer: Optional[SpeechSynthesizer] = None
        self._state: Optional[VoiceState] = None
        self._initialized = False
        self._start_time = 0.0
        self._stats = {
            "recognitions": 0,
            "syntheses": 0,
            "listening_sessions": 0,
            "recognition_time_ms": [],
            "synthesis_time_ms": [],
        }

    async def initialize(self) -> bool:
        """Initialize the voice controller service."""
        self._start_time = time.time()
        try:
            self.recognizer = SpeechRecognizer(language=self._default_language)
            self.synthesizer = SpeechSynthesizer(language=self._default_language)
            self._state = VoiceState(
                status="idle",
                mic_active=False,
                language=self._default_language,
            )
            self._initialized = True
            logger.info("VoiceControllerService initialized")
            return True
        except Exception as e:
            logger.error("VoiceControllerService init failed: %s", e)
            return False

    async def shutdown(self) -> None:
        """Shut down the voice controller service."""
        logger.info("VoiceControllerService shutting down...")

        if self.recognizer and self.recognizer.is_streaming:
            self.recognizer.stop_streaming()

        if self._state:
            self._state.status = "idle"
            self._state.mic_active = False

        self._initialized = False

    async def recognize(self, audio_data: str, language: Optional[str] = None) -> STTResult:
        """Recognize speech from audio data.

        Args:
            audio_data: Base64-encoded audio data or keyword for mock.
            language: Expected language (optional).

        Returns:
            STTResult with recognized transcript.
        """
        if not self._initialized or not self.recognizer:
            raise RuntimeError("VoiceControllerService not initialized")

        self._stats["recognitions"] += 1
        t0 = time.perf_counter()

        if self._state:
            self._state.status = "processing"
        result = self.recognizer.recognize(audio_data, language)

        if result.is_final and self._state:
            self._state.current_transcript = result.transcript

        elapsed = (time.perf_counter() - t0) * 1000
        self._stats["recognition_time_ms"].append(elapsed)
        if self._state:
            self._state.status = "idle"

        return result

    async def synthesize(self, text: str, language: Optional[str] = None, voice: Optional[str] = None) -> TTSResult:
        """Synthesize speech from text.

        Args:
            text: Text to synthesize.
            language: Language code (optional).
            voice: Voice to use (optional).

        Returns:
            TTSResult with synthesized audio.
        """
        if not self._initialized or not self.synthesizer:
            raise RuntimeError("VoiceControllerService not initialized")

        self._stats["syntheses"] += 1
        t0 = time.perf_counter()

        if self._state:
            self._state.status = "speaking"
        result = self.synthesizer.synthesize(text, language, voice)

        elapsed = (time.perf_counter() - t0) * 1000
        self._stats["synthesis_time_ms"].append(elapsed)
        if self._state:
            self._state.status = "idle"

        return result

    async def start_listening(self) -> bool:
        """Start listening (activate mic and streaming).

        Returns:
            True if listening started successfully.
        """
        if not self._initialized or not self.recognizer:
            raise RuntimeError("VoiceControllerService not initialized")

        if self._enable_streaming:
            self.recognizer.start_streaming()

        if self._state:
            self._state.status = "listening"
            self._state.mic_active = True
        self._stats["listening_sessions"] += 1
        return True

    async def stop_listening(self) -> bool:
        """Stop listening (deactivate mic and streaming).

        Returns:
            True if listening stopped successfully.
        """
        if not self._initialized or not self.recognizer:
            raise RuntimeError("VoiceControllerService not initialized")

        if self.recognizer.is_streaming:
            self.recognizer.stop_streaming()

        if self._state:
            self._state.status = "idle"
            self._state.mic_active = False
        return True

    async def get_state(self) -> VoiceState:
        """Get current voice system state."""
        return self._state

    async def set_language(self, language: str) -> None:
        """Set the voice system language.

        Args:
            language: Language code (e.g., "en-IN", "hi-IN").
        """
        if not self._initialized:
            raise RuntimeError("VoiceControllerService not initialized")
        if self._state:
            self._state.language = language
        self._default_language = language
        logger.info("Voice language set to: %s", language)

    async def health(self) -> Dict[str, Any]:
        """Return current health status."""
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "service_name": "jarvis_voice",
            "initialized": self._initialized,
            "uptime_seconds": round(uptime, 1),
        }

    async def stats(self) -> Dict[str, Any]:
        """Return service statistics."""
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        avg_rec = (
            sum(self._stats["recognition_time_ms"]) / len(self._stats["recognition_time_ms"])
            if self._stats["recognition_time_ms"]
            else 0
        )
        avg_syn = (
            sum(self._stats["synthesis_time_ms"]) / len(self._stats["synthesis_time_ms"])
            if self._stats["synthesis_time_ms"]
            else 0
        )
        return {
            "service": "jarvis_voice",
            "uptime_seconds": round(uptime, 1),
            "voice_state": self._state.status if self._state else "unknown",
            "language": self._state.language if self._state else "unknown",
            "recognitions": self._stats["recognitions"],
            "syntheses": self._stats["syntheses"],
            "avg_recognition_time_ms": round(avg_rec, 2),
            "avg_synthesis_time_ms": round(avg_syn, 2),
        }
