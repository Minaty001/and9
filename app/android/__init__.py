"""
app/android — Android device integration layer.

Single entry point for all Android action execution, action registry,
skill registry (dynamic handler routing), Chrome firewall, contacts
resolution, package resolution, and handler validation.
"""

# Executor
from app.android.executor import execute

# Action Registry
from app.android.action_registry import (
    REGISTRY, get_action, is_whitelisted, is_chrome_allowed,
    is_chrome_blocked, list_registered_actions, get_whitelist,
    validate_registry,
)

# Skill Registry
from app.android.skill_registry import (
    execute_skill, register_skill, get_registered_skills,
)

# Chrome Firewall
from app.android.chrome_firewall import (
    ChromeFirewallError, is_chrome_allowed as firewall_is_chrome_allowed,
    assert_not_chrome, check_payload, get_allowed_actions,
)

# Package Resolver
from app.android.apps.package_resolver import PackageResolver, get_resolver

# Contacts Resolver
from app.android.contacts.resolver import ContactsResolver

# Handler Validation
from app.android.validate_handlers import (
    validate_android_handlers, get_coverage_report,
)

__all__ = [
    "execute",
    "REGISTRY", "get_action", "is_whitelisted",
    "is_chrome_allowed", "is_chrome_blocked",
    "list_registered_actions", "get_whitelist", "validate_registry",
    "execute_skill", "register_skill", "get_registered_skills",
    "ChromeFirewallError", "assert_not_chrome", "check_payload", "get_allowed_actions",
    "PackageResolver", "get_resolver",
    "ContactsResolver",
    "validate_android_handlers", "get_coverage_report",
]
