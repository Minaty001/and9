"""
app/skills/youtube.py — YouTube search skill.

Searches YouTube without an API key using youtube-search-python.
Returns the best matching video URL and metadata.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── Music keywords to detect intent ───────────────────────────
_MUSIC_KEYWORDS = [
    "song", "gaana", "music", "gana", "sunna", "suno", "play", "laga", "laga do",
    "bajao", "baja do", "track", "album", "singer", "artist", "band", "playlist",
    "sunao", "sunna hai", "mann hai", "feel like listening", "soft song", "sad song",
    "romantic", "peppy", "party song", "devotional", "bhajan", "ghazal",
]

_MOOD_QUERIES = {
    "soft":       "soft hindi songs",
    "sad":        "sad hindi songs",
    "romantic":   "romantic hindi songs",
    "happy":      "happy bollywood songs",
    "party":      "party songs bollywood",
    "peppy":      "peppy upbeat bollywood songs",
    "devotional": "devotional bhajan songs",
    "ghazal":     "best ghazal songs",
    "english":    "soft english songs",
    "punjabi":    "punjabi songs hits",
    "lo-fi":      "lo-fi chill music",
    "sleep":      "relaxing sleep music",
}


def is_music_request(text: str) -> bool:
    """Return True if the message looks like a music/song request."""
    t = text.lower()
    return any(kw in t for kw in _MUSIC_KEYWORDS)


def extract_search_query(text: str) -> str:
    """Convert user message into a YouTube search query.

    Examples:
        'soft song laga do' → 'soft hindi songs'
        'Arijit Singh ka koi song' → 'Arijit Singh songs'
        'Tum Hi Ho sunna hai' → 'Tum Hi Ho'
    """
    t = text.lower()

    # Detect mood/genre keywords and map to better queries
    for mood, query in _MOOD_QUERIES.items():
        if mood in t:
            return query

    # Remove filler words to isolate the song/artist name
    fillers = [
        "jarvis", "sunna hai", "sunao", "suno", "laga do", "bajao", "baja do",
        "play karo", "play kar", "chal laga", "koi bhi", "koi sa", "please",
        "yaar", "bhai", "boss", "song sunna", "mujhe", "mera", "meri",
        "mann hai", "sunne ka", "ka song", "ka gaana", "gaana", "song",
    ]
    cleaned = t
    for f in fillers:
        cleaned = cleaned.replace(f, "")
    cleaned = cleaned.strip()

    if len(cleaned) > 3:
        return cleaned + " song"

    # Generic fallback
    return "best hindi songs"


def search_youtube(query: str, max_results: int = 1) -> Optional[dict]:
    """Search YouTube and return the best match.

    Returns:
        dict with keys: title, url, channel, duration, thumbnail
        or None on failure.
    """
    try:
        from youtubesearchpython import VideosSearch
        results = VideosSearch(query, limit=max_results)
        data = results.result()
        items = data.get("result", [])
        if not items:
            return None
        best = items[0]
        return {
            "title":     best.get("title", ""),
            "url":       best.get("link", ""),
            "channel":   best.get("channel", {}).get("name", ""),
            "duration":  best.get("duration", ""),
            "thumbnail": (best.get("thumbnails") or [{}])[0].get("url", ""),
        }
    except Exception as e:
        logger.warning(f"YouTube search failed: {e}")
        return None


def handle_music_request(text: str) -> Optional[dict]:
    """Full pipeline: detect intent → build query → search → return result.

    Returns dict with 'youtube_url', 'title', 'reply' or None.
    """
    if not is_music_request(text):
        return None

    query = extract_search_query(text)
    logger.info(f"YouTube search query: '{query}'")

    result = search_youtube(query)
    if not result or not result.get("url"):
        return {
            "reply": "Yaar, abhi YouTube pe kuch mila nahi. Thodi der baad try karo!",
            "youtube_url": None,
        }

    title   = result["title"]
    url     = result["url"]
    channel = result["channel"]
    dur     = result["duration"]

    reply = f'"{title}"'
    if channel:
        reply += f" by {channel}"
    if dur:
        reply += f" ({dur})"
    reply += " — play kar rahi hoon! 🎵"

    return {
        "reply":       reply,
        "youtube_url": url,
        "title":       title,
        "channel":     channel,
        "duration":    dur,
        "thumbnail":   result.get("thumbnail", ""),
    }
