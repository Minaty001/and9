"""
Phase 31 — Security Layer
===========================

Input validation, sanitization, authentication, encryption,
SQL injection/XSS prevention, audit logging, rate limiting,
access control, secret management, and prompt injection detection.

Components:
    - InputValidator: Validate input against dangerous patterns
    - InputSanitizer: Sanitize input by stripping dangerous chars
    - AuthManager: Token-based authentication and authorization
    - EncryptionManager: AES-256-GCM symmetric encryption
    - AuditLogger: Structured audit event logging and querying
    - SecretManager: In-memory secret storage with encryption at rest
    - AccessController: Token-based tool/operation access control
    - SecurityService: ServiceBase wrapper with all capabilities
"""

from .config import SecurityConfig
from .models import SecurityEvent, ValidationResult
from .validator import InputValidator
from .sanitizer import InputSanitizer
from .auth import AuthManager
from .encryption import EncryptionManager
from .audit import AuditLogger
from .secret_manager import SecretManager, SecretEntry
from .access_controller import AccessController
from .service import SecurityService, TokenBucket

__all__ = [
    "SecurityConfig",
    "SecurityEvent",
    "ValidationResult",
    "InputValidator",
    "InputSanitizer",
    "AuthManager",
    "EncryptionManager",
    "AuditLogger",
    "SecretManager",
    "SecretEntry",
    "AccessController",
    "TokenBucket",
    "SecurityService",
]
