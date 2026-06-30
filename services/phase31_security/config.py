"""
Phase 31 — Security Layer Configuration.
"""

from pydantic import Field
from services.base.config_base import BaseConfig


class SecurityConfig(BaseConfig):
    """Configuration for the security layer."""

    service_name: str = Field(default="jarvis_security", description="Security service name")
    enable_input_validation: bool = Field(default=True, description="Enable input validation")
    enable_sanitization: bool = Field(default=True, description="Enable input sanitization")
    enable_authentication: bool = Field(default=True, description="Enable authentication")
    enable_encryption: bool = Field(default=True, description="Enable encryption")
    enable_audit_logging: bool = Field(default=True, description="Enable audit logging")
    max_input_length: int = Field(default=4096, ge=1, le=65536, description="Max input length")
    blocked_chars: list = Field(default_factory=lambda: ["<", ">", "&", "'", '"', ";", "|", "`", "$", "(", ")", "{", "}", "\\", "\x00"], description="Blocked dangerous characters")
    allowed_domains: list = Field(default_factory=lambda: ["localhost", "jarvis.local"], description="Allowed domains")
    encryption_algorithm: str = Field(default="AES-256-GCM", description="Encryption algorithm")
    audit_log_retention_days: int = Field(default=90, ge=1, le=365, description="Audit log retention in days")
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    max_requests_per_minute: int = Field(default=120, ge=1, le=10000, description="Max requests per minute")

    model_config = {"env_prefix": "JARVIS_PHASE31_"}
