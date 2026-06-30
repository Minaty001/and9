"""
app/services/speech/ — Voice System.

Speech-to-Text and Text-to-Speech with streaming, interruption handling,
mic state, and language selection.

Components:
    - SpeechRecognizer: Mock speech recognition (STT)
    - SpeechSynthesizer: Mock speech synthesis (TTS)
    - VoiceControllerService: Service wrapper for voice functionality
    - VoiceState: Voice system state model
    - STTResult: Speech-to-text result model
    - TTSResult: Text-to-speech result model
"""

from .speech import SpeechRecognizer, SpeechSynthesizer
from .service import VoiceControllerService
from .models import VoiceState, STTResult, TTSResult

__all__ = [
    "SpeechRecognizer",
    "SpeechSynthesizer",
    "VoiceControllerService",
    "VoiceState",
    "STTResult",
    "TTSResult",
]
