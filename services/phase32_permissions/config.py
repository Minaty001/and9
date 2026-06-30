"""
Phase 32 — Permission Manager Configuration.
"""

from pydantic import Field
from services.base.config_base import BaseConfig


class PermissionConfig(BaseConfig):
    """Configuration for the permission manager."""

    service_name: str = Field(default="jarvis_permissions", description="Permission service name")
    default_role: str = Field(default="user", description="Default role for new users")
    enable_scoped_permissions: bool = Field(default=True, description="Enable resource scoping")
    max_roles_per_user: int = Field(default=5, ge=1, le=100, description="Max roles per user")
    enable_audit: bool = Field(default=True, description="Enable audit logging")
    cache_ttl_seconds: int = Field(default=60, ge=1, le=3600, description="Cache TTL in seconds")
    enable_owner_override: bool = Field(default=True, description="Owner can override permissions")

    model_config = {"env_prefix": "JARVIS_PHASE32_"}
