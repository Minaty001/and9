"""
Phase 23 — Voice Controller Service.

ServiceBase wrapper for the voice system.
"""

from __future__ import annotations

import time
import logging
from typing import Any, Dict, Optional

from services.base.service_base import ServiceBase
from .config import VoiceConfig
from .models import VoiceState, STTResult, TTSResult
from .speech import SpeechRecognizer, SpeechSynthesizer

logger = logging.getLogger(__name__)


class VoiceControllerService(ServiceBase):
    """Voice controller service managing speech recognition and synthesis.

    Usage:
        svc = VoiceControllerService()
        await svc.initialize()
        result = await svc.recognize("hello")
    """

    def __init__(self, config: Optional[VoiceConfig] = None):
        super().__init__(name="jarvis_voice", version="1.0.0")
        self.config = config or VoiceConfig()
        self.recognizer: Optional[SpeechRecognizer] = None
        self.synthesizer: Optional[SpeechSynthesizer] = None
        self._state: Optional[VoiceState] = None
        self._start_time = 0.0

    async def initialize(self) -> bool:
        """Initialize the voice controller service."""
        self._start_time = time.time()
        try:
            self.recognizer = SpeechRecognizer(language=self.config.default_language)
            self.synthesizer = SpeechSynthesizer(language=self.config.default_language)
            self._state = VoiceState(
                status="idle",
                mic_active=False,
                language=self.config.default_language,
            )
            self._metrics.reset()
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

        self._metrics.counter("recognitions", 1)
        t0 = time.perf_counter()

        self._state.status = "processing"
        result = self.recognizer.recognize(audio_data, language)

        if result.is_final:
            self._state.current_transcript = result.transcript

        elapsed = (time.perf_counter() - t0) * 1000
        self._metrics.histogram("recognition_time_ms", elapsed)
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

        self._metrics.counter("syntheses", 1)
        t0 = time.perf_counter()

        self._state.status = "speaking"
        result = self.synthesizer.synthesize(text, language, voice)

        elapsed = (time.perf_counter() - t0) * 1000
        self._metrics.histogram("synthesis_time_ms", elapsed)
        self._state.status = "idle"

        return result

    async def start_listening(self) -> bool:
        """Start listening (activate mic and streaming).

        Returns:
            True if listening started successfully.
        """
        if not self._initialized or not self.recognizer:
            raise RuntimeError("VoiceControllerService not initialized")

        if self.config.enable_streaming:
            self.recognizer.start_streaming()

        self._state.status = "listening"
        self._state.mic_active = True
        self._metrics.counter("listening_sessions", 1)
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
        self._state.language = language
        self.config.default_language = language
        logger.info("Voice language set to: %s", language)

    async def health(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "service_name": self.name,
            "version": self.version,
            "initialized": self._initialized,
            "uptime_seconds": round(uptime, 1),
        }

    async def stats(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        return {
            "service": self.name,
            "version": self.version,
            "uptime_seconds": round(uptime, 1),
            "voice_state": self._state.status if self._state else "unknown",
            "language": self._state.language if self._state else "unknown",
            "metrics": self._metrics.snapshot(),
        }
