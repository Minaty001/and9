"""
Timezone Utilities for Indian Cities — standalone version for micro_brain.

Provides timezone-aware time lookups for Indian cities using
Python 3.9+ zoneinfo (standard library, no extra dependencies).

Supported cities: Kolkata, Delhi, Mumbai, Chennai, Bengaluru, Hyderabad,
and 16+ other Indian cities — all mapping to Asia/Kolkata (IST, UTC+5:30).
"""
import re
from datetime import datetime
from zoneinfo import ZoneInfo

INDIAN_TIMEZONE = "Asia/Kolkata"
INDIAN_OFFSET = "+05:30"

SUPPORTED_CITIES: dict[str, str] = {
    "kolkata": INDIAN_TIMEZONE, "calcutta": INDIAN_TIMEZONE,
    "delhi": INDIAN_TIMEZONE, "new delhi": INDIAN_TIMEZONE, "dilli": INDIAN_TIMEZONE,
    "mumbai": INDIAN_TIMEZONE, "bombay": INDIAN_TIMEZONE,
    "chennai": INDIAN_TIMEZONE, "madras": INDIAN_TIMEZONE,
    "bangalore": INDIAN_TIMEZONE, "bengaluru": INDIAN_TIMEZONE,
    "hyderabad": INDIAN_TIMEZONE,
    "ahmedabad": INDIAN_TIMEZONE, "pune": INDIAN_TIMEZONE,
    "jaipur": INDIAN_TIMEZONE, "lucknow": INDIAN_TIMEZONE,
    "chandigarh": INDIAN_TIMEZONE, "bhopal": INDIAN_TIMEZONE,
    "indore": INDIAN_TIMEZONE, "kochi": INDIAN_TIMEZONE,
    "nagpur": INDIAN_TIMEZONE, "patna": INDIAN_TIMEZONE,
    "surat": INDIAN_TIMEZONE, "bhubaneswar": INDIAN_TIMEZONE,
    "guwahati": INDIAN_TIMEZONE, "amritsar": INDIAN_TIMEZONE,
    "varanasi": INDIAN_TIMEZONE, "banaras": INDIAN_TIMEZONE,
    "agra": INDIAN_TIMEZONE,
    "india": INDIAN_TIMEZONE,
}

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
    """Detect if a query is asking for time in a specific Indian city."""
    if not query:
        return None
    q = query.lower().strip()
    has_time_kw = any(kw in q for kw in ["time", "samay", "bajaa", "baje", "ghanti", "batao", "kitne"])
    if not has_time_kw:
        return None
    m = _CITY_IN_QUERY.search(q)
    if not m:
        return None
    city = m.group(0).strip()
    for two_word in ["new delhi"]:
        if two_word in q:
            return two_word
    return city


def get_time_in_city(city_name: str) -> dict | None:
    """Get the current time in a given Indian city."""
    normalized = city_name.lower().strip()
    tz_name = SUPPORTED_CITIES.get(normalized)
    if tz_name is None:
        return None
    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)
    today = now.date()
    hour_12 = now.hour % 12 or 12
    period = "AM" if now.hour < 12 else "PM"
    time_12 = f"{hour_12}:{now.minute:02d}:{now.second:02d} {period}"
    time_24 = f"{now.hour:02d}:{now.minute:02d}:{now.second:02d}"
    return {
        "city": normalized.title(),
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
    """Format a natural language response for time in a city."""
    info = get_time_in_city(city_name)
    if info is None:
        return f"Sorry, I don't know the timezone for '{city_name}'."
    return (
        f"In {info['city']}, it's {info['time_12h']} ({info['weekday']}, "
        f"{info['date']}, {info['timezone']} {info['offset']})"
    )
