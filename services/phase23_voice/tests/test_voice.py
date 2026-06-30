"""
Tests for Phase 23 — Voice System.
"""

import time
import pytest
from services.phase23_voice import (
    VoiceConfig,
    VoiceState,
    STTResult,
    TTSResult,
    SpeechRecognizer,
    SpeechSynthesizer,
    VoiceControllerService,
)


class TestVoiceConfig:
    """Verify VoiceConfig creation."""

    def test_default_config(self):
        config = VoiceConfig()
        assert config.service_name == "jarvis_voice"
        assert config.default_language == "en-IN"
        assert config.mic_sample_rate == 16000

    def test_custom_config(self):
        config = VoiceConfig(
            default_language="hi-IN",
            enable_streaming=False,
            mic_sample_rate=44100,
        )
        assert config.default_language == "hi-IN"
        assert config.enable_streaming is False
        assert config.mic_sample_rate == 44100

    def test_env_prefix(self):
        assert VoiceConfig.model_config["env_prefix"] == "JARVIS_PHASE23_"


class TestVoiceState:
    """Verify VoiceState creation."""

    def test_default_state(self):
        state = VoiceState()
        assert state.status == "idle"
        assert state.mic_active is False
        assert state.language == "en-IN"

    def test_custom_state(self):
        state = VoiceState(status="listening", mic_active=True, language="hi-IN")
        assert state.status == "listening"
        assert state.mic_active is True


class TestSTTResult:
    """Verify STTResult creation."""

    def test_create_result(self):
        result = STTResult(transcript="Hello world", confidence=0.95)
        assert result.transcript == "Hello world"
        assert result.confidence == 0.95
        assert result.is_final is True

    def test_result_defaults(self):
        result = STTResult(transcript="test")
        assert result.language == "en-IN"
        assert result.duration_seconds == 0.0


class TestTTSResult:
    """Verify TTSResult creation."""

    def test_create_result(self):
        result = TTSResult(audio_data="AAAA", text_synthesized="Hello")
        assert result.audio_data == "AAAA"
        assert result.text_synthesized == "Hello"
        assert result.format == "wav"

    def test_result_defaults(self):
        result = TTSResult(audio_data="data", text_synthesized="test")
        assert result.format == "wav"
        assert result.duration_seconds == 0.0


class TestSpeechRecognizer:
    """Verify SpeechRecognizer behavior."""

    def test_recognize_known(self):
        recognizer = SpeechRecognizer()
        result = recognizer.recognize("hello")
        assert "help" in result.transcript.lower()
        assert result.confidence > 0.9
        assert result.is_final is True

    def test_recognize_unknown(self):
        recognizer = SpeechRecognizer()
        result = recognizer.recognize("some_random_gibberish_12345")
        assert result.confidence < 0.5

    def test_recognize_with_language(self):
        recognizer = SpeechRecognizer()
        result = recognizer.recognize("hello", language="hi-IN")
        assert result.language == "hi-IN"

    def test_start_stop_streaming(self):
        recognizer = SpeechRecognizer()
        assert recognizer.start_streaming() is True
        assert recognizer.is_streaming is True
        assert recognizer.start_streaming() is False  # Already streaming
        assert recognizer.stop_streaming() is True
        assert recognizer.is_streaming is False
        assert recognizer.stop_streaming() is False  # Already stopped

    def test_add_mock_transcript(self):
        recognizer = SpeechRecognizer()
        recognizer.add_mock_transcript("custom", "Custom transcript", 0.85)
        result = recognizer.recognize("custom")
        assert result.transcript == "Custom transcript"
        assert result.confidence == 0.85

    def test_words_in_result(self):
        recognizer = SpeechRecognizer()
        result = recognizer.recognize("hello")
        assert len(result.words) > 0
        assert "word" in result.words[0]
        assert "start" in result.words[0]


class TestSpeechSynthesizer:
    """Verify SpeechSynthesizer behavior."""

    def test_synthesize_default(self):
        synthesizer = SpeechSynthesizer()
        result = synthesizer.synthesize("Hello world")
        assert result.text_synthesized == "Hello world"
        assert result.format == "wav"
        assert len(result.audio_data) > 0

    def test_synthesize_with_voice(self):
        synthesizer = SpeechSynthesizer(voice="male-1")
        result = synthesizer.synthesize("Test", voice="female-1")
        assert result.text_synthesized == "Test"

    def test_synthesize_with_language(self):
        synthesizer = SpeechSynthesizer(language="en-IN")
        result = synthesizer.synthesize("Hello", language="hi-IN")
        assert result.text_synthesized == "Hello"

    def test_duration_calculation(self):
        synthesizer = SpeechSynthesizer()
        result = synthesizer.synthesize("A" * 100)
        assert result.duration_seconds > 0.5


class TestVoiceControllerService:
    """Verify service wrapper."""

    @pytest.mark.asyncio
    async def test_initialize(self):
        svc = VoiceControllerService()
        assert await svc.initialize() is True

    @pytest.mark.asyncio
    async def test_shutdown(self):
        svc = VoiceControllerService()
        await svc.initialize()
        await svc.shutdown()
        assert not svc.is_initialized()

    @pytest.mark.asyncio
    async def test_health(self):
        svc = VoiceControllerService()
        await svc.initialize()
        health = await svc.health()
        assert health["status"] == "healthy"
        assert health["service_name"] == "jarvis_voice"

    @pytest.mark.asyncio
    async def test_stats(self):
        svc = VoiceControllerService()
        await svc.initialize()
        stats = await svc.stats()
        assert stats["service"] == "jarvis_voice"
        assert "metrics" in stats

    @pytest.mark.asyncio
    async def test_recognize(self):
        svc = VoiceControllerService()
        await svc.initialize()
        result = await svc.recognize("hello")
        assert "help" in result.transcript.lower()
        assert result.is_final is True

    @pytest.mark.asyncio
    async def test_synthesize(self):
        svc = VoiceControllerService()
        await svc.initialize()
        result = await svc.synthesize("Hello world")
        assert result.text_synthesized == "Hello world"
        assert len(result.audio_data) > 0

    @pytest.mark.asyncio
    async def test_start_stop_listening(self):
        svc = VoiceControllerService()
        await svc.initialize()
        assert await svc.start_listening() is True
        state = await svc.get_state()
        assert state.status == "listening"
        assert state.mic_active is True

        assert await svc.stop_listening() is True
        state = await svc.get_state()
        assert state.status == "idle"
        assert state.mic_active is False

    def test_get_state(self):
        svc = VoiceControllerService()
        # Before init, state is None
        # After init it should have defaults
        import asyncio
        asyncio.run(svc.initialize())
        state = asyncio.run(svc.get_state())
        assert state.status == "idle"
        assert state.language == "en-IN"

    @pytest.mark.asyncio
    async def test_set_language(self):
        svc = VoiceControllerService()
        await svc.initialize()
        await svc.set_language("hi-IN")
        assert (await svc.get_state()).language == "hi-IN"
        assert svc.config.default_language == "hi-IN"

    @pytest.mark.asyncio
    async def test_recognize_not_initialized(self):
        svc = VoiceControllerService()
        with pytest.raises(RuntimeError, match="not initialized"):
            await svc.recognize("hello")

    @pytest.mark.asyncio
    async def test_synthesize_not_initialized(self):
        svc = VoiceControllerService()
        with pytest.raises(RuntimeError, match="not initialized"):
            await svc.synthesize("hello")

    @pytest.mark.asyncio
    async def test_recognize_updates_state(self):
        svc = VoiceControllerService()
        await svc.initialize()
        result = await svc.recognize("weather")
        assert "weather" in result.transcript.lower()
        state = await svc.get_state()
        assert "weather" in state.current_transcript.lower()

    @pytest.mark.asyncio
    async def test_synthesize_duration(self):
        svc = VoiceControllerService()
        await svc.initialize()
        result = await svc.synthesize("Hello, how are you today?")
        assert result.duration_seconds > 0
