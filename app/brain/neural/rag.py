"""
AND9 — RAG Engine: Retrieval-Augmented Response Personalization.

Retrieves user profile facts, relevant episodes, and context from
EpisodicMemory to augment template responses with personalized details.

No LLM calls — uses keyword matching and template placeholders.
All retrieval is lazy and cached per query for the NeuralBridge call cycle.
"""

import logging
import re
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ── Intent → RAG Priority ───────────────────────────────────────
# Controls how aggressively we retrieve and inject context.
RAG_PRIORITY = {
    "PYTHON_CODING":    "HIGH",
    "WEB_CODING":       "HIGH",
    "CHAT":             "HIGH",
    "GENERAL_KNOWLEDGE": "MEDIUM",
    "AI_NEWS_MODELS":   "MEDIUM",
    "MEDICINE_KNOWLEDGE": "MEDIUM",
    "MOVIE_KNOWLEDGE":  "MEDIUM",
    "TIME":             "LOW",
    "DATE":             "LOW",
    "CAPABILITIES":     "LOW",
    "WEATHER":          "LOW",
}

# ── Profile keys to search by intent category ───────────────────
# These are the fact_key names in the user profile.
CATEGORY_FACTS = {
    "identity":    ["name", "age", "gender", "nationality"],
    "location":    ["city", "timezone", "country", "region"],
    "language":    ["primary_language", "secondary_language", "preferred_language"],
    "devices":     ["device_type", "os", "android_version"],
    "environment": ["dev_environment", "coding_language", "preferred_stack", "skill_level"],
    "preferences": ["communication_style", "response_style", "interests"],
    "goals":       ["current_goal", "project"],
}

# Mapping from fact_key → display label in Hindi/English
FACT_LABELS = {
    "name":                "name",
    "coding_language":     "coding_language",
    "preferred_language":  "preferred_language",
    "dev_environment":     "dev_environment",
    "device_type":         "device",
    "city":                "city",
    "current_goal":        "goal",
    "project":             "project",
    "skill_level":         "skill_level",
    "preferred_stack":     "preferred_stack",
}


class RAGContext:
    """Holds retrieved context for a single query processing cycle."""

    def __init__(self, profile: Optional[Dict] = None,
                 matched_facts: Optional[Dict] = None,
                 matched_episodes: Optional[List] = None,
                 priority: str = "NONE"):
        self.profile = profile or {}
        self.matched_facts = matched_facts or {}
        self.matched_episodes = matched_episodes or []
        self.priority = priority

    @property
    def has_context(self) -> bool:
        """True if we have any useful context to inject."""
        return bool(self.profile) or bool(self.matched_facts)

    @property
    def name(self) -> Optional[str]:
        """Get user's name from profile, if available."""
        for cat in ("identity",):
            val = self.profile.get(cat, {}).get("name")
            if val:
                return val
        return None

    @property
    def language(self) -> Optional[str]:
        """Get user's preferred coding language."""
        for cat in ("environment",):
            val = self.profile.get(cat, {}).get("coding_language")
            if val:
                return val
        return None

    @property
    def placeholders(self) -> Dict[str, str]:
        """Build a {placeholder → value} dict from profile for template filling."""
        result = {}
        for cat, keys in CATEGORY_FACTS.items():
            cat_data = self.profile.get(cat, {})
            for key in keys:
                if key in cat_data and cat_data[key]:
                    result[key] = str(cat_data[key])
                    # Also add a label variant
                    label = FACT_LABELS.get(key, key)
                    if label != key:
                        result[label] = str(cat_data[key])
        return result

    def to_dict(self) -> dict:
        return {
            "profile": self.profile,
            "matched_facts": self.matched_facts,
            "matched_episodes": self.matched_episodes,
            "priority": self.priority,
            "has_context": self.has_context,
        }


class RAGEngine:
    """Lightweight retrieval engine for response augmentation.

    Lazy-loads the EpisodicMemory singleton on first use.
    Falls back gracefully (empty RAGContext) if memory is unavailable.
    """

    def __init__(self, memory=None):
        """Initialize RAGEngine.

        Args:
            memory: Optional Memory instance. If None, lazy-loads from
                    app.memory.episodic.memory on first use.
        """
        self._memory = memory
        self._loaded = memory is not None

    def _ensure_memory(self) -> bool:
        """Lazy-load the memory system."""
        if self._loaded:
            return self._memory is not None
        self._loaded = True
        try:
            from app.memory.episodic.memory import Memory
            self._memory = Memory()
            # Quick test to see if memory actually works
            _ = self._memory.get_user_profile()
            logger.info("RAGEngine: connected to Memory")
            return True
        except Exception as e:
            logger.debug("RAGEngine: memory not available: %s", e)
            self._memory = None
            return False

    def augment(self, query: str, intent: str) -> RAGContext:
        """Retrieve relevant context for the given query + intent.

        Args:
            query: Original user query.
            intent: Classified intent string (e.g. "PYTHON_CODING").

        Returns:
            RAGContext with profile facts and matched episodes.
        """
        priority = RAG_PRIORITY.get(intent, "NONE")
        ctx = RAGContext(priority=priority)

        if priority == "NONE":
            return ctx  # Skip entirely for device actions

        if not self._ensure_memory():
            return ctx

        try:
            # 1. Always fetch the full user profile (cached in memory module)
            profile = self._memory.get_user_profile()
            ctx.profile = profile

            # 2. For HIGH/MEDIUM intents, search facts matching query keywords
            if priority in ("HIGH", "MEDIUM"):
                keywords = self._extract_keywords(query)
                matched = {}
                for kw in keywords[:5]:
                    try:
                        facts = self._memory.search_facts(kw)
                        matched.update(facts)
                    except Exception:
                        continue
                ctx.matched_facts = matched

                # 3. For HIGH intents, also search episodes for relevant past
                if priority == "HIGH":
                    try:
                        episodes = self._memory.search_episodes(query, limit=3)
                        ctx.matched_episodes = episodes
                    except Exception:
                        pass

        except Exception as e:
            logger.debug("RAGEngine: retrieval error: %s", e)

        return ctx

    def _extract_keywords(self, query: str) -> List[str]:
        """Extract meaningful keywords from a query."""
        # Remove common Hindi/English stopwords
        stopwords = {
            "kaise", "kya", "hai", "hoon", "hain", "kar", "karo", "karte",
            "ko", "ka", "ki", "ke", "se", "mein", "par", "aur", "yeh", "woh",
            "aap", "main", "mujhe", "tum", "tere", "mera", "tera",
            "the", "is", "are", "do", "does", "can", "will", "would",
            "how", "what", "why", "when", "where", "which", "who",
            "for", "this", "that", "with", "from", "have", "has",
        }
        words = re.findall(r'\w+', query.lower())
        return [w for w in words if w not in stopwords and len(w) > 2]


def get_rag_response(intent: str, query: str,
                     rag_ctx: RAGContext,
                     default_response: str) -> str:
    """Augment a template response with RAG context.

    Priority-based augmentation:
      - HIGH:  Try to fill placeholders in the message.
      - MEDIUM: Append a personal note if profile facts are available.
      - LOW:   Only inject name if available.
      - NONE:  Return the default response as-is.

    Args:
        intent: Classified intent string.
        query: Original user query.
        rag_ctx: Retrieved RAG context.
        default_response: The original template response.

    Returns:
        Augmented response string.
    """
    priority = RAG_PRIORITY.get(intent, "NONE")
    if priority == "NONE" or not rag_ctx.has_context:
        return default_response

    placeholders = rag_ctx.placeholders

    # Step 1: Try to fill {placeholders} in the default template
    if placeholders:
        filled = default_response
        for key, val in placeholders.items():
            placeholder = "{" + key + "}"
            if placeholder in filled:
                filled = filled.replace(placeholder, val)
        if filled != default_response:
            return filled

    # Step 2: For HIGH priority, append a personalized sentence
    if priority == "HIGH":
        name = rag_ctx.name
        lang = rag_ctx.language
        extras = []

        if lang:
            extras.append(f"Aap {lang} mein kaam karte hain.")
        if name:
            extras.append(f"Kya help chahiye {name}?")

        if extras:
            return default_response + " " + " ".join(extras)

    # Step 3: For MEDIUM priority, add name if available
    if priority == "MEDIUM":
        name = rag_ctx.name
        if name:
            return default_response + f" Kya poochhna chahte hain {name}?"
        return default_response

    # Step 4: For LOW priority, just use name
    name = rag_ctx.name
    if name:
        return default_response.replace("Bolo bhai", f"Bolo {name}") \
                               .replace("Kya help chahiye", f"Kya help chahiye {name}?")

    return default_response
