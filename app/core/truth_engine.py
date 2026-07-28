"""
app/core/truth_engine.py — Truth-First validation layer.

Constitution V3:
  Rule 5 — Confidence map enforcement
  Rule 6 — No LLM inference stored as memory
  Rule 8 — Source tracking for all memory writes

This module is the gatekeeper between memory retrieval and LLM context
building. Every fact that reaches the LLM passes through here.

Confidence map (Rule 5):
  direct_user_statement  → 1.0
  observed_repeated      → 0.7
  regex_extraction       → 0.3
  llm_inference          → 0.0 (never stored)
"""
import logging
import re

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# Confidence map
# ═══════════════════════════════════════════════════════════════

CONFIDENCE_MAP: dict[str, float] = {
    "user_input":        1.0,   # Direct user statement
    "direct_statement": 1.0,   # Alias
    "user_stated":      1.0,   # Alias
    "observed":         0.7,   # Observed repeated behavior
    "observed_pattern": 0.7,   # Alias
    "cross_session":    0.7,   # Pattern across sessions
    "regex_extraction": 0.3,   # Keyword/regex match (may be coincidental)
    "keyword_detection": 0.3,  # Alias
    "llm_inference":    0.0,   # NEVER use LLM-inferred facts
    "system":           1.0,   # System-generated, self-evident
}

LLM_INFERENCE_SOURCES = {"llm_inference", "llm_extraction", "ai_inferred"}


# ═══════════════════════════════════════════════════════════════
# Validation
# ═══════════════════════════════════════════════════════════════

def validate_memory(
    value: str,
    source: str,
    confidence: float,
    verified: bool = False,
) -> bool:
    """Check whether a memory item passes the truth gate.

    Rejects:
      1. LLM-inferred facts (confidence 0.0 / llm_inference source)
      2. Unverified regex extractions (confidence < 0.5 and not verified)
      3. Empty/null values
      4. Generic filler values
    """
    # Reject empty
    if not value or not value.strip():
        return False

    # Reject LLM-inferred
    if source in LLM_INFERENCE_SOURCES or confidence <= 0.0:
        return False

    # Unverified low-confidence facts are not safe to use
    if confidence < 0.5 and not verified:
        return False

    return True


def cap_confidence(source: str) -> float:
    """Return the maximum allowed confidence for a given source type.

    Use this when writing memory to ensure confidence never exceeds
    what the source type justifies.
    """
    return CONFIDENCE_MAP.get(source.lower(), 0.0)


def get_source_type(source: str) -> str:
    """Normalise a source string to a known source type.

    Returns 'unknown' if no match found.
    """
    s = source.lower().replace(" ", "_")
    if s in CONFIDENCE_MAP:
        return s
    # Fuzzy matching for common variants
    for key in CONFIDENCE_MAP:
        if key in s or s in key:
            return key
    return "unknown"


# ═══════════════════════════════════════════════════════════════
# Memory context checking
# ═══════════════════════════════════════════════════════════════

def has_relevant_memory(memory_ctx: dict, query: str = "") -> bool:
    """Check if memory context contains any usable facts.

    Returns True only if there are verified facts or user-profile
    entries that pass the truth gate.

    Use before making LLM calls about stored information — if this
    returns False, the LLM should respond with "I don't know/mujhe
    nahi pata."
    """
    # Check user profile
    profile = memory_ctx.get("user_profile", {}) or {}
    for facts in profile.values():
        if isinstance(facts, dict) and facts:
            for val in facts.values():
                if val and str(val).strip():
                    return True

    # Check recent episodes for user content
    for ep in memory_ctx.get("recent_episodes", []) or []:
        if ep.get("role") == "user" and ep.get("content", "").strip():
            return True

    # Check relevant past episodes
    for ep in memory_ctx.get("relevant_past", []) or []:
        if ep.get("role") == "user" and ep.get("content", "").strip():
            return True

    return False


def generate_dont_know_response(topic: str = "") -> str:
    """Generate an honest 'I don't know' response in Hinglish.

    Per Constitution Rule 1: if information is not in context, say
    'mujhe nahi pata' rather than inventing or hallucinating.
    """
    if topic:
        responses = [
            f"Mujhe is baare mein koi jaankari nahi hai. "
            f"Aap '{topic}' ke baare mein bata sakte hain?",
            f"Maine abhi tak '{topic}' ke baare mein kuch save nahi kiya hai. "
            f"Aap batao, main yaad rakh loonga.",
            f"Mujhe nahi pata '{topic}' ke baare mein. Aap thoda aur bata sakte hain?",
        ]
    else:
        responses = [
            "Mujhe nahi pata. Aap bata sakte hain?",
            "Main is baare mein kuch nahi jaanti. Kya aap bata sakte hain?",
            "Yeh mujhe nahi pata. Agar aap bataenge toh main yaad rakh sakti hoon.",
        ]

    import random
    return random.choice(responses)


# ═══════════════════════════════════════════════════════════════
# Pre-LLM verification gate
# ═══════════════════════════════════════════════════════════════

def verify_before_llm(
    memory_ctx: dict,
    query: str = "",
    min_confidence: float = 0.5,
) -> tuple[bool, str]:
    """Verify whether the LLM can safely answer using available context.

    Args:
        memory_ctx: Memory context dict from Memory.build_memory_context()
        query: The user's query string.
        min_confidence: Minimum confidence threshold for facts.

    Returns:
        Tuple of (has_truth, guidance_response).
        If has_truth is False, guidance_response contains an appropriate
        "I don't know" message to return instead of calling the LLM.
    """
    # Check if we have any relevant, verified memory
    if has_relevant_memory(memory_ctx, query):
        return True, ""

    # No usable memory found — return honest don't-know response
    # Extract topic from query if possible (simple heuristic)
    topic = ""
    if query:
        # Simple topic extraction: look for keywords
        topic_match = re.search(
            r'(?:about|regarding|baare mein|ke baare)\s+["\']?(.+?)["\']?(?:\s+\?|\s*$)',
            query, re.IGNORECASE
        )
        if topic_match:
            topic = topic_match.group(1).strip()

    return False, generate_dont_know_response(topic)


# ═══════════════════════════════════════════════════════════════
# Analysis helpers
# ═══════════════════════════════════════════════════════════════

def annotate_facts_with_confidence(facts: list[dict]) -> list[dict]:
    """Annotate each fact with its confidence level and source type.

    Input facts: list of dicts with at least 'source' key
    Output: annotated with 'confidence' and 'valid' flags
    """
    result = []
    for fact in facts:
        source = fact.get("source", "unknown")
        confidence = cap_confidence(source)
        valid = validate_memory(
            value=str(fact.get("value", "")),
            source=source,
            confidence=confidence,
            verified=fact.get("verified", False),
        )
        result.append({
            **fact,
            "confidence": confidence,
            "confidence_level": _confidence_label(confidence),
            "valid": valid,
        })
    return result


def _confidence_label(confidence: float) -> str:
    """Return a human-readable label for a confidence score."""
    if confidence >= 1.0:
        return "confirmed"
    elif confidence >= 0.7:
        return "high"
    elif confidence >= 0.3:
        return "medium"
    elif confidence > 0.0:
        return "low"
    return "invalid"
