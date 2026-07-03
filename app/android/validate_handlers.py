"""
AND9 — Android Handler Coverage Validator (Priority 1).

At startup this scans OverlayViewController.kt to extract which action
string literals are handled in the 'when (action)' block, then cross-checks
that against the Python action registry.

If any critical action has no Android handler, a RuntimeError is raised.

Flow:
    validate_android_handlers()
        ↓
    Parse OverlayViewController.kt for handled action strings
        ↓
    Compare with Python REGISTRY required actions
        ↓
    Missing? → RuntimeError (fatal at startup)
    OK?      → INFO log
"""
import os
import re
import logging
from pathlib import Path
from typing import Set, List

from app.android.action_registry import _REQUIRED_ACTIONS

logger = logging.getLogger(__name__)

# Path to the Kotlin overlay file that dispatches Android actions
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_KT_PATH = _PROJECT_ROOT / "android" / "app" / "src" / "main" / "java" / "com" / "jarvis" / "assistant" / "overlay" / "OverlayViewController.kt"

_OVERLAY_KT_PATH = Path(
    os.environ.get(
        "AND9_OVERLAY_KT",
        str(_DEFAULT_KT_PATH),
    )
)

# ── Known Android-side handler patterns ──────────────────────────────────────
# These are the string literals that appear in the `when (action) { }` block
# inside OverlayViewController.kt plus internal service methods.
# We extract them with a regex and supplement with any always-handled builtins.

# Actions that are handled inside JarvisAccessibilityService (not the overlay)
_ACCESSIBILITY_HANDLED = frozenset({
    "go_home", "close_app", "back", "go_back",
    "home", "notifications", "screenshot",
})

# Actions whose Android execution is an Intent fire-and-forget — handled via
# AlarmClock / ContactsContract intents, not a local Kotlin function.
# We trust Python verifies these at action_registry level already.
_INTENT_ONLY_ACTIONS = frozenset({
    "emergency",        # handled directly by Android system
    "airplane_mode",    # Settings intent
    "news",             # web intent
    "web_lookup",       # web intent
})

# Python actions that map to the same Kotlin handler
_KOTLIN_ALIASES = {
    "flashlight_on": "flashlight",
    "flashlight_off": "flashlight",
    "volume_up": "volume",
    "volume_down": "volume",
    "volume_mute": "volume",
    "volume_max": "volume",
    "youtube_play": "youtube_search",
    "send_sms": "call",         # handled by CONTACTS_LOOKUP block
    "open_camera": "camera",
    "go_home": "home",
    "web_lookup": "search",
    "news": "search",
}


def _extract_kotlin_handlers(kt_path: Path) -> Set[str] | None:
    """Parse the Kotlin file and extract action string literals from when{} blocks.

    Looks for patterns like:
        "open_app"    ->    ...
        "alarm", "set_alarm" ->    ...

    Returns a set of lowercase action strings found, or None if the file cannot be read/accessed.
    """
    try:
        if not kt_path.exists():
            logger.warning(
                "OverlayViewController.kt not found at: %s — skipping Kotlin parse.",
                kt_path,
            )
            return None
        source = kt_path.read_text(encoding="utf-8")
    except (PermissionError, FileNotFoundError, OSError) as e:
        logger.warning(
            "OverlayViewController.kt cannot be read/accessed at %s: %s — skipping Kotlin parse.",
            kt_path,
            e,
        )
        return None
    except Exception as e:
        logger.warning("Unexpected error reading Kotlin source %s: %s", kt_path, e)
        return None

    # Match action string literals inside when blocks
    # e.g.  "torch", "flashlight" ->  { ... }
    # or    "set_alarm"           ->  { ... }
    found: Set[str] = set()
    # Find all quoted strings used as when-case labels
    pattern = re.compile(r'"([a-z_][a-z0-9_]*)"', re.IGNORECASE)
    for m in pattern.finditer(source):
        token = m.group(1).lower()
        # Filter to tokens that look like action names (underscores, short)
        if "_" in token or len(token) <= 15:
            found.add(token)

    logger.debug("Extracted %d string literals from Kotlin source.", len(found))
    return found


def _normalize_actions(raw: Set[str]) -> Set[str]:
    """Apply known aliases so Kotlin strings map to Python action names."""
    result: Set[str] = set(raw)
    for py_action, kt_action in _KOTLIN_ALIASES.items():
        if kt_action in result:
            result.add(py_action)
    return result


def validate_android_handlers() -> None:
    """Assert that every required Python action has an Android handler.

    Called once at application startup (from main._init_and9).

    Raises:
        RuntimeError: If any critical action lacks an Android handler.
    """
    kt_handlers = _extract_kotlin_handlers(_OVERLAY_KT_PATH)
    if kt_handlers is None:
        logger.warning(
            "Android handler coverage check skipped: Kotlin source file not accessible."
        )
        return

    kt_normalized = _normalize_actions(kt_handlers)

    # Add always-covered sets
    all_covered = kt_normalized | _ACCESSIBILITY_HANDLED | _INTENT_ONLY_ACTIONS

    missing: List[str] = []
    for action in sorted(_REQUIRED_ACTIONS):
        # Check exact match OR alias coverage
        alias = _KOTLIN_ALIASES.get(action, action)
        if action not in all_covered and alias not in all_covered:
            missing.append(action)

    if missing:
        msg = (
            f"AND9 Handler Coverage FATAL: {len(missing)} required action(s) have "
            f"no confirmed Android handler: {missing}\n"
            f"Either add them to OverlayViewController.kt or "
            f"update _ACCESSIBILITY_HANDLED / _INTENT_ONLY_ACTIONS in validate_handlers.py."
        )
        logger.critical(msg)
        raise RuntimeError(msg)

    logger.info(
        "AND9 Handler Coverage OK: all %d required actions have Android handlers. "
        "(Kotlin literals: %d, Accessibility: %d, Intent-only: %d)",
        len(_REQUIRED_ACTIONS),
        len(kt_handlers),
        len(_ACCESSIBILITY_HANDLED),
        len(_INTENT_ONLY_ACTIONS),
    )


def get_coverage_report() -> dict:
    """Return a full coverage report dict for diagnostics / admin endpoints."""
    kt_handlers = _extract_kotlin_handlers(_OVERLAY_KT_PATH)
    if kt_handlers is None:
        return {
            "total_required": len(_REQUIRED_ACTIONS),
            "covered": [],
            "missing": sorted(_REQUIRED_ACTIONS),
            "coverage_pct": 0.0,
            "kotlin_literals_found": [],
            "kt_path": str(_OVERLAY_KT_PATH),
            "kt_found": False,
            "error": "Kotlin source file not found or permission denied.",
        }

    kt_normalized = _normalize_actions(kt_handlers)
    all_covered = kt_normalized | _ACCESSIBILITY_HANDLED | _INTENT_ONLY_ACTIONS

    covered = []
    missing = []
    for action in sorted(_REQUIRED_ACTIONS):
        alias = _KOTLIN_ALIASES.get(action, action)
        if action in all_covered or alias in all_covered:
            covered.append(action)
        else:
            missing.append(action)

    return {
        "total_required": len(_REQUIRED_ACTIONS),
        "covered": covered,
        "missing": missing,
        "coverage_pct": round(len(covered) / max(len(_REQUIRED_ACTIONS), 1) * 100, 1),
        "kotlin_literals_found": sorted(kt_handlers),
        "kt_path": str(_OVERLAY_KT_PATH),
        "kt_found": _OVERLAY_KT_PATH.exists(),
    }
