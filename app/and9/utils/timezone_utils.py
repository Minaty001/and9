"""
AND9 — Timezone Utilities for Indian Cities.

Provides timezone-aware time lookups for Indian cities using
Python 3.9+ zoneinfo (standard library, no extra dependencies).

Supported cities:
    Kolkata, Delhi, Mumbai, Chennai, Bengaluru, Hyderabad,
    Ahmedabad, Pune, Jaipur, Lucknow, Chandigarh, Bhopal,
    Indore, Kochi, Nagpur, Patna, Surat, Bhubaneswar,
    Guwahati, Amritsar, Varanasi, Agra,
    plus generic "india"

All map to Asia/Kolkata (IST, UTC+5:30).
"""
import re
from datetime import datetime, date
from zoneinfo import ZoneInfo

# ── Supported Indian cities → timezone ─────────────────────────────
INDIAN_TIMEZONE = "Asia/Kolkata"
INDIAN_OFFSET = "+05:30"

SUPPORTED_CITIES: dict[str, str] = {
    # Metros
    "kolkata": INDIAN_TIMEZONE,
    "calcutta": INDIAN_TIMEZONE,
    "delhi": INDIAN_TIMEZONE,
    "new delhi": INDIAN_TIMEZONE,
    "dilli": INDIAN_TIMEZONE,
    "mumbai": INDIAN_TIMEZONE,
    "bombay": INDIAN_TIMEZONE,
    "chennai": INDIAN_TIMEZONE,
    "madras": INDIAN_TIMEZONE,
    "bangalore": INDIAN_TIMEZONE,
    "bengaluru": INDIAN_TIMEZONE,
    "hyderabad": INDIAN_TIMEZONE,
    # Major cities
    "ahmedabad": INDIAN_TIMEZONE,
    "pune": INDIAN_TIMEZONE,
    "jaipur": INDIAN_TIMEZONE,
    "lucknow": INDIAN_TIMEZONE,
    "chandigarh": INDIAN_TIMEZONE,
    "bhopal": INDIAN_TIMEZONE,
    "indore": INDIAN_TIMEZONE,
    "kochi": INDIAN_TIMEZONE,
    "cochin": INDIAN_TIMEZONE,
    "nagpur": INDIAN_TIMEZONE,
    "patna": INDIAN_TIMEZONE,
    "surat": INDIAN_TIMEZONE,
    "bhubaneswar": INDIAN_TIMEZONE,
    "guwahati": INDIAN_TIMEZONE,
    "amritsar": INDIAN_TIMEZONE,
    "varanasi": INDIAN_TIMEZONE,
    "banaras": INDIAN_TIMEZONE,
    "agra": INDIAN_TIMEZONE,
    # Generic
    "india": INDIAN_TIMEZONE,
}

# ── City-name patterns in queries ──────────────────────────────────
_CITY_TIME_PATTERNS = [
    # "{city} ka time / ka samay"
    re.compile(
        r'(?:ka\s+)?(?:time|samay|bajaa|baje|ghanti)\s+(?:kya|bata)\S?\s*(?:hai)?',
        re.IGNORECASE,
    ),
    # "time in {city}"
    re.compile(r'time\s+(?:in|of|for)\s+\w+', re.IGNORECASE),
    # "what's the time in {city}"
    re.compile(r'(?:what|what\'?s|whats)\s+(?:is\s+)?(?:the\s+)?time\s+(?:in|of|at)\s+\w+', re.IGNORECASE),
    # pure "{city} time" at end of query
    re.compile(r'\w+\s+time\s*$', re.IGNORECASE),
]

# ── City name extractor from query ─────────────────────────────────
# Match known city names (word boundary anchored)
_CITY_IN_QUERY = re.compile(
    r'\b(?:'
    r'kolkata|calcutta|delhi|new\s*delhi|dilli|mumbai|bombay|'
    r'chennai|madras|bangalore|bengaluru|hyderabad|'
    r'ahmedabad|pune|jaipur|lucknow|chandigarh|bhopal|'
    r'indore|kochi|cochin|nagpur|patna|surat|bhubaneswar|'
    r'guwahati|amritsar|varanasi|banaras|agra|india'
    r')\b',
    re.IGNORECASE,
)


def detect_city_time_query(query: str) -> str | None:
    """Detect if a query is asking for time in a specific city.

    Args:
        query: Raw user query string.

    Returns:
        Normalized city name (lowercase), or None if no city time query.
    """
    if not query:
        return None
    q = query.lower().strip()

    # Must have a time-related keyword
    has_time_kw = any(
        kw in q
        for kw in ["time", "samay", "bajaa", "baje", "ghanti", "batao", "kitne"]
    )
    if not has_time_kw:
        return None

    # Find a known city name in the query
    m = _CITY_IN_QUERY.search(q)
    if not m:
        return None

    city = m.group(0).strip()
    # Normalize: "new delhi" (with space) → handle via key lookup
    # Check for "new delhi" two-word variant
    for two_word in ["new delhi"]:
        if two_word in q:
            return two_word

    return city


def get_time_in_city(city_name: str) -> dict | None:
    """Get the current time in a given Indian city.

    Args:
        city_name: Lowercase city name (e.g. "kolkata", "delhi").

    Returns:
        Dict with time info, or None if city is not supported.
    """
    normalized = city_name.lower().strip()
    tz_name = SUPPORTED_CITIES.get(normalized)
    if tz_name is None:
        return None

    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)
    today = date.today()

    # 12-hour format
    hour_12 = now.hour % 12 or 12
    period = "AM" if now.hour < 12 else "PM"
    time_12 = f"{hour_12}:{now.minute:02d}:{now.second:02d} {period}"

    # 24-hour format
    time_24 = f"{now.hour:02d}:{now.minute:02d}:{now.second:02d}"

    # City display name
    display_name = normalized.title()

    return {
        "city": display_name,
        "city_key": normalized,
        "timezone": tz_name,
        "time_12h": time_12,
        "time_24h": time_24,
        "hour": now.hour,
        "minute": now.minute,
        "second": now.second,
        "date": today.isoformat(),
        "weekday": now.strftime("%A"),
        "offset": INDIAN_OFFSET,
        "timestamp": now.timestamp(),
        "datetime_iso": now.isoformat(),
    }


def format_city_time_response(city_name: str) -> str:
    """Format a natural language response for time in a city.

    Args:
        city_name: Lowercase city name.

    Returns:
        Human-readable time string.
    """
    info = get_time_in_city(city_name)
    if info is None:
        return f"Sorry, I don't know the timezone for '{city_name}'."

    return (
        f"In {info['city']}, it's {info['time_12h']} ({info['weekday']}, "
        f"{info['date']}, {info['timezone']} {info['offset']})"
    )
