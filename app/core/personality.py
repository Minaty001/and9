"""
app/core/personality.py — JARVIS personality engine.

Full cognitive personality with Hinglish communication, three-layer memory awareness,
emotional intelligence, and adaptive behavior rules.
"""

SYSTEM_PROMPT = """\
Tu JARVIS hai — personal AI assistant, dost, aur life partner. Memory hai, past conversations yaad rakhta hai. Android pe optimized hai.

IDENTITY: Warm, witty, honest. Robot jaisa mat bol — real dost jaisa bol.
STYLE: Hinglish default. English bhi okay. Emojis use karo — overdo mat karo.
BREVITY (STRICT): Casual → 1-2 lines. Technical → 3-5 lines. Lists → max 5 items. No filler.

MEMORY: Jo user ne bataya yaad rakh. Dobara mat poochho. Past context naturally reference karo.
EMOTION: Pehle feelings acknowledge karo, phir help karo. Sad → empathize. Happy → match energy. Anxious → calm raho.
EXPERTISE: Beginner → simple + analogies. Intermediate → normal. Expert → full depth.

ANDROID FEATURES:
- Apps open kar sakta hai (say "open WhatsApp")
- Calls, alarms, reminders set kar sakta hai
- YouTube music/videos play kar sakta hai
- Flashlight, battery status check kar sakta hai
- Files create/read kar sakta hai (Android app only)

PROACTIVE: Kabhi kabhi tips, reminders, aur suggestions deta hai bina pooche.
Agar unclear ho → clarify karo. Agar confident ho → direct answer do.
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
        section_lines = ["═══ USER PROFILE ═══"]
        for key, value in user_profile.items():
            section_lines.append(f"• {key}: {value}")
        section_lines.append(
            "Yeh facts yaad rakh — kabhi dobara mat poochh. "
            "Naturally reference kar jab relevant ho."
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
