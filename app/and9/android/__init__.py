"""AND9 — Android Execution Layer.

Routes parsed intents to Android device actions through the action registry,
skill registry, and Chrome firewall enforcement.
"""

from .action_registry import (
    get_action,
    is_whitelisted,
    is_chrome_allowed,
    is_chrome_blocked,
    list_registered_actions,
    get_whitelist,
    validate_registry,
)
from .android_executor import execute
from .chrome_firewall import (
    ChromeFirewallError,
    is_chrome_allowed,
    assert_not_chrome,
    check_payload,
    get_allowed_actions,
)
from .skill_registry import (
    register_skill,
    execute_skill,
    get_registered_skills,
)
from .validate_handlers import (
    validate_android_handlers,
    get_coverage_report,
)

__all__ = [
    "get_action",
    "is_whitelisted",
    "is_chrome_allowed",
    "is_chrome_blocked",
    "list_registered_actions",
    "get_whitelist",
    "validate_registry",
    "execute",
    "ChromeFirewallError",
    "assert_not_chrome",
    "check_payload",
    "register_skill",
    "execute_skill",
    "get_registered_skills",
    "validate_android_handlers",
    "get_coverage_report",
]
