"""
AND9 — Query Normalizer (Phase 2 of Refactor).

Centralized Hindi/Hinglish → English command normalization.
Single-pass regex alternation to prevent double-replacement.

All mappings are in the REPLACEMENTS dict. Longest phrases
are matched first.
"""
import re
from typing import Tuple


class QueryNormalizer:
    """Normalize user queries from Hindi/Hinglish to English commands.

    Example:
        >>> qn = QueryNormalizer()
        >>> qn.normalize("youtube kholo")
        ('open youtube', True)
        >>> qn.normalize("call lagao mummy ko")
        ('call mummy ko', True)
        >>> qn.normalize("home jao")
        ('go home', True)
    """

    # ── Hindi → English Replacement Map ────────────────────────────
    # Per Phase 2 spec: exact mappings the user specified.
    # Sorted by length (longest first) to prevent sub-string matches.
    REPLACEMENTS = {
        # ── Open / Launch ───────────────────────────────────────
        "youtube kholo": "open youtube",
        "camera kholo": "open camera",
        "open karo": "open",
        "launch karo": "open",
        "kholo": "open",

        # ── Close ───────────────────────────────────────────────
        "band karo": "close",

        # ── Search ──────────────────────────────────────────────
        "search karo": "search",
        "dhundo": "search",

        # ── Call ────────────────────────────────────────────────
        "phone lagao": "call",
        "call lagao": "call",

        # ── Alarm ───────────────────────────────────────────────
        "alarm lagao": "set alarm",

        # ── Reminder ────────────────────────────────────────────
        "reminder lagao": "set reminder",

        # ── Timer ───────────────────────────────────────────────
        "timer lagao": "set timer",

        # ── Home (critical — no other path catches "home jao") ──
        "home jao": "go home",
    }

    def __init__(self):
        # Build single-pass regex: longest phrases first
        phrases = sorted(self.REPLACEMENTS.keys(), key=len, reverse=True)
        escaped = [re.escape(p) for p in phrases]
        self._pattern = '|'.join(escaped) if escaped else None

    def normalize(self, query: str) -> Tuple[str, bool]:
        """Convert Hindi/Hinglish query to normalized English.

        Args:
            query: Raw user input.

        Returns:
            Tuple of (normalized_query, was_modified).
        """
        original = query
        q = query.lower().strip()
        if not q:
            return q, False

        if self._pattern:
            def replace_fn(match):
                phrase = match.group(0)
                return self.REPLACEMENTS.get(phrase, phrase)
            q = re.sub(self._pattern, replace_fn, q)

        # Collapse multiple spaces
        q = re.sub(r'\s+', ' ', q).strip()
        # Remove punctuation (keep ? and !)
        q = re.sub(r'[.,;:()\[\]{}"\']', '', q)

        was_modified = (q != original.lower().strip())
        return q, was_modified

    def extract_app_name(self, query: str) -> str:
        """Extract app name from open/launch commands."""
        q = query.lower().strip()

        # "open <app>"
        m = re.search(r'\bopen\s+(.+)$', q)
        if m:
            return m.group(1).strip()

        # "launch <app>"
        m = re.search(r'\blaunch\s+(.+)$', q)
        if m:
            return m.group(1).strip()

        # "<app> open"
        m = re.search(r'^(.+?)\s+open$', q)
        if m:
            return m.group(1).strip()

        return ""

    def extract_search_terms(self, query: str) -> str:
        """Extract search terms from search/youtube queries."""
        q = query.lower().strip()

        # "search <terms>"
        m = re.search(r'\bsearch\s+(.+?)$', q)
        if m:
            return m.group(1).strip()

        # "youtube search <terms>"
        m = re.search(r'\byoutube\s+search\s+(.+)$', q)
        if m:
            return m.group(1).strip()

        return q

    def extract_time_expression(self, query: str) -> str:
        """Extract the time-related portion of a query."""
        time_patterns = [
            r'(?:after|in|baad|me|ke\s*baad|for|at|ko)\s+\d[\d\s:ampm]*',
            r'\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM|baje)?',
        ]
        for pattern in time_patterns:
            m = re.search(pattern, query)
            if m:
                return m.group(0).strip()
        return ""
