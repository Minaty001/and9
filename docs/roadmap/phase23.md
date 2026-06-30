# Phase 23: Voice System

## Purpose
Speech-to-text (STT) and text-to-speech (TTS) service with streaming, interruption handling, mic state management, and language selection. `VoiceControllerService` wraps `SpeechRecognizer` (mock STT) and `SpeechSynthesizer` (mock TTS) with a unified lifecycle including initialize/shutdown/health/stats. Supports configurable language (default `en-IN`) and streaming mode.

## Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `JARVIS_PHASE23_DEFAULT_LANGUAGE` | en-IN | Default voice language |
| `JARVIS_PHASE23_ENABLE_STREAMING` | true | Enable streaming recognition |

## Architecture
```
VoiceControllerService
  ├── initialize() — create SpeechRecognizer + SpeechSynthesizer
  ├── recognize(audio_data) → STTResult — speech-to-text
  ├── synthesize(text) → TTSResult — text-to-speech
  ├── start_listening() / stop_listening() — mic control
  ├── set_language(lang) — switch language
  ├── health() / stats() — introspection
  │
  ├── SpeechRecognizer — mock STT with predefined transcripts
  │     ├── recognize(audio) → STTResult
  │     ├── start_streaming() / stop_streaming()
  │     └── add_mock_transcript(key, text, confidence)
  │
  ├── SpeechSynthesizer — mock TTS with configurable voice
  │     └── synthesize(text, language, voice) → TTSResult
  │
  └── Models: VoiceState, STTResult, TTSResult
```

## Code
```python
class VoiceControllerService:
    async def initialize(self):
        self.recognizer = SpeechRecognizer(language=self._default_language)
        self.synthesizer = SpeechSynthesizer(language=self._default_language)
        self._state = VoiceState(status="idle", mic_active=False)
        self._initialized = True

    async def recognize(self, audio_data: str) -> STTResult:
        result = self.recognizer.recognize(audio_data)
        return result

    async def synthesize(self, text: str) -> TTSResult:
        result = self.synthesizer.synthesize(text)
        return result

class SpeechRecognizer:
    def recognize(self, audio_data, language=None) -> STTResult:
        key = audio_data.lower().strip()
        mock = self._mock_transcripts.get(key, self._default_transcript)
        return STTResult(transcript=mock["transcript"], confidence=mock["confidence"], is_final=True)

class SpeechSynthesizer:
    def synthesize(self, text, language=None, voice=None) -> TTSResult:
        mock_audio = base64.b64encode(f"mock_audio:{voice}:{lang}:{text}".encode()).decode()
        return TTSResult(audio_data=mock_audio, format="wav", duration_seconds=duration, text_synthesized=text)
```

## Location
`app/services/speech/` — voice controller, recognizer, synthesizer, and models
