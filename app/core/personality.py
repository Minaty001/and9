"""
app/core/personality.py — JARVIS personality engine.

Constitution V3 compliant — Truth-First system prompt.
   Rule 1: Never hallucinate — if information is not in context, say "Mujhe nahi pata"
   Rule 4: Never claim memory you don't have
   Rule 6: Never present LLM-generated content as facts
"""
import logging

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Tu JARVIS hai — AI assistant, dost, aur technical partner.

=== TRUTH RULES (ALWAYS FOLLOW) ===
1. Sirf wohi information use karo jo context mein di gayi hai.
2. Agar kuch nahi pata, toh "Mujhe nahi pata" bolo. Kabhi bhi information invent mat karo.
3. Jo user ne abhi bataya hai woh yaad rakho. Past conversations ka apne aap reference mat karo.
4. "confidently recall" ya "naturally reference" mat karo — sirf context mein kya hai woh batao.
5. Agar user poochhe ki "yaad hai?" aur context mein kuch nahi hai, toh sach bolo "nahi pata".
6. Kabhi bhi "Maine pehle suna tha lekin..." type ke fake statements mat banao.

=== STYLE ===
- Hinglish default. Warm, friendly — robotic nahi. Honest. Concise.
- BREVITY (STRICT): Casual → 1-2 lines. Technical → 3-5 lines. Code → code block only. No filler.
- Pehle feelings acknowledge karo, phir task.
- Agar unclear → clarify, assume mat. Topic change → smoothly follow.

=== EMOTION ===
Happy → energy match. Sad → empathize. Stressed → check in.
User ke emotions ke hisaab se respond kar — pehle empathy, phir solution.

=== AVAILABILITY ===
- Built-in skills: web search via SerpAPI, YouTube music, event/reminder/goal management, daily review
- External agents: image generation (SeaArt), coding, research
- Jab koi skill use karni ho toh user ko batao ki kya ho raha hai
"""


# ── Expertise level instruction map ─────────────────────────────
_EXPERTISE_INSTRUCTIONS: dict[str, str] = {
    "beginner": (
        "User beginner hai — simple Hinglish mein samjha, jargon avoid kar, "
        "real-life analogies use kar. Step by step bata."
    ),
    "intermediate": (
        "User intermediate level pe hai — normal Hinglish mein explain kar, "
        "thoda technical detail de sakta hai but over-complicate mat kar."
    ),
    "expert": (
        "User expert hai — full technical depth de, basics skip kar, "
        "advanced concepts directly discuss kar. Assume strong foundation."
    ),
}


def build_personality_prompt(
    user_profile: dict | None = None,
    emotional_context: dict | None = None,
    expertise_level: str = "intermediate",
) -> str:
    """Build a dynamic personality prompt enriched with user context.

    Args:
        user_profile: Key-value facts about the user (name, profession, etc.).
        emotional_context: Mapping of topic → detected emotion/mood.
        expertise_level: One of 'beginner', 'intermediate', 'expert'.

    Returns:
        Full system prompt string ready for the LLM.
    """
    parts: list[str] = [SYSTEM_PROMPT]

    # ── User Profile ────────────────────────────────────────────
    if user_profile:
        section_lines = ["═══ USER PROFILE (context mein diya hai) ═══"]
        for key, value in user_profile.items():
            section_lines.append(f"• {key}: {value}")
        section_lines.append(
            "Yeh info context mein hai. Sirf isi ka reference karo. "
            "Agar profile mein kuch nahi hai toh assume mat karo."
        )
        parts.append("\n".join(section_lines))

    # ── Emotional Context ───────────────────────────────────────
    if emotional_context:
        section_lines = ["═══ EMOTIONAL CONTEXT ═══"]
        for topic, emotion in emotional_context.items():
            section_lines.append(f"• {topic} → {emotion}")
        section_lines.append(
            "User ke emotions ke hisaab se respond kar — "
            "pehle empathy, phir solution."
        )
        parts.append("\n".join(section_lines))

    # ── Expertise Level ─────────────────────────────────────────
    level = expertise_level.lower() if expertise_level else "intermediate"
    instruction = _EXPERTISE_INSTRUCTIONS.get(
        level, _EXPERTISE_INSTRUCTIONS["intermediate"]
    )
    parts.append(f"═══ EXPERTISE LEVEL ═══\n{instruction}")

    return "\n\n".join(parts)


# ═══════════════════════════════════════════════════════════════
# PERSONA MODEL
# ═══════════════════════════════════════════════════════════════

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional as OptionalType


@dataclass
class Persona:
    """A personality persona with tone, style, and constraints."""

    id: str
    name: str
    tone: str = "helpful"
    style_guide: str = ""
    greeting_rules: Dict[str, Any] = field(default_factory=dict)
    response_constraints: Dict[str, Any] = field(default_factory=dict)
    vocabulary_whitelist: List[str] = field(default_factory=list)
    vocabulary_blacklist: List[str] = field(default_factory=list)
    emoji_usage: str = "normal"  # never/rarely/normal/expressive
    formality_level: int = 5     # 1-10
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PersonalityProfile:
    """Current personality profile state."""

    active_persona_id: str
    tone_scores: Dict[str, float] = field(default_factory=dict)
    style_attributes: Dict[str, Any] = field(default_factory=dict)
    greeting_history: List[str] = field(default_factory=list)
    response_count: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ═══════════════════════════════════════════════════════════════
# BUILT-IN PERSONAS
# ═══════════════════════════════════════════════════════════════

BUILTIN_PERSONAS = {
    "jarvis_default": Persona(
        id="jarvis_default",
        name="JARVIS Default",
        tone="helpful",
        style_guide="Professional, clear, and concise assistant. Provide accurate information with a helpful demeanor.",
        greeting_rules={"greeting": "Hello! I'm JARVIS, your AI assistant. How can I help you today?", "time_based": True},
        response_constraints={"max_length": 500, "allow_markdown": True, "allow_code_blocks": True},
        emoji_usage="normal",
        formality_level=7,
        metadata={"category": "general", "version": "1.0"},
    ),
    "jarvis_casual": Persona(
        id="jarvis_casual",
        name="JARVIS Casual",
        tone="friendly",
        style_guide="Friendly and conversational assistant. Use everyday language, be approachable, and make the user feel comfortable.",
        greeting_rules={"greeting": "Hey there! I'm JARVIS. What's up?", "time_based": False},
        response_constraints={"max_length": 500, "allow_markdown": True, "allow_code_blocks": True},
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
        emoji_usage="never",
        formality_level=10,
        metadata={"category": "professional", "version": "1.0"},
    ),
}


# ═══════════════════════════════════════════════════════════════
# PERSONALITY ENGINE
# ═══════════════════════════════════════════════════════════════

import re as _re


class PersonalityEngine:
    """Core engine for personality management and response processing.

    Manages personas, applies tone, generates greetings, constrains responses.
    """

    def __init__(self, active_persona_id: str = "jarvis_default"):
        self._personas: Dict[str, Persona] = {}
        self._profile: OptionalType[PersonalityProfile] = None
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

    def get_persona(self) -> OptionalType[Persona]:
        """Get the active persona."""
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
        """List all registered persona IDs."""
        return list(self._personas.keys())

    def get_persona_by_id(self, persona_id: str) -> OptionalType[Persona]:
        """Get a persona by its ID."""
        return self._personas.get(persona_id)

    def apply_tone(self, text: str, persona: OptionalType[Persona] = None) -> str:
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
            adjusted = adjusted[0].upper() + adjusted[1:] if adjusted else adjusted

        if p.formality_level >= 9:
            adjusted = adjusted[0].upper() + adjusted[1:] if adjusted else adjusted
            contractions = {
                "i'm": "I am", "don't": "do not", "can't": "cannot", "won't": "will not",
                "it's": "it is", "that's": "that is", "there's": "there is",
            }
            for casual, formal in contractions.items():
                adjusted = adjusted.replace(casual, formal)
                adjusted = adjusted.replace(casual.capitalize(), formal.capitalize())

        # Update tone score
        if self._profile and p.tone in self._profile.tone_scores:
            self._profile.tone_scores[p.tone] += 1.0

        return adjusted

    def generate_greeting(self, context: OptionalType[Dict[str, Any]] = None) -> str:
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

    def constrain_response(self, text: str, persona: OptionalType[Persona] = None) -> str:
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
            constrained = _re.sub(r'[\U0001F300-\U0001F9FF]', '', constrained)

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

    def get_profile(self) -> OptionalType[PersonalityProfile]:
        """Get the current personality profile."""
        return self._profile


# ═══════════════════════════════════════════════════════════════
# PERSONALITY SERVICE
# ═══════════════════════════════════════════════════════════════

import time as _time


class PersonalityService:
    """Integrated personality service wrapping PersonalityEngine.

    Provides persona management, tone application, greeting generation,
    response constraints, and tone detection with health/stats introspection.

    Usage:
        svc = PersonalityService()
        await svc.initialize()
        greeting = await svc.generate_greeting({"time_of_day": "morning"})
    """

    def __init__(self, active_persona: str = "jarvis_default"):
        self._active_persona = active_persona
        self.engine: OptionalType[PersonalityEngine] = None
        self._initialized = False
        self._start_time = 0.0
        self._stats = {
            "tone_applications": 0,
            "greetings_generated": 0,
            "responses_constrained": 0,
            "persona_switches": 0,
            "tone_detections": 0,
        }

    async def initialize(self) -> bool:
        """Initialize the personality engine service."""
        self._start_time = _time.time()
        try:
            self.engine = PersonalityEngine(active_persona_id=self._active_persona)
            self._initialized = True
            logger.info("PersonalityService initialized with persona: %s", self._active_persona)
            return True
        except Exception as e:
            logger.error("PersonalityService init failed: %s", e)
            return False

    async def shutdown(self) -> None:
        """Shut down the personality service."""
        logger.info("PersonalityService shutting down...")
        self._initialized = False

    async def apply_tone(self, text: str, persona_id: OptionalType[str] = None) -> str:
        """Apply tone adjustments to text.

        Args:
            text: Input text.
            persona_id: Optional persona ID (uses active if not specified).

        Returns:
            Tone-adjusted text.
        """
        if not self._initialized or not self.engine:
            raise RuntimeError("PersonalityService not initialized")

        persona = self._resolve_persona(persona_id)
        self._stats["tone_applications"] += 1
        return self.engine.apply_tone(text, persona)

    async def generate_greeting(self, context: OptionalType[Dict[str, Any]] = None) -> str:
        """Generate a greeting based on active persona.

        Args:
            context: Optional context for time-based greetings.

        Returns:
            Greeting string.
        """
        if not self._initialized or not self.engine:
            raise RuntimeError("PersonalityService not initialized")

        self._stats["greetings_generated"] += 1
        return self.engine.generate_greeting(context)

    async def constrain_response(self, text: str, persona_id: OptionalType[str] = None) -> str:
        """Apply response constraints.

        Args:
            text: Response text.
            persona_id: Optional persona ID.

        Returns:
            Constrained text.
        """
        if not self._initialized or not self.engine:
            raise RuntimeError("PersonalityService not initialized")

        persona = self._resolve_persona(persona_id)
        self._stats["responses_constrained"] += 1
        return self.engine.constrain_response(text, persona)

    async def set_persona(self, persona_id: str) -> bool:
        """Set the active persona.

        Args:
            persona_id: Persona identifier.

        Returns:
            True if set successfully.
        """
        if not self._initialized or not self.engine:
            raise RuntimeError("PersonalityService not initialized")

        result = self.engine.set_persona(persona_id)
        if result:
            self._stats["persona_switches"] += 1
        return result

    async def get_persona(self, persona_id: OptionalType[str] = None) -> OptionalType[Persona]:
        """Get a persona by ID, or active persona if not specified.

        Args:
            persona_id: Optional persona ID.

        Returns:
            Persona or None.
        """
        if not self._initialized or not self.engine:
            raise RuntimeError("PersonalityService not initialized")

        if persona_id:
            return self.engine.get_persona_by_id(persona_id)
        return self.engine.get_persona()

    async def detect_tone(self, text: str) -> str:
        """Detect the tone of a text.

        Args:
            text: Text to analyze.

        Returns:
            Detected tone string.
        """
        if not self._initialized or not self.engine:
            raise RuntimeError("PersonalityService not initialized")

        self._stats["tone_detections"] += 1
        return self.engine.detect_tone(text)

    async def list_personas(self) -> List[str]:
        """List all registered persona IDs."""
        if not self._initialized or not self.engine:
            raise RuntimeError("PersonalityService not initialized")
        return self.engine.list_personas()

    async def register_persona(self, persona: Persona) -> bool:
        """Register a new persona.

        Args:
            persona: Persona to register.

        Returns:
            True if registered successfully.
        """
        if not self._initialized or not self.engine:
            raise RuntimeError("PersonalityService not initialized")
        result = self.engine.register_persona(persona)
        if result:
            self._stats["persona_switches"] += 1  # Track as a registration stat
        return result

    async def get_profile(self) -> OptionalType[PersonalityProfile]:
        """Get the current personality profile."""
        if not self._initialized or not self.engine:
            raise RuntimeError("PersonalityService not initialized")
        return self.engine.get_profile()

    async def health(self) -> Dict[str, Any]:
        """Return current health status."""
        uptime = _time.time() - self._start_time if self._start_time > 0 else 0
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "service_name": "jarvis_personality",
            "initialized": self._initialized,
            "uptime_seconds": round(uptime, 1),
        }

    async def stats(self) -> Dict[str, Any]:
        """Return service statistics."""
        uptime = _time.time() - self._start_time if self._start_time > 0 else 0
        persona = self.engine.get_persona() if self.engine else None
        return {
            "service": "jarvis_personality",
            "uptime_seconds": round(uptime, 1),
            "active_persona": persona.id if persona else "unknown",
            "persona_count": len(self.engine.list_personas()) if self.engine else 0,
            **self._stats,
        }

    def _resolve_persona(self, persona_id: OptionalType[str] = None) -> OptionalType[Persona]:
        """Resolve a persona ID to a Persona object."""
        if persona_id:
            return self.engine.get_persona_by_id(persona_id)
        return self.engine.get_persona()
