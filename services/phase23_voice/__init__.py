"""
Phase 23 — Voice System.

Speech-to-Text, Text-to-Speech, streaming. Interruption handling,
mic state, language selection.

Components:
    - VoiceConfig: Configuration for voice system
    - VoiceState: Voice system state model
    - STTResult: Speech-to-text result model
    - TTSResult: Text-to-speech result model
    - SpeechRecognizer: Mock speech recognition
    - SpeechSynthesizer: Mock speech synthesis
    - VoiceControllerService: ServiceBase wrapper
"""

from .config import VoiceConfig
from .models import VoiceState, STTResult, TTSResult
from .speech import SpeechRecognizer, SpeechSynthesizer
from .service import VoiceControllerService

__all__ = [
    "VoiceConfig",
    "VoiceState",
    "STTResult",
    "TTSResult",
    "SpeechRecognizer",
    "SpeechSynthesizer",
    "VoiceControllerService",
]
