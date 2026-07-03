"""
app/core/config.py — Centralised configuration from environment variables.

All secrets come from environment variables. NO hardcoded keys.
"""
import os
from functools import lru_cache


@lru_cache()
def _str_env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


# ── Supabase (primary database) ────────────────────────────────
SUPABASE_URL = _str_env("SUPABASE_URL", "https://ipvdftzjyxwjhahfkwbq.supabase.co")
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
os.makedirs(NOTES_DIR, exist_ok=True)

# ═══════════════════════════════════════════════════════════════
# AND9 — Brain / Android-specific configuration
# ═══════════════════════════════════════════════════════════════

# ── Timer Limits ────────────────────────────────────────────────
MAX_TIMER_SECONDS = int(os.environ.get("AND9_MAX_TIMER_SECONDS", "86400"))  # 24h

# ── Pattern Learning ────────────────────────────────────────────
TIME_PATTERN_THRESHOLD = int(os.environ.get("AND9_TIME_PATTERN_THRESHOLD", "3"))
SEQUENCE_PATTERN_THRESHOLD = int(os.environ.get("AND9_SEQUENCE_PATTERN_THRESHOLD", "2"))
MAX_HISTORY_SIZE = int(os.environ.get("AND9_MAX_HISTORY_SIZE", "1000"))

# ── Contact Resolution ──────────────────────────────────────────
ENABLE_CONTACTS_CONTRACT = os.environ.get("AND9_ENABLE_CONTACTS_CONTRACT", "0") == "1"

# ── Logging ─────────────────────────────────────────────────────
DEBUG_ENABLED = os.environ.get("AND9_DEBUG", "0") == "1"
MAX_QUERY_LOGS = int(os.environ.get("AND9_MAX_QUERY_LOGS", "1000"))

# ── Android App Packages ────────────────────────────────────────
CHROME_PACKAGE = "com.android.chrome"
CHROME_COMPONENT = "com.android.chrome/com.google.android.apps.chrome.Main"
YOUTUBE_PACKAGE = "com.google.android.youtube"
YOUTUBE_COMPONENT = "com.google.android.youtube/.activities.YouTubeActivity"
