"""
Phase 38 — Configuration System
================================

Centralized config management. Load/save from multiple sources (env, file,
memory). Overrides, profiles, validation.

Components:
    - ConfigStore: Key-value config storage with profile support
    - ProfileManager: Create, delete, rename, activate profiles
    - ConfigValidator: Type checking, range, regex, allowed values
    - ConfigService: ServiceBase wrapper
"""

from .config import ConfigSystemConfig
from .models import ConfigEntry, ConfigSource, ValidationError
from .config_store import ConfigStore
from .profile_manager import ProfileManager
from .validator import ConfigValidator
from .hot_reload import HotReloadManager
from .service import ConfigService

__all__ = [
    "ConfigSystemConfig",
    "ConfigEntry",
    "ConfigSource",
    "ValidationError",
    "ConfigStore",
    "ProfileManager",
    "ConfigValidator",
    "HotReloadManager",
    "ConfigService",
]
