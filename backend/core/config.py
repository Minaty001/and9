"""
app/core/config.py — Centralised configuration from environment variables.

All secrets come from environment variables. NO hardcoded keys.
"""
import os
from functools import lru_cache


@lru_cache()
def _str_env(key: str, default: str = "") -> str:
    """Read a string environment variable with an optional default (cached).

    Args:
        key: Environment variable name.
        default: Fallback value if the variable is not set (default '').

    Returns:
        The environment variable value or the default.
    """
    return os.environ.get(key, default)


# ── Supabase (primary database) ────────────────────────────────
SUPABASE_URL = _str_env("SUPABASE_URL")   # set to your Supabase project URL
SUPABASE_KEY = _str_env("SUPABASE_KEY")   # anon or service_role key from Supabase dashboard

# ── Groq (Primary LLM — fast, free tier) ───────────────────────
GROQ_API_KEY      = _str_env("GROQ_API_KEY")
GROQ_API_BASE     = "https://api.groq.com/openai/v1"
GROQ_CHAT_MODEL   = _str_env("GROQ_CHAT_MODEL",   "llama-3.3-70b-versatile")
GROQ_CODING_MODEL = _str_env("GROQ_CODING_MODEL", "llama-3.3-70b-versatile")

# ── Opencode Zen (Fallback LLM) ────────────────────────────────
OPENCODE_API_KEY      = _str_env("OPENCODE_API_KEY")
OPENCODE_API_BASE     = "https://opencode.ai/zen/v1"
OPENCODE_CHAT_MODEL   = _str_env("OPENCODE_CHAT_MODEL",   "deepseek-v4-flash-free")
OPENCODE_CODING_MODEL = _str_env("OPENCODE_CODING_MODEL", "deepseek-v4-flash-free")

# ── External APIs (optional) ───────────────────────────────────
SERP_API_KEY    = _str_env("SERP_API_KEY")
NEWS_API_KEY    = _str_env("NEWS_API_KEY")
WEATHER_API_KEY = _str_env("WEATHER_API_KEY")

# ── Vector / Embedding Search ──────────────────────────────────
ENABLE_VECTOR_SEARCH = os.environ.get("ENABLE_VECTOR_SEARCH", "").lower() in ("true", "1")
EMBEDDING_MODEL      = _str_env("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIMENSIONS = int(os.environ.get("EMBEDDING_DIMENSIONS", "384"))

# ── Deployment ─────────────────────────────────────────────────
IS_RENDER  = os.environ.get("RENDER", "").lower() in ("true", "1")
IS_TERMUX  = "TERMUX_VERSION" in os.environ
IS_WINDOWS = os.name == "nt"

# ── Legacy aliases (some agents may import these) ──────────────
MEMORY_DB  = None   # no SQLite
NOTES_DIR  = "/tmp/.jarvis_data"
STATE_FILE = "/tmp/.jarvis_data/jarvis_state.json"
# Lazy init: only create the directory when first needed
_notes_dir_created = False
def _ensure_notes_dir():
    """Create the NOTES_DIR directory on first access (lazy initialisation)."""
    global _notes_dir_created
    if not _notes_dir_created:
        os.makedirs(NOTES_DIR, exist_ok=True)
        _notes_dir_created = True
