"""
app/core/context_builder.py — Assembles rich LLM context from all memory layers.

Takes user profile, emotional context, recent episodes, and current analysis
to build a comprehensive system prompt that makes JARVIS truly context-aware.

Constitution V3:
   Rule 1 — Never instruct LLM to "confidently recall" or invent context
   Rule 4 — Honest memory boundaries: only what context contains
"""
import logging
from typing import Optional

from app.core.personality import build_personality_prompt

logger = logging.getLogger(__name__)


class ContextBuilder:
    """Builds rich context for LLM calls from all memory layers."""

    def build(
        self,
        user_profile: dict | None = None,
        emotional_context: dict | None = None,
        recent_episodes: list | None = None,
        relevant_past: list | None = None,
        current_analysis=None,
        extra_context: str = "",   # goals + events injected here
    ) -> str:
        """Assemble the complete system prompt from every memory layer."""
        expertise = "intermediate"
        if current_analysis:
            expertise = _safe_get(current_analysis, "expertise_level", "intermediate")

        parts: list[str] = [
            build_personality_prompt(
                user_profile=user_profile,
                emotional_context=emotional_context,
                expertise_level=expertise,
            )
        ]

        if recent_episodes:
            section = self._format_recent_episodes(recent_episodes)
            if section:
                parts.append(section)

        if relevant_past:
            section = self._format_relevant_past(relevant_past)
            if section:
                parts.append(section)

        if current_analysis:
            section = self._format_current_analysis(current_analysis)
            if section:
                parts.append(section)

        # ── Goals + Events context (from GoalTracker / EventSystem) ──
        if extra_context and extra_context.strip():
            parts.append(extra_context.strip())

        # ── Truth-first closing instruction (Rule 1/4) ──────────────
        parts.append(
            "REMEMBER: Respond naturally in Hinglish. "
            "Sirf upar diya hua context use karo. "
            "Agar context mein kuch nahi hai toh assume mat karo — "
            "sach bolo ki aapko nahi pata. "
            "Kabhi bhi information invent mat karo."
        )

        return "\n\n".join(parts)


    def build_minimal(
        self,
        user_profile: dict | None = None,
        expertise_level: str = "intermediate",
    ) -> str:
        """Build a minimal context for non-chat agents (coding, research etc).

        Includes only the user profile and expertise level — no emotional
        context, episodes, or conversation analysis.

        Args:
            user_profile: Key-value facts about the user.
            expertise_level: One of 'beginner', 'intermediate', 'expert'.

        Returns:
            Minimal system prompt string.
        """
        return build_personality_prompt(
            user_profile=user_profile,
            emotional_context=None,
            expertise_level=expertise_level,
        )

    # ── Private helpers ─────────────────────────────────────────

    @staticmethod
    def _format_recent_episodes(episodes: list, max_count: int = 8) -> str:
        """Format recent conversation episodes into a readable section.

        Args:
            episodes: List of dicts with 'role' and 'content' keys.
            max_count: Maximum number of episodes to include.

        Returns:
            Formatted section string.
        """
        if not episodes:
            return ""

        lines: list[str] = ["═══ RECENT CONVERSATION ═══"]
        for ep in episodes[-max_count:]:
            role = ep.get("role", "unknown")
            content = ep.get("content", "")
            # Truncate very long messages to keep context window manageable
            if len(content) > 500:
                content = content[:497] + "..."
            lines.append(f"[{role}]: {content}")
        lines.append(
            "Yeh recent conversation hai. Sirf yahi context use karo — "
            "kuch bhi invent mat karo."
        )
        return "\n".join(lines)

    @staticmethod
    def _format_relevant_past(episodes: list) -> str:
        """Format semantically relevant past episodes.

        Args:
            episodes: List of dicts with 'role', 'content', and optional 'timestamp'.

        Returns:
            Formatted section string.
        """
        if not episodes:
            return ""

        lines: list[str] = [
            "═══ RELEVANT PAST CONTEXT ═══",
            "User ne pehle is topic pe baat ki thi (yeh context mein hai):",
        ]
        for ep in episodes:
            role = ep.get("role", "unknown")
            content = ep.get("content", "")
            ts = ep.get("timestamp", "")
            if len(content) > 400:
                content = content[:397] + "..."
            prefix = f"  [{ts}] " if ts else "  "
            lines.append(f"{prefix}[{role}]: {content}")
        lines.append(
            "Sirf upar di gayi information ka reference karo. "
            "Koi bhi additional detail invent mat karo."
        )
        return "\n".join(lines)

    @staticmethod
    def _format_current_analysis(analysis) -> str:
        """Format the current message analysis into an instruction section.

        Args:
            analysis: Dict or object with keys like emotion, intensity,
                      intent, topic, expertise_level, is_memory_recall,
                      is_memory_store, entities.

        Returns:
            Formatted section string.
        """
        lines: list[str] = ["═══ CURRENT CONTEXT ═══"]

        emotion = _safe_get(analysis, "emotion", None)
        intensity = _safe_get(analysis, "intensity", None)
        if emotion:
            intensity_str = f" (intensity: {intensity}/5)" if intensity else ""
            lines.append(f"User ka current mood: {emotion}{intensity_str}")

        intent = _safe_get(analysis, "intent", None)
        if intent:
            lines.append(f"Intent: {intent}")

        topic = _safe_get(analysis, "topic", None)
        if topic:
            lines.append(f"Topic: {topic}")

        expertise = _safe_get(analysis, "expertise_level", None)
        if expertise:
            lines.append(f"Expertise level: {expertise}")

        # Memory-related flags — truth-first instructions
        if _safe_get(analysis, "is_memory_recall", False):
            lines.append(
                "User purana context yaad karna chahta hai. "
                "Agar context mein kuch nahi hai toh sach bolo "
                "ki aapko nahi pata — invent mat karo."
            )
        if _safe_get(analysis, "is_memory_store", False):
            lines.append(
                "User kuch yaad rakhne bol raha hai — "
                "acknowledge karo ki tum yaad rakh loge."
            )

        # Extracted entities
        entities = _safe_get(analysis, "entities", None)
        if entities:
            lines.append(f"Extracted info: {entities}")

        # Only return the section if we actually have data beyond the header
        if len(lines) <= 1:
            return ""
        return "\n".join(lines)


# ── Module-level helper ─────────────────────────────────────────

def _safe_get(obj, key: str, default=None):
    """Retrieve a value from a dict or object attribute, with a fallback.

    Works with both dict-like objects and objects with attributes,
    making the builder resilient to varied analysis formats.
    """
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)
