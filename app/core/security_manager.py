"""
app/core/security_manager.py — Security layer for AND9

All actions pass through security before execution.

Risk levels:
  SAFE      -> execute immediately
  LOW       -> execute + notify
  MEDIUM    -> single confirmation required
  HIGH      -> typed confirmation required
  BLOCKED   -> reject with reason

Sensitive intents that require confirmation:
  delete_file, send_sms, make_call (to unknown contacts)
  send_email, modify_settings, access_private_data
  purchase_action, clear_all_data
"""

import logging
import re
from enum import Enum
from typing import Tuple

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    SAFE    = 0
    LOW     = 1
    MEDIUM  = 2
    HIGH    = 3
    BLOCKED = 4


# Actions and their risk levels
RISK_MAP = {
    "delete_file":       RiskLevel.HIGH,
    "clear_all_data":    RiskLevel.HIGH,
    "send_sms":          RiskLevel.MEDIUM,
    "make_call":         RiskLevel.MEDIUM,
    "send_email":        RiskLevel.MEDIUM,
    "modify_settings":   RiskLevel.MEDIUM,
    "purchase_action":   RiskLevel.HIGH,
    "access_contacts":   RiskLevel.LOW,
    "access_location":   RiskLevel.LOW,
    "take_screenshot":   RiskLevel.LOW,
    "open_app":          RiskLevel.SAFE,
    "play_music":        RiskLevel.SAFE,
    "set_alarm":         RiskLevel.SAFE,
    "set_timer":         RiskLevel.SAFE,
    "volume_up":         RiskLevel.SAFE,
    "volume_down":       RiskLevel.SAFE,
    "wifi_on":           RiskLevel.SAFE,
    "wifi_off":          RiskLevel.SAFE,
}


class SecurityManager:
    def assess(self, intent: str, entities: dict) -> Tuple[RiskLevel, str]:
        """
        Returns (risk_level, reason_string).
        Caller decides whether to execute or prompt for confirmation.
        """
        # 1. Validate input
        if not intent or not isinstance(intent, str):
            return RiskLevel.BLOCKED, "Invalid intent."

        # 2. Sanitize entities
        for key, val in (entities or {}).items():
            if isinstance(val, str) and self._looks_dangerous(val):
                return RiskLevel.BLOCKED, f"Dangerous value in '{key}'."

        # 3. Look up risk map
        risk = RISK_MAP.get(intent, RiskLevel.LOW)
        reason = self._build_reason(intent, risk)
        return risk, reason

    def _looks_dangerous(self, value: str) -> bool:
        """Detect potential injection or traversal attempts."""
        patterns = [r"\.\.\/", r";\s*rm\s", r"<script", r"DROP TABLE",
                    r"eval\(", r"exec\("]
        return any(re.search(p, value, re.IGNORECASE) for p in patterns)

    def _build_reason(self, intent: str, risk: RiskLevel) -> str:
        reasons = {
            RiskLevel.SAFE:    "Safe to execute.",
            RiskLevel.LOW:     f"'{intent}' accesses personal data.",
            RiskLevel.MEDIUM:  f"'{intent}' requires your confirmation.",
            RiskLevel.HIGH:    f"'{intent}' is a high-risk action. Type CONFIRM to proceed.",
            RiskLevel.BLOCKED: f"'{intent}' is not allowed.",
        }
        return reasons.get(risk, "Unknown risk.")

    def audit_log(self, intent: str, entities: dict,
                  risk: RiskLevel, executed: bool) -> None:
        """Write every action to the audit trail."""
        logger.info(
            f"AUDIT | intent={intent} | risk={risk.name} | "
            f"executed={executed} | entities_keys={list((entities or {}).keys())}"
        )