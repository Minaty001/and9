"""
Phase 25 — Personality Engine.

Core engine for managing personas, applying tone, generating greetings,
and constraining responses.
"""

import logging
import random
from typing import Any, Dict, List, Optional

from .models import Persona, PersonalityProfile

logger = logging.getLogger(__name__)

# Built-in personas
BUILTIN_PERSONAS = {
    "jarvis_default": Persona(
        id="jarvis_default",
        name="JARVIS Default",
        tone="helpful",
        style_guide="Professional, clear, and concise assistant. Provide accurate information with a helpful demeanor.",
        greeting_rules={"greeting": "Hello! I'm JARVIS, your AI assistant. How can I help you today?", "time_based": True},
        response_constraints={"max_length": 500, "allow_markdown": True, "allow_code_blocks": True},
        vocabulary_whitelist=[],
        vocabulary_blacklist=[],
        emoji_usage="normal",
        formality_level=7,
        metadata={"category": "general", "version": "1.0"},
    ),
    "jarvis_casual": Persona(
        id="jarvis_casual",
        name="jarvis_casual",
        tone="friendly",
        style_guide="Friendly and conversational assistant. Use everyday language, be approachable, and make the user feel comfortable.",
        greeting_rules={"greeting": "Hey there! I'm JARVIS. What's up?", "time_based": False},
        response_constraints={"max_length": 500, "allow_markdown": True, "allow_code_blocks": True},
        vocabulary_whitelist=[],
        vocabulary_blacklist=[],
        emoji_usage="normal",
        formality_level=4,
        metadata={"category": "casual", "version": "1.0"},
    ),
    "jarvis_professional": Persona(
        id="jarvis_professional",
        name="JARVIS Professional",
        tone="formal",
        style_guide="Formal and precise assistant. Use proper language, avoid contractions, maintain a professional distance, and prioritize accuracy over friendliness.",
        greeting_rules={"greeting": "Good day. I am JARVIS, your professional AI assistant. How may I assist you?", "time_based": True},
        response_constraints={"max_length": 500, "allow_markdown": True, "allow_code_blocks": True},
        vocabulary_whitelist=[],
        vocabulary_blacklist=[],
        emoji_usage="never",
        formality_level=10,
        metadata={"category": "professional", "version": "1.0"},
    ),
}


class PersonalityEngine:
    """Core engine for personality management and response processing."""

    def __init__(self, active_persona_id: str = "jarvis_default"):
        self._personas: Dict[str, Persona] = {}
        self._profile: Optional[PersonalityProfile] = None
        self._active_persona_id = active_persona_id

        # Register built-in personas
        for pid, persona in BUILTIN_PERSONAS.items():
            self._personas[pid] = persona

        self._init_profile()

    def _init_profile(self) -> None:
        """Initialize the personality profile."""
        self._profile = PersonalityProfile(
            active_persona_id=self._active_persona_id,
            tone_scores={tone: 0.0 for tone in ["helpful", "friendly", "formal", "humorous", "empathetic"]},
        )

    def set_persona(self, persona_id: str) -> bool:
        """Set the active persona by ID.

        Args:
            persona_id: Persona identifier.

        Returns:
            True if persona was set successfully.
        """
        if persona_id not in self._personas:
            logger.warning("Persona not found: %s", persona_id)
            return False

        self._active_persona_id = persona_id
        if self._profile:
            self._profile.active_persona_id = persona_id
        logger.info("Active persona set to: %s", persona_id)
        return True

    def get_persona(self) -> Optional[Persona]:
        """Get the active persona.

        Returns:
            Active Persona or None.
        """
        return self._personas.get(self._active_persona_id)

    def register_persona(self, persona: Persona) -> bool:
        """Register a new persona.

        Args:
            persona: Persona to register.

        Returns:
            True if registered successfully.
        """
        if persona.id in self._personas:
            logger.warning("Persona already exists, overwriting: %s", persona.id)
        self._personas[persona.id] = persona
        logger.info("Registered persona: %s", persona.id)
        return True

    def list_personas(self) -> List[str]:
        """List all registered persona IDs.

        Returns:
            List of persona ID strings.
        """
        return list(self._personas.keys())

    def get_persona_by_id(self, persona_id: str) -> Optional[Persona]:
        """Get a persona by its ID.

        Args:
            persona_id: Persona identifier.

        Returns:
            Persona or None if not found.
        """
        return self._personas.get(persona_id)

    def apply_tone(self, text: str, persona: Optional[Persona] = None) -> str:
        """Apply tone adjustments to text based on persona.

        Args:
            text: Input text to adjust.
            persona: Persona to use (defaults to active persona).

        Returns:
            Tone-adjusted text.
        """
        p = persona or self.get_persona()
        if not p:
            return text

        adjusted = text

        # Apply formality adjustments
        if p.formality_level >= 7:
            # Basic capitalization for any formal/moderate text
            adjusted = adjusted[0].upper() + adjusted[1:] if adjusted else adjusted

        if p.formality_level >= 9:
            # Formal: ensure proper capitalization
            adjusted = adjusted[0].upper() + adjusted[1:] if adjusted else adjusted
            # Remove casual contractions
            contractions = {"i'm": "I am", "don't": "do not", "can't": "cannot", "won't": "will not",
                           "it's": "it is", "that's": "that is", "there's": "there is"}
            for casual, formal in contractions.items():
                adjusted = adjusted.replace(casual, formal)
                adjusted = adjusted.replace(casual.capitalize(), formal.capitalize())

        elif p.formality_level <= 4:
            # Casual: add friendly touches
            if not adjusted.startswith(("Hey", "Hey!", "Hi", "Hi!")):
                pass  # Keep as is for now

        # Update tone score
        if self._profile and p.tone in self._profile.tone_scores:
            self._profile.tone_scores[p.tone] += 1.0

        return adjusted

    def generate_greeting(self, context: Optional[Dict[str, Any]] = None) -> str:
        """Generate a greeting based on the active persona and context.

        Args:
            context: Optional context dict (e.g., {"time_of_day": "morning"}).

        Returns:
            Greeting string.
        """
        persona = self.get_persona()
        if not persona:
            return "Hello!"

        rules = persona.greeting_rules
        greeting = rules.get("greeting", "Hello!")

        # Time-based greeting adjustment
        if rules.get("time_based", False) and context:
            tod = context.get("time_of_day", "")
            if tod == "morning":
                greeting = greeting.replace("Hello", "Good morning").replace("Hey", "Good morning")
            elif tod == "afternoon":
                greeting = greeting.replace("Hello", "Good afternoon").replace("Hey", "Good afternoon")
            elif tod == "evening":
                greeting = greeting.replace("Hello", "Good evening").replace("Hey", "Good evening")

        # Track greeting in history
        if self._profile:
            self._profile.greeting_history.append(greeting)

        return greeting

    def constrain_response(self, text: str, persona: Optional[Persona] = None) -> str:
        """Apply response constraints based on persona.

        Args:
            text: Response text to constrain.
            persona: Persona to use (defaults to active persona).

        Returns:
            Constrained response text.
        """
        p = persona or self.get_persona()
        if not p:
            return text

        constrained = text

        # Apply max length constraint
        max_len = p.response_constraints.get("max_length", 500)
        if len(constrained) > max_len:
            constrained = constrained[:max_len].rsplit(" ", 1)[0] + "..."

        # Apply vocabulary blacklist
        for word in p.vocabulary_blacklist:
            constrained = constrained.replace(word, "[redacted]")

        # Apply emoji constraint
        if p.emoji_usage == "never":
            # Simple emoji removal (basic range)
            import re
            constrained = re.sub(r'[\U0001F300-\U0001F9FF]', '', constrained)
        elif p.emoji_usage == "rarely":
            # Reduce emoji count
            pass

        # Update response count
        if self._profile:
            self._profile.response_count += 1

        return constrained.strip()

    def detect_tone(self, text: str) -> str:
        """Detect the tone of a text.

        Args:
            text: Text to analyze.

        Returns:
            Detected tone string.
        """
        text_lower = text.lower()

        # Simple keyword-based tone detection
        formal_indicators = ["regarding", "therefore", "however", "nevertheless", "accordingly",
                            "please find", "per your", "kindly", "respectfully"]
        casual_indicators = ["hey", "yeah", "nah", "cool", "awesome", "dude", "gonna", "wanna"]
        empathetic_indicators = ["sorry", "apologize", "understand", "feel", "concern"]
        humorous_indicators = ["lol", "haha", "joke", "funny", "😂", "😄"]
        helpful_indicators = ["let me", "i can", "here's", "try", "suggestion", "recommend"]

        scores = {
            "formal": sum(1 for w in formal_indicators if w in text_lower),
            "casual": sum(1 for w in casual_indicators if w in text_lower),
            "empathetic": sum(1 for w in empathetic_indicators if w in text_lower),
            "humorous": sum(1 for w in humorous_indicators if w in text_lower),
            "helpful": sum(1 for w in helpful_indicators if w in text_lower),
        }

        if not any(scores.values()):
            return "neutral"

        return max(scores, key=scores.get)

    def get_profile(self) -> Optional[PersonalityProfile]:
        """Get the current personality profile."""
        return self._profile
