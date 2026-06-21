"""
AND9 — Dynamic Package Resolver (Phase 4 Rebuild).

Resolves app names to Android Intent launch parameters.

Resolution order:
    1. Dynamic cache  — installed_apps.json (written by Android at startup)
    2. Alias map      — short codes (yt, wa, insta, etc.)
    3. Static app_map — known fallback packages
    4. Fuzzy match    — for typos / partial names
    5. None           — inform user, NEVER open Chrome as fallback

Android side:
    PackageManager.queryIntentActivities() writes installed_apps.json on startup.
    Format: {"com.google.android.youtube": "YouTube", ...}
"""
import json
import logging
import os
from difflib import get_close_matches
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

# Path where Android writes the installed apps cache
_INSTALLED_APPS_PATH = os.environ.get(
    "AND9_INSTALLED_APPS_PATH",
    "/app/.jarvis_data/installed_apps.json"
)


class PackageResolver:
    """Resolve app names to Android Intent launch parameters.

    Attributes:
        app_map:  Static dict of known apps → Intent params.
        aliases:  Short names / alternate spellings → canonical name.
        _dynamic: Dict of package_name → label from installed_apps.json.
    """

    def __init__(self):
        # ── Static App Map (fallback / bootstrap) ────────────────
        self.app_map: Dict[str, dict] = {
            # Social & Communication
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
            # Browsers
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
            # System
            "camera": {
                "action": "android.media.action.STILL_IMAGE_CAMERA",
                "package": "com.android.camera2",
                "category": "android.intent.category.DEFAULT",
            },
            "gallery": {
                "action": "android.intent.action.MAIN",
                "package": "com.google.android.apps.photos",
                "component": "com.google.android.apps.photos/.home.HomeActivity",
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
            # Maps & Travel
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
            # Email
            "gmail": {
                "action": "android.intent.action.MAIN",
                "package": "com.google.android.gm",
                "component": "com.google.android.gm/.ConversationListActivityGmail",
                "category": "android.intent.category.LAUNCHER",
            },
            # Music & Video
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
            # Shopping
            "flipkart": {
                "action": "android.intent.action.MAIN",
                "package": "com.flipkart.android",
                "component": "com.flipkart.android/.activity.HomeActivity",
                "category": "android.intent.category.LAUNCHER",
            },
            "amazon": {
                "action": "android.intent.action.MAIN",
                "package": "com.amazon.mShop.android.shopping",
                "component": "com.amazon.mShop.android.shopping/.HomeActivity",
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
            # Payments
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
            # Productivity
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
        self.aliases: Dict[str, str] = {
            # YouTube
            "yt": "youtube", "ytb": "youtube", "you tube": "youtube",
            "youtube app": "youtube",
            # WhatsApp
            "wa": "whatsapp", "wp": "whatsapp", "what's app": "whatsapp",
            "whatsapp app": "whatsapp",
            # Telegram
            "tg": "telegram", "tele": "telegram",
            # Instagram
            "ig": "instagram", "insta": "instagram",
            # Facebook
            "fb": "facebook", "face book": "facebook",
            # Snapchat
            "snap": "snapchat",
            # Twitter/X
            "twit": "twitter", "x": "twitter",
            # Maps
            "maps": "google maps", "google map": "google maps",
            # Gmail
            "mail": "gmail",
            # Play Store
            "play": "play store", "playstore": "play store",
            "play store app": "play store",
            # Calculator
            "calc": "calculator", "calci": "calculator",
            # Camera
            "cam": "camera",
            # Settings
            "setting": "settings", "set": "settings",
            # Files
            "file manager": "files", "file": "files",
            # Docs/Sheets
            "doc": "docs", "sheet": "sheets",
            # Google Pay
            "gpay": "google pay", "g pay": "google pay", "gp": "google pay",
            # PhonePe
            "pp": "phonepe", "phone pe": "phonepe",
            # Paytm
            "pt": "paytm",
            # Flipkart
            "flip": "flipkart",
            # Amazon
            "amz": "amazon",
            # Prime Video
            "prime": "prime video",
            # Netflix
            "net": "netflix",
            # Hotstar
            "star": "hotstar", "hot star": "hotstar",
            # Food
            "swig": "swiggy", "zom": "zomato",
            # Ride
            "uber cab": "uber", "ola cab": "ola", "ola cabs": "ola",
        }

        # ── Dynamic cache (loaded from installed_apps.json) ───────
        self._dynamic: Dict[str, str] = {}  # package → label
        self._dynamic_by_label: Dict[str, str] = {}  # label_lower → package
        self.load_dynamic_cache()

    # ── Dynamic Cache ─────────────────────────────────────────────

    def load_dynamic_cache(self) -> bool:
        """Load installed_apps.json written by Android PackageManager.

        Called at startup. Safe to call multiple times (refreshes cache).

        Returns:
            True if cache loaded successfully, False otherwise.
        """
        try:
            if os.path.exists(_INSTALLED_APPS_PATH):
                with open(_INSTALLED_APPS_PATH, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self._dynamic = data
                self._dynamic_by_label = {
                    label.lower(): pkg
                    for pkg, label in data.items()
                }
                logger.info("Loaded %d installed apps from cache.", len(data))
                return True
        except Exception as e:
            logger.warning("Failed to load installed_apps.json: %s", e)
        return False

    def update_dynamic_cache(self, apps: Dict[str, str]) -> None:
        """Update dynamic cache from Android client and save to disk."""
        try:
            self._dynamic = apps
            self._dynamic_by_label = {
                label.lower(): pkg
                for pkg, label in apps.items()
            }
            os.makedirs(os.path.dirname(_INSTALLED_APPS_PATH), exist_ok=True)
            with open(_INSTALLED_APPS_PATH, 'w', encoding='utf-8') as f:
                json.dump(apps, f, ensure_ascii=False)
            logger.info("Saved %d installed apps to cache.", len(apps))
        except Exception as e:
            logger.error("Failed to save installed apps cache: %s", e)

    # ── Resolution ───────────────────────────────────────────────

    def resolve(self, app_name: str) -> Optional[dict]:
        """Resolve an app name to Android Intent launch parameters.

        Resolution order:
            1. Dynamic cache (installed_apps.json label match)
            2. Alias map
            3. Static app_map (exact)
            4. Fuzzy match
            5. None (caller must inform user — never Chrome fallback)

        Args:
            app_name: App name as spoken by user (any case).

        Returns:
            Intent dict or None if not found.
        """
        name = app_name.lower().strip()
        if not name:
            return None

        # 1. Dynamic cache — label match
        pkg = self._dynamic_by_label.get(name)
        if pkg:
            return self._build_dynamic_intent(pkg, self._dynamic[pkg])

        # 2. Alias map
        canonical = self.aliases.get(name)
        if canonical:
            intent = self.app_map.get(canonical)
            if intent:
                return intent
            # Check dynamic too
            pkg = self._dynamic_by_label.get(canonical)
            if pkg:
                return self._build_dynamic_intent(pkg, self._dynamic[pkg])

        # 3. Static app_map exact match
        intent = self.app_map.get(name)
        if intent:
            return intent

        # 4. Fuzzy match
        fuzzy_name = self.fuzzy_match(name)
        if fuzzy_name:
            return self.app_map.get(fuzzy_name) or self._resolve_dynamic_fuzzy(fuzzy_name)

        # 5. Not found — caller must handle (never Chrome)
        logger.info("App not resolved: '%s'", app_name)
        return None

    def fuzzy_match(self, query: str) -> Optional[str]:
        """Find the best matching canonical app name for a partial query.

        Args:
            query: Partial or misspelled app name.

        Returns:
            Canonical app name string, or None.
        """
        all_names = (
            set(self.app_map.keys())
            | set(self.aliases.keys())
            | set(self._dynamic_by_label.keys())
        )
        matches = get_close_matches(query.lower(), all_names, n=1, cutoff=0.6)
        if matches:
            best = matches[0]
            return self.aliases.get(best, best)
        return None

    def _build_dynamic_intent(self, package: str, label: str) -> dict:
        """Build a launcher intent for a dynamically discovered app."""
        return {
            "action": "android.intent.action.MAIN",
            "package": package,
            "label": label,
            "category": "android.intent.category.LAUNCHER",
            "dynamic": True,
        }

    def _resolve_dynamic_fuzzy(self, name: str) -> Optional[dict]:
        """Try to find a dynamic app by fuzzy label match."""
        matches = get_close_matches(name, self._dynamic_by_label.keys(), n=1, cutoff=0.6)
        if matches:
            pkg = self._dynamic_by_label[matches[0]]
            label = self._dynamic.get(pkg, matches[0])
            return self._build_dynamic_intent(pkg, label)
        return None

    def list_apps(self) -> List[str]:
        """Return sorted list of all known app names (static + dynamic)."""
        dynamic_labels = list(self._dynamic_by_label.keys())
        return sorted(set(self.app_map.keys()) | set(dynamic_labels))

    def list_aliases(self) -> Dict[str, str]:
        """Return all aliases."""
        return dict(self.aliases)

_resolver_instance = None

def get_resolver() -> PackageResolver:
    """Get the singleton PackageResolver instance."""
    global _resolver_instance
    if _resolver_instance is None:
        _resolver_instance = PackageResolver()
    return _resolver_instance
