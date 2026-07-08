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
- External agents: coding, research
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
