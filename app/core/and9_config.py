"""
AND9 — Centralized Configuration.

All configurable parameters in one place so they can be tuned
without hunting through source files.
"""
import os

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

# ── API ─────────────────────────────────────────────────────────
CHROME_PACKAGE = "com.android.chrome"
CHROME_COMPONENT = "com.android.chrome/com.google.android.apps.chrome.Main"
YOUTUBE_PACKAGE = "com.google.android.youtube"
YOUTUBE_COMPONENT = "com.google.android.youtube/.activities.YouTubeActivity"
