"""
AND9 — Self-Healing Diagnostics (Priority 9).

Automatically invoked when an intent fails in the orchestrator pipeline.
Checks system health, validates Android handlers, and attempts to find the root cause
(e.g., missing permissions, unhandled actions, database lock).
"""
import logging
import os
import sqlite3
from typing import Dict, Any

from app.android.validate_handlers import get_coverage_report

logger = logging.getLogger(__name__)

# Paths for checking permissions/locks
_DB_PATH = os.environ.get(
    "AND9_REMINDERS_STORAGE_DB",
    "/app/.jarvis_data/reminders_engine.db"
)


def run_diagnostics(error: Exception, intent_name: str, action_type: str, params: dict) -> Dict[str, Any]:
    """Run system diagnostics to identify the cause of a pipeline error.

    Args:
        error: The caught exception.
        intent_name: The detected intent.
        action_type: The action attempting to run.
        params: The extracted parameters.

    Returns:
        Dict containing diagnostic report.
    """
    report = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "intent_state": {
            "intent": intent_name,
            "action": action_type,
            "params_keys": list(params.keys()) if params else [],
        },
        "system_health": {
            "db_accessible": False,
            "handler_coverage_ok": False,
        },
        "recommendation": "Check backend logs for stack trace.",
    }

    # 1. Check SQLite DB locks
    try:
        with sqlite3.connect(_DB_PATH, timeout=1.0) as con:
            con.execute("SELECT 1").fetchone()
            report["system_health"]["db_accessible"] = True
    except Exception as db_err:
        report["system_health"]["db_accessible"] = False
        report["recommendation"] = f"SQLite Database locked or inaccessible: {db_err}"

    # 2. Check Android Handler Coverage
    try:
        coverage = get_coverage_report()
        missing = coverage.get("missing", [])
        if not missing:
            report["system_health"]["handler_coverage_ok"] = True
        else:
            report["system_health"]["handler_coverage_ok"] = False
            if action_type and action_type.lower() in missing:
                report["recommendation"] = f"Action '{action_type}' has no handler in Android OverlayViewController.kt."
    except Exception as cov_err:
        logger.warning("Diagnostics failed to get coverage report: %s", cov_err)

    # 3. Analyze specific exceptions
    if isinstance(error, KeyError):
        report["recommendation"] = f"Missing expected dictionary key in intent resolution: {error}"
    elif isinstance(error, ValueError):
        report["recommendation"] = "Value extraction failed. Regex might have returned unexpected format."
    elif isinstance(error, sqlite3.OperationalError):
        report["recommendation"] = "SQLite Operational Error (disk full or permissions issue)."

    logger.error("Diagnostic Report Generated for %s: %s", type(error).__name__, report)
    return report
