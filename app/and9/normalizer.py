"""
AND9 — Input Normalizer.

Converts Hindi/Hinglish commands into normalized English commands
so that the priority router and reflex brains see a consistent,
predictable vocabulary. Supports the full set of Hinglish action
verbs and multi-word phrases used by Hindi-speaking Android users.

Normalization pipeline:
  1. lowercase + strip
  2. Hindi phrase → English phrase (single-pass regex, longest match wins)
  3. Clean extra whitespace
  4. Remove punctuation (preserving ? and ! for intent detection)

Example mappings:
  "youtube kholo"        → "youtube open"
  "call lagao mummy ko"  → "call mummy ko"
  "alarm lagao 7 baje"   → "set alarm 7 baje"
  "torch on karo"        → "flashlight on"
  "gaana chalao"         → "song play"
  "home jao"             → "go home"
"""
import re
from typing import Tuple


# ── Hindi → English Command Mapping ──────────────────────────────
# Each key is a Hindi/Hinglish phrase, each value is the normalized
# English equivalent. Longest phrases are matched first to prevent
# partial replacement of sub-strings.
_HINDI_TO_ENGLISH = {
    # ── Open / Launch ───────────────────────────────────────────
    "kholo": "open",              # "kholo" → open
    "khol": "open",               # "khol" → open (short form)
    "chalao": "open",             # "chalao" → open/play
    "chalu karo": "open",         # "chalu karo" → turn on/open
    "launch karo": "open",        # "launch karo" → open
    "launch": "open",             # "launch" → open
    "start": "open",              # "start" → open

    # ── Close ──────────────────────────────────────────────────
    "band karo": "close",         # "band karo" → close
    "band": "close",              # "band" → close
    "bnd karo": "close",          # "bnd karo" → close (typo variant)

    # ── Search ─────────────────────────────────────────────────
    "search karo": "search",      # "search karo" → search
    "dhundo": "search",           # "dhundo" → search
    "dhundho": "search",          # "dhundho" → search
    "khojo": "search",            # "khojo" → search
    "talaash karo": "search",     # "talaash karo" → search

    # ── Play / Media ───────────────────────────────────────────
    "bajao": "play",              # "bajao" → play (music)
    "play karo": "play",          # "play karo" → play
    "chalao": "play",             # "chalao" → play (context-dependent)
    "laga do": "play",            # "laga do" → play/put on
    "sunao": "play",              # "sunao" → play/recite

    # ── Call ───────────────────────────────────────────────────
    "call lagao": "call",         # "call lagao" → call
    "phone lagao": "call",        # "phone lagao" → call
    "call karo": "call",          # "call karo" → call
    "phone karo": "call",         # "phone karo" → call
    "dial karo": "call",          # "dial karo" → call

    # ── Alarm ──────────────────────────────────────────────────
    "alarm lagao": "set alarm",   # "alarm lagao" → set alarm
    "alarm laga do": "set alarm", # "alarm laga do" → set alarm
    "alarm set karo": "set alarm",# "alarm set karo" → set alarm
    "alarm set": "set alarm",     # "alarm set" → set alarm

    # ── Reminder ───────────────────────────────────────────────
    "reminder lagao": "set reminder",    # "reminder lagao" → set reminder
    "reminder set karo": "set reminder", # "reminder set karo" → set reminder
    "yaad dilana": "set reminder",       # "yaad dilana" → remind
    "yaad dila": "set reminder",         # "yaad dila" → remind (short)
    "remind me": "set reminder",         # "remind me" → set reminder

    # ── Timer ──────────────────────────────────────────────────
    "timer lagao": "set timer",   # "timer lagao" → set timer
    "timer set karo": "set timer",# "timer set karo" → set timer
    "timer set": "set timer",     # "timer set" → set timer

    # ── Volume ─────────────────────────────────────────────────
    "volume badhao": "volume up",       # "volume badhao" → volume up
    "volume kam karo": "volume down",   # "volume kam karo" → volume down
    "awaz badhao": "volume up",         # "awaz badhao" → volume up
    "awaz kam karo": "volume down",     # "awaz kam karo" → volume down

    # ── Music / Media ──────────────────────────────────────────
    "gaana": "song",              # "gaana" → song
    "gana": "song",               # "gana" → song (alternate spelling)
    "geet": "song",               # "geet" → song
    "video chalao": "play video", # "video chalao" → play video
    "film chalao": "play movie",  # "film chalao" → play movie
    "movie chalao": "play movie", # "movie chalao" → play movie

    # ── Flashlight ─────────────────────────────────────────────
    "torch on karo": "flashlight on",   # "torch on karo" → flashlight on
    "torch off karo": "flashlight off", # "torch off karo" → flashlight off
    "light on karo": "flashlight on",   # "light on karo" → flashlight on
    "light off karo": "flashlight off", # "light off karo" → flashlight off

    # ── Home ───────────────────────────────────────────────────
    "home jao": "go home",              # "home jao" → go home
    "home screen kholo": "go home",     # "home screen kholo" → go home
    "sab apps band karo": "go home",    # "sab apps band karo" → go home (close all)
    "home": "go home",                  # "home" → go home
}

# Phrases sorted by length (longest first) so multi-word matches
# take priority over single-word sub-matches.
_HINDI_PHRASES = sorted(_HINDI_TO_ENGLISH.keys(), key=len, reverse=True)


def normalize(query: str) -> Tuple[str, bool]:
    """Normalize a user query: Hindi → English, lowercase, clean.

    Uses a single-pass regex replacement strategy to prevent
    double-replacement (e.g., "home jao" → "go home", not "go go home").
    All phrases are matched simultaneously via regex alternation, with
    the longest match winning.

    Args:
        query: Raw user input in Hindi, Hinglish, or English.

    Returns:
        Tuple of (normalized_query, was_modified). The was_modified
        flag is True if any Hindi→English conversion occurred.

    Example:
        >>> normalize("youtube kholo")
        ('youtube open', True)
        >>> normalize("home jao")
        ('go home', True)
        >>> normalize("hello world")
        ('hello world', False)
    """
    original = query
    q = query.lower().strip()

    # Build regex alternation from all Hindi phrases (longest first).
    # The re.sub engine tries alternatives left-to-right; since we
    # order longest-first, a longer phrase always beats a shorter
    # one that happens to overlap.
    escaped_phrases = [re.escape(p) for p in _HINDI_PHRASES]
    pattern = '|'.join(escaped_phrases)

    def replace_match(match):
        phrase = match.group(0)
        return _HINDI_TO_ENGLISH.get(phrase, phrase)

    if pattern:
        q = re.sub(pattern, replace_match, q)

    # Collapse multiple spaces left by replaced phrases
    q = re.sub(r'\s+', ' ', q).strip()

    # Remove punctuation (keep ? and ! for downstream intent detection)
    q = re.sub(r'[.,;:()\[\]{}"\']', '', q)

    was_modified = (q != original.lower().strip())
    return q, was_modified


def extract_potential_app_name(query: str) -> str:
    """Extract an app name from a normalized open/launch command.

    Handles both word orders produced by normalization:
      - "open youtube"  → "youtube"  (open X pattern)
      - "youtube open"  → "youtube"  (X open pattern)

    Args:
        query: Normalized query containing "open" or "launch".

    Returns:
        App name string, or empty string if no app name found.
    """
    q = query.lower().strip()

    # Pattern: "open <app_name>"
    m = re.search(r'\bopen\s+(.+)$', q)
    if m:
        return m.group(1).strip()

    # Pattern: "launch <app_name>"
    m = re.search(r'\blaunch\s+(.+)$', q)
    if m:
        return m.group(1).strip()

    # Pattern: "<app_name> open" (Hindi word order preserved)
    m = re.search(r'^(.+?)\s+open$', q)
    if m:
        return m.group(1).strip()

    # Pattern: "<app_name> launch"
    m = re.search(r'^(.+?)\s+launch$', q)
    if m:
        return m.group(1).strip()

    return ""


def extract_search_query(query: str) -> str:
    """Extract the search terms from a search/youtube query.

    Handles patterns like:
      - "search python tutorial"
      - "search cooking on youtube"
      - "youtube search cooking"

    Args:
        query: Normalized query containing "search" keywords.

    Returns:
        Search terms string. Falls back to returning the full query
        if no search-specific pattern is detected.
    """
    # Pattern: "search <terms>" or "search <terms> on youtube"
    m = re.search(r'\bsearch\s+(.+?)(?:\s+on\s+\w+)?$', query)
    if m:
        return m.group(1).strip()

    # Pattern: "youtube search <terms>"
    m = re.search(r'\byoutube\s+search\s+(.+)$', query)
    if m:
        return m.group(1).strip()

    return query
