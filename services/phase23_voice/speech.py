"""
Phase 23 — Speech Recognizer and Synthesizer.

Mock implementations for speech-to-text and text-to-speech.
"""

import time
import base64
import logging
from typing import Any, Dict, List, Optional

from .models import STTResult, TTSResult

logger = logging.getLogger(__name__)


class SpeechRecognizer:
    """Mock speech recognizer with predefined transcripts."""

    def __init__(self, language: str = "en-IN"):
        self.language = language
        self._is_streaming = False
        self._mock_transcripts = {
            "hello": {"transcript": "Hello, how can I help you?", "confidence": 0.95},
            "weather": {"transcript": "What is the weather like today?", "confidence": 0.92},
            "time": {"transcript": "What time is it?", "confidence": 0.98},
            "news": {"transcript": "Give me the latest news", "confidence": 0.90},
            "stop": {"transcript": "Stop listening", "confidence": 0.97},
        }
        self._default_transcript = {"transcript": "I didn't catch that", "confidence": 0.30}

    def recognize(self, audio_data: str, language: Optional[str] = None) -> STTResult:
        """Recognize speech from audio data.

        Args:
            audio_data: Base64-encoded audio data or text keyword for mock.
            language: Expected language (optional).

        Returns:
            STTResult with recognized transcript.
        """
        lang = language or self.language

        # For mock, we use the audio_data as a lookup key
        key = audio_data.lower().strip()

        # Empty audio indicates incomplete/streaming input
        if not key:
            return STTResult(
                transcript=self._default_transcript["transcript"],
                confidence=self._default_transcript["confidence"],
                language=lang,
                duration_seconds=0.0,
                is_final=False,
                words=[],
            )

        mock = self._mock_transcripts.get(key, self._default_transcript)

        # Simulate processing time
        time.sleep(0.05)

        return STTResult(
            transcript=mock["transcript"],
            confidence=mock["confidence"],
            language=lang,
            duration_seconds=2.0,
            is_final=True,
            words=[
                {"word": w, "start": i * 0.3, "end": (i + 1) * 0.3, "confidence": mock["confidence"]}
                for i, w in enumerate(mock["transcript"].split())
            ],
        )

    def start_streaming(self) -> bool:
        """Start streaming recognition.

        Returns:
            True if streaming started successfully.
        """
        if self._is_streaming:
            return False
        self._is_streaming = True
        logger.info("Speech recognizer streaming started")
        return True

    def stop_streaming(self) -> bool:
        """Stop streaming recognition.

        Returns:
            True if streaming stopped successfully.
        """
        if not self._is_streaming:
            return False
        self._is_streaming = False
        logger.info("Speech recognizer streaming stopped")
        return True

    @property
    def is_streaming(self) -> bool:
        """Whether the recognizer is currently streaming."""
        return self._is_streaming

    def add_mock_transcript(self, key: str, transcript: str, confidence: float = 0.9) -> None:
        """Add a custom mock transcript for testing.

        Args:
            key: Lookup key (audio data keyword).
            transcript: Transcript text.
            confidence: Confidence score.
        """
        self._mock_transcripts[key] = {"transcript": transcript, "confidence": confidence}


class SpeechSynthesizer:
    """Mock speech synthesizer with configurable voice."""

    def __init__(self, voice: str = "default", language: str = "en-IN"):
        self.voice = voice
        self.language = language

    def synthesize(self, text: str, language: Optional[str] = None, voice: Optional[str] = None) -> TTSResult:
        """Synthesize speech from text.

        Args:
            text: Text to synthesize.
            language: Language code (optional).
            voice: Voice to use (optional).

        Returns:
            TTSResult with base64-encoded audio.
        """
        lang = language or self.language
        vc = voice or self.voice

        # Simulate processing time proportional to text length
        duration = max(0.5, len(text) * 0.05)
        time.sleep(0.02)

        # Generate mock base64 audio data
        mock_audio = base64.b64encode(f"mock_audio:{vc}:{lang}:{text}".encode()).decode()

        return TTSResult(
            audio_data=mock_audio,
            format="wav",
            duration_seconds=duration,
            text_synthesized=text,
        )
