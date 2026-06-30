"""
Phase 25 — Personality Engine.

Separate personality from reasoning. Tone, style, greetings,
response constraints. Configurable personas.

Components:
    - PersonalityConfig: Configuration for personality engine
    - Persona: Persona data model
    - PersonalityProfile: Profile data model
    - PersonalityEngine: Core engine with built-in personas
    - PersonalityEngineService: ServiceBase wrapper
"""

from .config import PersonalityConfig
from .models import Persona, PersonalityProfile
from .engine import PersonalityEngine
from .service import PersonalityEngineService

__all__ = [
    "PersonalityConfig",
    "Persona",
    "PersonalityProfile",
    "PersonalityEngine",
    "PersonalityEngineService",
]
