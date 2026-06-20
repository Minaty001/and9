"""
Intent executor - generates Android Intent URIs and direct commands.
Works for both Render (cloud) fallback and on-device execution.
"""
import logging
from typing import Optional, Dict, Any
import urllib.parse

logger = logging.getLogger(__name__)


# Map of app names (English + Hinglish) to Android package names.
# The keys are matched by substring, so short aliases work.
APP_MAP: dict[str, str] = {
    # Google / System
    "youtube":    "com.google.android.youtube",
    "yt":         "com.google.android.youtube",
    "chrome":     "com.android.chrome",
    "google":     "com.google.android.googlequicksearchbox",
    "gmail":      "com.google.android.gm",
    "maps":       "com.google.android.apps.maps",
    "map":        "com.google.android.apps.maps",
    "navigate":   "com.google.android.apps.maps",
    "photos":     "com.google.android.apps.photos",
    "drive":      "com.google.android.apps.docs",
    "calendar":   "com.google.android.calendar",
    "meet":       "com.google.android.apps.meetings",

    # Communication
    "whatsapp":   "com.whatsapp",
    "wa":         "com.whatsapp",
    "wapp":       "com.whatsapp",
    "telegram":   "org.telegram.messenger",
    "tg":         "org.telegram.messenger",
    "instagram":  "com.instagram.android",
    "ig":         "com.instagram.android",
    "insta":      "com.instagram.android",
    "facebook":   "com.facebook.katana",
    "fb":         "com.facebook.katana",
    "messenger":  "com.facebook.orca",
    "twitter":    "com.twitter.android",
    "x":          "com.twitter.android",

    # Media
    "spotify":    "com.spotify.music",
    "netflix":    "com.netflix.mediaclient",
    "prime":      "com.amazon.primevideo",
    "hotstar":    "in.startv.hotstar",
    "jio":        "com.jio.media.jiocinema",
    "gaana":      "com.gaana.app",

    # Phone / Contacts
    "phone":      "com.android.phone",
    "dialer":     "com.android.dialer",
    "contacts":   "com.android.contacts",
    "truecaller": "com.truecaller",

    # Tools
    "calculator": "com.google.android.calculator",
    "calc":       "com.google.android.calculator",
    "calci":      "com.google.android.calculator",
    "camera":     "com.android.camera",
    "settings":   "com.android.settings",
    "file":       "com.android.documentsui",
    "files":      "com.android.documentsui",
    "clock":      "com.google.android.deskclock",
    "alarm":      "com.google.android.deskclock",
    "play store": "com.android.vending",
    "playstore":  "com.android.vending",
    "store":      "com.android.vending",

    # Browsers
    "firefox":    "org.mozilla.firefox",
    "edge":       "com.microsoft.emmx",
    "brave":      "com.brave.browser",
    "opera":      "com.opera.browser",
    "uc":         "com.UCMobile.intl",

    # Productivity
    "keep":       "com.google.android.keep",
    "notes":      "com.google.android.keep",
    "docs":       "com.google.android.apps.docs",
    "sheets":     "com.google.android.apps.docs.sheets",
    "slides":     "com.google.android.apps.docs.slides",

    # Shopping
    "flipkart":   "com.flipkart.android",
    "amazon":     "com.amazon.mshop.android",
    "myntra":     "com.myntra.android",
    "meesho":     "com.meesho.supply",

    # Payments
    "gpay":       "com.google.android.apps.nbu.paisa.user",
    "google pay": "com.google.android.apps.nbu.paisa.user",
    "phonepe":    "com.phonepe.app",
    "paytm":      "net.one97.paytm",

    # Travel
    "uber":       "com.ubercab",
    "ola":        "com.olacabs.customer",
    "irctc":      "com.irctc.passenger",
    "redbus":     "in.redbus.android",

    # Food
    "zomato":     "com.application.zomato",
    "swiggy":     "in.swiggy.android",
}

# Hinglish phrase → normalized app_name mapping
HINGLISH_ALIASES: dict[str, str] = {
    "yt": "youtube",
    "y t": "youtube",
    "wa": "whatsapp",
    "w p": "whatsapp",
    "insta": "instagram",
    "ig": "instagram",
    "fb": "facebook",
    "tg": "telegram",
    "calc": "calculator",
    "maps": "maps",
    "gmail": "gmail",
    "camera": "camera",
    "phone": "phone",
    "settings": "settings",
    "store": "play store",
    "gp": "google pay",
    "pp": "phonepe",
}


class IntentExecutor:
    """Generate executable intents for Android apps."""

    @staticmethod
    def resolve_app_name(name: str) -> str:
        """Normalize user-spoken app name. Checks Hinglish aliases first."""
        raw = name.lower().strip()
        compact = raw.replace(" ", "")
        if compact in HINGLISH_ALIASES:
            return HINGLISH_ALIASES[compact]
        return raw

    @staticmethod
    def _match_app(name: str) -> Optional[str]:
        """Match name to a package. Priority: exact match > longest substring match.

        Single-character keys are excluded from substring matching to avoid
        false positives (e.g. 'x' for Twitter matching 'netflix').
        """
        if name in APP_MAP:
            return APP_MAP[name]
        candidates = []
        for key, pkg in APP_MAP.items():
            if len(key) >= 2 and key in name:
                candidates.append((len(key), pkg))
        if candidates:
            candidates.sort(key=lambda x: -x[0])
            return candidates[0][1]
        return None

    @staticmethod
    def open_app(app_name: str) -> Dict[str, Any]:
        """Generate app opening intent. Supports Hinglish aliases."""
        name = IntentExecutor.resolve_app_name(app_name)
        package = IntentExecutor._match_app(name)

        if not package:
            # Retry with compact form (no spaces) as fallback
            compact = name.replace(" ", "")
            if compact != name:
                package = IntentExecutor._match_app(compact)

        if not package:
            return {"error": f"App '{app_name}' not found in registry (searched: {name})"}

        return {
            "action": "LAUNCH_APP",
            "package": package,
            "category": "android.intent.category.LAUNCHER",
            "extras": {}
        }

    @staticmethod
    def play_youtube(query: str, video_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate YouTube playback intent."""
        if video_id:
            intent_uri = f"https://www.youtube.com/watch?v={video_id}"
            return {
                "action": "VIEW",
                "data": intent_uri,
                "package": "com.google.android.youtube",
                "extras": {"is_video": True}
            }
        search_query = urllib.parse.quote(query)
        intent_uri = f"https://www.youtube.com/results?search_query={search_query}"
        return {
            "action": "VIEW",
            "data": intent_uri,
            "package": "com.google.android.youtube",
            "extras": {"is_search": True}
        }

    @staticmethod
    def set_alarm(hour: int, minute: int, label: str = "Jarvis Alarm") -> Dict[str, Any]:
        return {
            "action": "SET_ALARM",
            "package": "com.android.deskclock",
            "extras": {
                "hour": hour, "minute": minute,
                "label": label, "skip_ui": False
            }
        }

    @staticmethod
    def create_reminder(title: str, time_str: str) -> Dict[str, Any]:
        return {
            "action": "CREATE_EVENT",
            "package": "com.google.android.calendar",
            "extras": {"title": title, "time": time_str, "type": "reminder"}
        }

    @staticmethod
    def make_call(number: str) -> Dict[str, Any]:
        clean_number = ''.join(filter(lambda x: x.isdigit() or x == '+', number))
        return {
            "action": "CALL",
            "data": f"tel:{clean_number}",
            "package": "com.android.phone",
            "extras": {}
        }

    @staticmethod
    def list_apps() -> list:
        """Return all registered app names (for suggestions / help)."""
        return sorted(set(k for k in APP_MAP.keys() if len(k) > 1))
