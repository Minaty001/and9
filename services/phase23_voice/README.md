# Phase 23 — Voice System

Speech-to-Text, Text-to-Speech, streaming. Interruption handling, mic state, language selection.

## Components

### VoiceConfig
Configuration for the voice system. Uses environment variable prefix `JARVIS_PHASE23_`.

| Field | Default | Description |
|---|---|---|
| service_name | `jarvis_voice` | Service name |
| stt_provider | `mock` | STT provider |
| tts_provider | `mock` | TTS provider |
| default_language | `en-IN` | Default language |
| enable_streaming | `True` | Enable audio streaming |
| enable_interruption | `True` | Enable interruption |
| mic_sample_rate | `16000` | Mic sample rate |
| vad_threshold | `0.5` | VAD threshold |
| max_speech_duration_seconds | `30` | Max speech duration |

### VoiceState
Pydantic model: `status` (idle/listening/processing/speaking), `mic_active`, `language`, `current_transcript`, `noise_level`, `timestamp`.

### STTResult
Pydantic model: `transcript`, `confidence`, `language`, `duration_seconds`, `is_final`, `words`.

### TTSResult
Pydantic model: `audio_data` (base64), `format`, `duration_seconds`, `text_synthesized`.

### SpeechRecognizer
Mock recognizer with:
- `recognize(audio_data, language)` → STTResult using predefined transcripts
- `start_streaming()` / `stop_streaming()` — Streaming control
- `add_mock_transcript()` — Custom transcript for testing

### SpeechSynthesizer
Mock synthesizer with:
- `synthesize(text, language, voice)` → TTSResult with configurable voice
- Generates deterministic base64 mock audio

### VoiceControllerService
ServiceBase wrapper providing `recognize()`, `synthesize()`, `start_listening()`, `stop_listening()`, `get_state()`, `set_language()`.
