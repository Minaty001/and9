"""
AND9 — Chrome Fallback Firewall (Phase 14).

Enforces the AND9 Final Rule:
    "Search is last priority. Device actions always win.
     Chrome may ONLY be opened for: SEARCH, NEWS, WEB_LOOKUP."

Usage:
    from app.skills.android.chrome_firewall import assert_not_chrome

    # In android_executor.py, before dispatching any payload:
    assert_not_chrome(action_type, payload)

Any action trying to route to Chrome that is NOT search/news/web_lookup
will raise ChromeFirewallError and be logged as a security violation.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ChromeFirewallError(ValueError):
    """Raised when a non-search action attempts to open Chrome."""
    pass


# ── Chrome-allowed actions ────────────────────────────────────────
# ONLY these action types may open Chrome/browser.
# All other device actions are blocked from opening Chrome.
CHROME_ALLOWED_ACTIONS = frozenset({
    "search",
    "news",
    "web_lookup",
    "open_app",
})

# Chrome package identifiers to detect in payloads
_CHROME_PACKAGES = frozenset({
    "com.android.chrome",
    "com.chrome",
    "com.chrome.beta",
    "com.chrome.dev",
    "com.chrome.canary",
    "org.mozilla.firefox",
    "com.microsoft.emmx",  # Edge
    "com.opera.browser",
})

# Chrome URL patterns that indicate browser routing
_CHROME_URL_PREFIXES = (
    "https://www.google.com/search",
    "https://google.com/search",
    "http://www.google.com/search",
)


def is_chrome_allowed(action_type: str) -> bool:
    """Check if an action type is permitted to open Chrome.

    Args:
        action_type: AND9 action type string (e.g., "call", "search").

    Returns:
        True only for search/news/web_lookup.

    Examples:
        >>> is_chrome_allowed("search")
        True
        >>> is_chrome_allowed("call")
        False
        >>> is_chrome_allowed("set_alarm")
        False
    """
    return action_type.lower() in CHROME_ALLOWED_ACTIONS


def assert_not_chrome(action_type: str, payload: Optional[dict] = None) -> None:
    """Assert that a non-search action is not routing to Chrome.

    Checks both the action_type and the payload's package/data fields.
    Raises ChromeFirewallError if a violation is detected.

    Args:
        action_type: AND9 action type being executed.
        payload:     Android intent payload dict (checked for Chrome package/URL).

    Raises:
        ChromeFirewallError: If Chrome routing is detected for a blocked action.

    Examples:
        >>> assert_not_chrome("search", {"package": "com.android.chrome"})
        # No error — search is allowed

        >>> assert_not_chrome("set_alarm", {"package": "com.android.chrome"})
        # Raises ChromeFirewallError!

        >>> assert_not_chrome("youtube_search", {"package": "com.android.chrome"})
        # Raises ChromeFirewallError!
    """
    if is_chrome_allowed(action_type):
        return  # Allowed — no check needed

    if payload is None:
        return

    # Check package field
    pkg = payload.get("package", "").lower()
    if pkg in _CHROME_PACKAGES:
        msg = (
            f"🚫 Chrome Firewall BLOCKED: action '{action_type}' "
            f"attempted to open Chrome (package: {pkg}). "
            f"Only SEARCH/NEWS/WEB_LOOKUP may use Chrome."
        )
        logger.error(msg)
        raise ChromeFirewallError(msg)

    # Check data/URL field for Google search URLs
    data = payload.get("data", "")
    if isinstance(data, str):
        for prefix in _CHROME_URL_PREFIXES:
            if data.startswith(prefix):
                msg = (
                    f"🚫 Chrome Firewall BLOCKED: action '{action_type}' "
                    f"attempted to open Google search URL: {data[:80]}. "
                    f"Only SEARCH/NEWS/WEB_LOOKUP may use web search."
                )
                logger.error(msg)
                raise ChromeFirewallError(msg)


def check_payload(action_type: str, payload: dict) -> dict:
    """Non-raising version of assert_not_chrome.

    Returns the payload unchanged if allowed, or a blocked payload
    with an error response if Chrome is detected.

    Args:
        action_type: AND9 action type.
        payload:     Android intent payload.

    Returns:
        Original payload if OK, or error payload if blocked.
    """
    try:
        assert_not_chrome(action_type, payload)
        return payload
    except ChromeFirewallError as e:
        logger.error("Chrome firewall triggered: %s", e)
        return {
            "blocked": True,
            "reason": str(e),
            "action": action_type,
        }


def get_allowed_actions() -> frozenset:
    """Return the frozenset of actions that may open Chrome."""
    return CHROME_ALLOWED_ACTIONS
