"""
AND9 — App Launch Actions (Phase 6 of Refactor).

Launches Android apps via dynamic package resolution.
Uses PackageResolver which merges IntentExecutor.APP_MAP
with ReflexAppResolver aliases for comprehensive coverage.

Never hardcodes app names — always resolves through the
package resolver layer.
"""
import logging

from app.android.apps.package_resolver import get_resolver

logger = logging.getLogger(__name__)

# Single source of truth for app resolution
_package_resolver = get_resolver()


def execute_open_app(app_name: str) -> dict:
    """Open an Android app by name.

    Resolves the app name through PackageResolver and returns
    the appropriate Android Intent payload.

    Args:
        app_name: App name or alias (e.g., "youtube", "yt", "whatsapp").

    Returns:
        Dict with response, action, payload.
    """
    if not app_name or not app_name.strip():
        return {
            "response": "Kaun si app kholni hai? Naam batao! 📱",
            "action": "UNKNOWN_APP",
            "payload": {},
        }

    resolved = _package_resolver.resolve(app_name)
    if resolved:
        return {
            "response": f"{app_name.title()} khol raha hoon... 📱",
            "action": "LAUNCH_APP",
            "payload": resolved,
            "metadata": {"app_name": app_name},
        }

    # Try fuzzy match
    fuzzy = _package_resolver.fuzzy_match(app_name)
    if fuzzy:
        resolved = _package_resolver.resolve(fuzzy)
        if resolved:
            return {
                "response": f"Kya aap '{fuzzy.title()}' kholna chahte ho? 🎯",
                "action": "LAUNCH_APP",
                "payload": resolved,
                "metadata": {"app_name": fuzzy, "fuzzy": True},
            }

    return {
        "response": f"App nahi mila '{app_name}'. Kripya sahi naam boliye! 😕",
        "action": "UNKNOWN_APP",
        "payload": {},
        "metadata": {"app_name": app_name},
    }


def execute_close_app() -> dict:
    """Send close/go-back command to Android client."""
    return {
        "response": "App band kar raha hoon... 🔙",
        "action": "CLOSE_APP",
        "payload": {},
    }
