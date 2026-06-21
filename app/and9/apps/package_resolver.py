"""
AND9 — Dynamic Package Resolver (Phase 6 of Refactor).

Resolves app names to Android Intent launch parameters.
Merges IntentExecutor.APP_MAP (60+ apps) with Hindi aliases
and short codes for comprehensive coverage.

Supports:
    - Exact name resolution
    - Alias resolution (yt→youtube, wa→whatsapp, insta→instagram)
    - Fuzzy matching for partial names

In production, this should also query Android PackageManager
for dynamically discovering installed apps.
"""
import logging
from difflib import get_close_matches
from typing import Optional

logger = logging.getLogger(__name__)


class PackageResolver:
    """Resolve app names to Android Intent launch parameters.

    Maintains an extended app mapping with Hindi aliases and
    region-specific name variants common in Indian mobile usage.

    Attributes:
        app_map: Dict mapping canonical app name → Intent dict.
        aliases: Dict mapping alias → canonical name.
    """

    def __init__(self):
        # ── Extended App Map ────────────────────────────────────
        # Merges IntentExecutor.APP_MAP coverage with extra aliases.
        self.app_map = {
            # ── Social & Communication ──────────────────────────
            "youtube": {
                "action": "android.intent.action.MAIN",
                "package": "com.google.android.youtube",
                "component": "com.google.android.youtube/.activities.YouTubeActivity",
                "category": "android.intent.category.LAUNCHER",
            },
            "whatsapp": {
                "action": "android.intent.action.MAIN",
                "package": "com.whatsapp",
                "component": "com.whatsapp/.HomeActivity",
                "category": "android.intent.category.LAUNCHER",
            },
            "telegram": {
                "action": "android.intent.action.MAIN",
                "package": "org.telegram.messenger",
                "component": "org.telegram.messenger/.DefaultIcon",
                "category": "android.intent.category.LAUNCHER",
            },
            "instagram": {
                "action": "android.intent.action.MAIN",
                "package": "com.instagram.android",
                "component": "com.instagram.android/.activity.MainTabActivity",
                "category": "android.intent.category.LAUNCHER",
            },
            "facebook": {
                "action": "android.intent.action.MAIN",
                "package": "com.facebook.katana",
                "component": "com.facebook.katana/.LoginActivity",
                "category": "android.intent.category.LAUNCHER",
            },
            "messenger": {
                "action": "android.intent.action.MAIN",
                "package": "com.facebook.orca",
                "component": "com.facebook.orca/.app.IntentDispatchActivity",
                "category": "android.intent.category.LAUNCHER",
            },
            "twitter": {
                "action": "android.intent.action.MAIN",
                "package": "com.twitter.android",
                "component": "com.twitter.android/.StartActivity",
                "category": "android.intent.category.LAUNCHER",
            },
            "linkedin": {
                "action": "android.intent.action.MAIN",
                "package": "com.linkedin.android",
                "component": "com.linkedin.android/.home.ProminentMainActivity",
                "category": "android.intent.category.LAUNCHER",
            },
            "snapchat": {
                "action": "android.intent.action.MAIN",
                "package": "com.snapchat.android",
                "component": "com.snapchat.android/.LandingPageActivity",
                "category": "android.intent.category.LAUNCHER",
            },

            # ── Browsers ────────────────────────────────────────
            "chrome": {
                "action": "android.intent.action.VIEW",
                "package": "com.android.chrome",
                "component": "com.android.chrome/com.google.android.apps.chrome.Main",
                "category": "android.intent.category.LAUNCHER",
            },
            "firefox": {
                "action": "android.intent.action.MAIN",
                "package": "org.mozilla.firefox",
                "component": "org.mozilla.firefox/org.mozilla.gecko.BrowserApp",
                "category": "android.intent.category.LAUNCHER",
            },

            # ── System ──────────────────────────────────────────
            "camera": {
                "action": "android.intent.action.MAIN",
                "package": "com.android.camera2",
                "component": "com.android.camera2/.CameraActivity",
                "category": "android.intent.category.LAUNCHER",
            },
            "calculator": {
                "action": "android.intent.action.MAIN",
                "package": "com.android.calculator2",
                "component": "com.android.calculator2/.Calculator",
                "category": "android.intent.category.LAUNCHER",
            },
            "settings": {
                "action": "android.intent.action.MAIN",
                "package": "com.android.settings",
                "component": "com.android.settings/.Settings",
                "category": "android.intent.category.LAUNCHER",
            },
            "files": {
                "action": "android.intent.action.MAIN",
                "package": "com.android.documentsui",
                "component": "com.android.documentsui/.files.FilesActivity",
                "category": "android.intent.category.LAUNCHER",
            },
            "clock": {
                "action": "android.intent.action.MAIN",
                "package": "com.android.deskclock",
                "component": "com.android.deskclock/.DeskClock",
                "category": "android.intent.category.LAUNCHER",
            },
            "calendar": {
                "action": "android.intent.action.MAIN",
                "package": "com.android.calendar",
                "component": "com.android.calendar/.AllInOneCalendarActivity",
                "category": "android.intent.category.LAUNCHER",
            },
            "contacts": {
                "action": "android.intent.action.MAIN",
                "package": "com.android.contacts",
                "component": "com.android.contacts/.activities.PeopleActivity",
                "category": "android.intent.category.LAUNCHER",
            },
            "phone": {
                "action": "android.intent.action.MAIN",
                "package": "com.android.dialer",
                "component": "com.android.dialer/.main.impl.MainActivity",
                "category": "android.intent.category.LAUNCHER",
            },
            "dialer": {
                "action": "android.intent.action.MAIN",
                "package": "com.android.dialer",
                "component": "com.android.dialer/.main.impl.MainActivity",
                "category": "android.intent.category.LAUNCHER",
            },
            "play store": {
                "action": "android.intent.action.MAIN",
                "package": "com.android.vending",
                "component": "com.android.vending/.AssetBrowserActivity",
                "category": "android.intent.category.LAUNCHER",
            },

            # ── Maps & Travel ───────────────────────────────────
            "maps": {
                "action": "android.intent.action.MAIN",
                "package": "com.google.android.apps.maps",
                "component": "com.google.android.apps.maps/.MapsActivity",
                "category": "android.intent.category.LAUNCHER",
            },
            "google maps": {
                "action": "android.intent.action.MAIN",
                "package": "com.google.android.apps.maps",
                "component": "com.google.android.apps.maps/.MapsActivity",
                "category": "android.intent.category.LAUNCHER",
            },
            "uber": {
                "action": "android.intent.action.MAIN",
                "package": "com.ubercab",
                "component": "com.ubercab/.client.feature.pickup.PickupActivity",
                "category": "android.intent.category.LAUNCHER",
            },
            "ola": {
                "action": "android.intent.action.MAIN",
                "package": "nc.ola.cabs",
                "component": "nc.ola.cabs/.activities.home.HomeActivity",
                "category": "android.intent.category.LAUNCHER",
            },

            # ── Email ───────────────────────────────────────────
            "gmail": {
                "action": "android.intent.action.MAIN",
                "package": "com.google.android.gm",
                "component": "com.google.android.gm/.ConversationListActivityGmail",
                "category": "android.intent.category.LAUNCHER",
            },

            # ── Music & Video ───────────────────────────────────
            "spotify": {
                "action": "android.intent.action.MAIN",
                "package": "com.spotify.music",
                "component": "com.spotify.music/.MainActivity",
                "category": "android.intent.category.LAUNCHER",
            },
            "netflix": {
                "action": "android.intent.action.MAIN",
                "package": "com.netflix.mediaclient",
                "component": "com.netflix.mediaclient/.ui.webapp.NetflixActivity",
                "category": "android.intent.category.LAUNCHER",
            },
            "prime video": {
                "action": "android.intent.action.MAIN",
                "package": "com.amazon.avod.thirdpartyclient",
                "component": "com.amazon.avod.thirdpartyclient/.app.activity.GenericAndroidLauncher",
                "category": "android.intent.category.LAUNCHER",
            },
            "hotstar": {
                "action": "android.intent.action.MAIN",
                "package": "in.startv.hotstar",
                "component": "in.startv.hotstar/.ui.base.controller.NavigationActivity",
                "category": "android.intent.category.LAUNCHER",
            },

            # ── Shopping ────────────────────────────────────────
            "flipkart": {
                "action": "android.intent.action.MAIN",
                "package": "com.flipkart.android",
                "component": "com.flipkart.android/.activity.HomeActivity",
                "category": "android.intent.category.LAUNCHER",
            },
            "amazon": {
                "action": "android.intent.action.MAIN",
                "package": "com.amazon.amazon",
                "component": "com.amazon.amazon/.app.activity.HomeActivity",
                "category": "android.intent.category.LAUNCHER",
            },
            "swiggy": {
                "action": "android.intent.action.MAIN",
                "package": "in.swiggy.android",
                "component": "in.swiggy.android/.activities.HomeActivity",
                "category": "android.intent.category.LAUNCHER",
            },
            "zomato": {
                "action": "android.intent.action.MAIN",
                "package": "com.application.zomato",
                "component": "com.application.zomato/.common.base.activity.BaseSplashActivity",
                "category": "android.intent.category.LAUNCHER",
            },

            # ── Payments ────────────────────────────────────────
            "google pay": {
                "action": "android.intent.action.MAIN",
                "package": "com.google.android.apps.nbu.paisa.user",
                "component": "com.google.android.apps.nbu.paisa.user/.ui.smartpay.SmartPayActivity",
                "category": "android.intent.category.LAUNCHER",
            },
            "phonepe": {
                "action": "android.intent.action.MAIN",
                "package": "com.phonepe.app",
                "component": "com.phonepe.app/.activities.SplashActivity",
                "category": "android.intent.category.LAUNCHER",
            },
            "paytm": {
                "action": "android.intent.action.MAIN",
                "package": "net.one97.paytm",
                "component": "net.one97.paytm/.AudiBanglaActivity",
                "category": "android.intent.category.LAUNCHER",
            },

            # ── Productivity ────────────────────────────────────
            "drive": {
                "action": "android.intent.action.MAIN",
                "package": "com.google.android.apps.docs",
                "component": "com.google.android.apps.docs/.app.DocumentsActivity",
                "category": "android.intent.category.LAUNCHER",
            },
            "docs": {
                "action": "android.intent.action.MAIN",
                "package": "com.google.android.apps.docs.editors.docs",
                "component": "com.google.android.apps.docs.editors.docs/.app.DocumentsActivity",
                "category": "android.intent.category.LAUNCHER",
            },
            "sheets": {
                "action": "android.intent.action.MAIN",
                "package": "com.google.android.apps.docs.editors.sheets",
                "component": "com.google.android.apps.docs.editors.sheets/.app.DocumentsActivity",
                "category": "android.intent.category.LAUNCHER",
            },
        }

        # ── Alias Map ────────────────────────────────────────────
        self.aliases = {
            "yt": "youtube", "ytb": "youtube", "you tube": "youtube",
            "wa": "whatsapp", "wp": "whatsapp", "what's app": "whatsapp",
            "tg": "telegram", "tele": "telegram",
            "ig": "instagram", "insta": "instagram",
            "fb": "facebook", "face book": "facebook",
            "snap": "snapchat",
            "twit": "twitter", "x": "twitter",
            "maps": "google maps", "google map": "google maps",
            "gmail": "gmail", "mail": "gmail",
            "play": "play store", "playstore": "play store",
            "calc": "calculator", "calci": "calculator",
            "cam": "camera",
            "setting": "settings", "set": "settings",
            "file manager": "files", "file": "files",
            "doc": "docs", "sheet": "sheets",
            "gpay": "google pay", "g pay": "google pay", "gp": "google pay",
            "pp": "phonepe", "phone pe": "phonepe",
            "pt": "paytm",
            "flip": "flipkart",
            "amz": "amazon",
            "prime": "prime video",
            "net": "netflix",
            "star": "hotstar", "hot star": "hotstar",
            "swig": "swiggy",
            "zom": "zomato",
            "uber cab": "uber",
            "ola cab": "ola", "ola cabs": "ola",
        }

    def resolve(self, app_name: str) -> Optional[dict]:
        """Resolve an app name to an Android Intent launch dict.

        Args:
            app_name: Canonical or alias app name (lowercase).

        Returns:
            Intent dict or None.
        """
        name = app_name.lower().strip()

        # Check alias map first
        canonical = self.aliases.get(name)
        if canonical:
            return self.app_map.get(canonical)

        # Direct lookup
        return self.app_map.get(name)

    def fuzzy_match(self, query: str) -> Optional[str]:
        """Find the best matching app name for a partial query."""
        all_names = set(self.app_map.keys()) | set(self.aliases.keys())
        matches = get_close_matches(query.lower(), all_names, n=1, cutoff=0.6)
        if matches:
            best = matches[0]
            if best in self.aliases:
                return self.aliases[best]
            return best
        return None

    def list_apps(self) -> list[str]:
        """Return sorted list of all known app names."""
        return sorted(self.app_map.keys())

    def list_aliases(self) -> dict:
        """Return all aliases."""
        return dict(self.aliases)
