"""
Phase 31 — Security Service.

ServiceBase wrapper for the Security Layer.
Includes rate limiting, access control, and secret management.
"""

from __future__ import annotations

import time
import logging
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

from services.base.service_base import ServiceBase
from .config import SecurityConfig
from .models import SecurityEvent, ValidationResult
from .validator import InputValidator
from .sanitizer import InputSanitizer
from .auth import AuthManager
from .encryption import EncryptionManager
from .audit import AuditLogger
from .secret_manager import SecretManager
from .access_controller import AccessController

logger = logging.getLogger(__name__)


class TokenBucket:
    """Token bucket rate limiter.

    A simple thread-safe token bucket implementation for rate limiting.
    Tokens are refilled at a constant rate over time.

    Usage:
        bucket = TokenBucket(capacity=120, refill_rate=2.0)  # 120 tokens, 2/sec refill
        if bucket.consume():
            print("Request allowed")
    """

    def __init__(self, capacity: float, refill_rate: float):
        """Initialize token bucket.

        Args:
            capacity: Maximum number of tokens the bucket can hold.
            refill_rate: Tokens added per second.
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self._tokens = float(capacity)
        self._last_refill = time.monotonic()
        self._lock = Lock()

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self.capacity, self._tokens + elapsed * self.refill_rate)
        self._last_refill = now

    def consume(self, tokens: float = 1.0) -> bool:
        """Try to consume tokens from the bucket.

        Args:
            tokens: Number of tokens to consume (default 1.0).

        Returns:
            True if tokens were consumed, False if bucket is empty.
        """
        with self._lock:
            self._refill()
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False

    @property
    def available_tokens(self) -> float:
        """Get the current number of available tokens."""
        with self._lock:
            self._refill()
            return self._tokens

    def reset(self) -> None:
        """Reset the bucket to full capacity."""
        with self._lock:
            self._tokens = float(self.capacity)
            self._last_refill = time.monotonic()


class SecurityService(ServiceBase):
    """Security service for input validation, sanitization, authentication,
    encryption, audit logging, rate limiting, access control, and secret management.

    Usage:
        svc = SecurityService()
        await svc.initialize()
        result = await svc.validate("user input")
        clean = await svc.sanitize("user input")
        token = await svc.authenticate_user("user123")
        cipher, iv = await svc.encrypt("secret data")
    """

    def __init__(self, config: Optional[SecurityConfig] = None):
        super().__init__(name="jarvis_security", version="1.0.0")
        self.config = config or SecurityConfig()
        self.validator: Optional[InputValidator] = None
        self.sanitizer: Optional[InputSanitizer] = None
        self.auth: Optional[AuthManager] = None
        self.encryption: Optional[EncryptionManager] = None
        self.audit: Optional[AuditLogger] = None
        self.secrets: Optional[SecretManager] = None
        self.access_control: Optional[AccessController] = None
        self._rate_limiter: Optional[TokenBucket] = None
        self._start_time = 0.0

    async def initialize(self) -> bool:
        self._start_time = time.time()
        try:
            self.validator = InputValidator(self.config)
            self.sanitizer = InputSanitizer(self.config)
            self.auth = AuthManager(self.config)
            self.encryption = EncryptionManager(self.config)
            self.audit = AuditLogger(self.config)
            self.secrets = SecretManager(self.encryption)
            self.access_control = AccessController(self.auth, self.audit)

            # Token bucket: capacity = max_requests_per_minute, refill = capacity / 60 per sec
            capacity = float(self.config.max_requests_per_minute)
            self._rate_limiter = TokenBucket(capacity=capacity, refill_rate=capacity / 60.0)

            self._metrics.reset()
            self._initialized = True
            logger.info("SecurityService initialized")
            return True
        except Exception as e:
            logger.error("SecurityService init failed: %s", e)
            return False

    async def shutdown(self) -> None:
        logger.info("SecurityService shutting down...")
        self._initialized = False

    # ── Rate Limiting ──────────────────────────────────────────────

    async def check_rate_limit(self, tokens: float = 1.0) -> bool:
        """Check if a request is within the rate limit.

        Args:
            tokens: Number of tokens to consume (default 1.0).

        Returns:
            True if within limit, False if rate limited.
        """
        if not self._rate_limiter or not self.config.rate_limit_enabled:
            return True
        allowed = self._rate_limiter.consume(tokens)
        self._metrics.counter("rate_limit_checks", 1)
        if not allowed:
            self._metrics.counter("rate_limit_blocks", 1)
        return allowed

    async def get_rate_limit_status(self) -> dict:
        """Get the current rate limit status.

        Returns:
            Dict with capacity, available_tokens, refill_rate, enabled.
        """
        if not self._rate_limiter:
            return {"enabled": False, "available_tokens": 0, "capacity": 0, "refill_rate": 0}
        return {
            "enabled": self.config.rate_limit_enabled,
            "capacity": self._rate_limiter.capacity,
            "available_tokens": round(self._rate_limiter.available_tokens, 1),
            "refill_rate": self._rate_limiter.refill_rate,
        }

    async def reset_rate_limiter(self) -> None:
        """Reset the rate limiter to full capacity."""
        if self._rate_limiter:
            self._rate_limiter.reset()
            logger.debug("Rate limiter reset")

    # ── Input Validation ───────────────────────────────────────────

    async def validate(self, input_text: str) -> ValidationResult:
        """Validate input text for security threats.

        Args:
            input_text: The text to validate.

        Returns:
            ValidationResult.
        """
        if not self.validator:
            raise RuntimeError("SecurityService not initialized")
        t0 = time.perf_counter()
        result = self.validator.validate(input_text)
        elapsed = (time.perf_counter() - t0) * 1000
        self._metrics.counter("validations", 1)
        self._metrics.histogram("validation_time_ms", elapsed)
        if not result.is_valid:
            self._metrics.counter("validation_failures", 1)

        if self.config.enable_audit_logging and self.audit:
            self.audit.log_event(SecurityEvent(
                event_type="validation",
                severity="medium" if not result.is_valid else "low",
                source="InputValidator",
                details={
                    "input_length": len(input_text),
                    "risk_score": result.risk_score,
                    "prompt_injection": result.prompt_injection_detected,
                },
                blocked=not result.is_valid,
            ))
        return result

    # ── Input Sanitization ─────────────────────────────────────────

    async def sanitize(self, input_text: str) -> str:
        """Sanitize input text.

        Args:
            input_text: The text to sanitize.

        Returns:
            Sanitized text.
        """
        if not self.sanitizer:
            raise RuntimeError("SecurityService not initialized")
        t0 = time.perf_counter()
        result = self.sanitizer.sanitize(input_text)
        elapsed = (time.perf_counter() - t0) * 1000
        self._metrics.counter("sanitizations", 1)
        self._metrics.histogram("sanitize_time_ms", elapsed)

        if self.config.enable_audit_logging and self.audit:
            self.audit.log_event(SecurityEvent(
                event_type="sanitization",
                severity="low",
                source="InputSanitizer",
                details={"original_length": len(input_text), "sanitized_length": len(result)},
            ))
        return result

    # ── Authentication ─────────────────────────────────────────────

    async def generate_token(self, user_id: str, scope: Optional[List[str]] = None) -> str:
        """Generate an authentication token for a user.

        Args:
            user_id: The user identifier.
            scope: List of permission scopes.

        Returns:
            Token string.
        """
        return await self.authenticate_user(user_id, scope)

    async def authenticate_user(self, user_id: str, scope: Optional[List[str]] = None) -> str:
        """Generate an authentication token for a user.

        Args:
            user_id: The user identifier.
            scope: List of permission scopes.

        Returns:
            Token string.
        """
        if not self.auth:
            raise RuntimeError("SecurityService not initialized")
        token = self.auth.generate_token(user_id, scope)
        self._metrics.counter("tokens_generated", 1)

        if self.config.enable_audit_logging and self.audit:
            self.audit.log_event(SecurityEvent(
                event_type="auth",
                severity="low",
                source="AuthManager",
                user_id=user_id,
                details={"action": "token_generated", "scope": scope},
            ))
        return token

    async def authenticate(self, token: str) -> bool:
        """Validate an authentication token.

        Args:
            token: The token to validate.

        Returns:
            True if valid.
        """
        if not self.auth:
            raise RuntimeError("SecurityService not initialized")
        result = self.auth.authenticate(token)
        self._metrics.counter("auth_checks", 1)
        if self.config.enable_audit_logging and self.audit:
            self.audit.log_event(SecurityEvent(
                event_type="auth",
                severity="low" if result else "high",
                source="AuthManager",
                details={"action": "authenticate", "result": result},
                blocked=not result,
            ))
        return result

    async def validate_scope(self, token: str, required_scope: str) -> bool:
        """Check if a token has the required scope.

        Args:
            token: The token to check.
            required_scope: The scope required.

        Returns:
            True if the token has the scope.
        """
        if not self.auth:
            raise RuntimeError("SecurityService not initialized")
        return self.auth.validate_scope(token, required_scope)

    async def revoke_token(self, token: str) -> bool:
        """Revoke a token.

        Args:
            token: The token to revoke.

        Returns:
            True if revoked.
        """
        if not self.auth:
            raise RuntimeError("SecurityService not initialized")
        result = self.auth.revoke_token(token)
        self._metrics.counter("tokens_revoked", 1)
        return result

    async def get_user_id(self, token: str) -> str:
        """Get the user ID from a token.

        Args:
            token: The token.

        Returns:
            User ID string.
        """
        if not self.auth:
            raise RuntimeError("SecurityService not initialized")
        return self.auth.get_user_id(token)

    # ── Encryption ─────────────────────────────────────────────────

    async def encrypt(self, data: str) -> Tuple[str, str]:
        """Encrypt data.

        Args:
            data: Plaintext.

        Returns:
            Tuple of (ciphertext_b64, iv_b64).
        """
        if not self.encryption:
            raise RuntimeError("SecurityService not initialized")
        t0 = time.perf_counter()
        ciphertext, iv = self.encryption.encrypt(data)
        elapsed = (time.perf_counter() - t0) * 1000
        self._metrics.counter("encryptions", 1)
        self._metrics.histogram("encrypt_time_ms", elapsed)
        return ciphertext, iv

    async def decrypt(self, ciphertext: str, iv: str) -> str:
        """Decrypt data.

        Args:
            ciphertext: Base64 ciphertext.
            iv: Base64 IV.

        Returns:
            Plaintext string.
        """
        if not self.encryption:
            raise RuntimeError("SecurityService not initialized")
        t0 = time.perf_counter()
        plaintext = self.encryption.decrypt(ciphertext, iv)
        elapsed = (time.perf_counter() - t0) * 1000
        self._metrics.counter("decryptions", 1)
        self._metrics.histogram("decrypt_time_ms", elapsed)
        return plaintext

    # ── Audit Logging ──────────────────────────────────────────────

    async def audit_log(self, event: SecurityEvent) -> None:
        """Log a security event.

        Args:
            event: The SecurityEvent to log.
        """
        if not self.audit:
            raise RuntimeError("SecurityService not initialized")
        self.audit.log_event(event)
        self._metrics.counter("audit_events", 1)

    async def query_audit_log(self, filters: Optional[Dict] = None) -> List[SecurityEvent]:
        """Query audit log events.

        Args:
            filters: Optional dict of field:value filters.

        Returns:
            List of matching SecurityEvent objects.
        """
        if not self.audit:
            raise RuntimeError("SecurityService not initialized")
        self._metrics.counter("audit_queries", 1)
        return self.audit.query(filters)

    async def get_recent_events(self, limit: int = 50) -> List[SecurityEvent]:
        """Get recent security events.

        Args:
            limit: Max events.

        Returns:
            List of SecurityEvent.
        """
        if not self.audit:
            raise RuntimeError("SecurityService not initialized")
        return self.audit.get_recent_events(limit)

    async def export_audit_log(self, format: str = "json") -> str:
        """Export audit log.

        Args:
            format: "json" or "csv".

        Returns:
            Formatted string.
        """
        if not self.audit:
            raise RuntimeError("SecurityService not initialized")
        return self.audit.export_logs(format)

    # ── Secret Management ──────────────────────────────────────────

    async def store_secret(self, name: str, value: str, scope: str = "global") -> bool:
        """Store a secret (encrypted in memory).

        Args:
            name: The secret name.
            value: The plaintext secret value.
            scope: The scope.

        Returns:
            True if stored.
        """
        if not self.secrets:
            raise RuntimeError("SecurityService not initialized")
        result = self.secrets.store_secret(name, value, scope)
        self._metrics.counter("secrets_stored", 1)
        if self.config.enable_audit_logging and self.audit:
            self.audit.log_event(SecurityEvent(
                event_type="secret_management",
                severity="low",
                source="SecretManager",
                details={"action": "store", "secret_name": name, "scope": scope},
            ))
        return result

    async def get_secret(self, name: str) -> Optional[str]:
        """Get a decrypted secret value.

        Args:
            name: The secret name.

        Returns:
            Decrypted value or None.
        """
        if not self.secrets:
            raise RuntimeError("SecurityService not initialized")
        value = self.secrets.get_secret(name)
        self._metrics.counter("secret_retrievals", 1)
        return value

    async def list_secrets(self) -> List[dict]:
        """List all stored secrets (metadata only).

        Returns:
            List of secret metadata dicts.
        """
        if not self.secrets:
            raise RuntimeError("SecurityService not initialized")
        return self.secrets.list_secrets()

    async def revoke_secret(self, name: str) -> bool:
        """Revoke a secret.

        Args:
            name: The secret name.

        Returns:
            True if revoked.
        """
        if not self.secrets:
            raise RuntimeError("SecurityService not initialized")
        result = self.secrets.revoke_secret(name)
        if result and self.config.enable_audit_logging and self.audit:
            self.audit.log_event(SecurityEvent(
                event_type="secret_management",
                severity="medium",
                source="SecretManager",
                details={"action": "revoke", "secret_name": name},
            ))
        return result

    async def rotate_secret(self, name: str, new_value: str) -> bool:
        """Rotate a secret with a new value.

        Args:
            name: The secret name.
            new_value: The new plaintext value.

        Returns:
            True if rotated.
        """
        if not self.secrets:
            raise RuntimeError("SecurityService not initialized")
        result = self.secrets.rotate_secret(name, new_value)
        if result and self.config.enable_audit_logging and self.audit:
            self.audit.log_event(SecurityEvent(
                event_type="secret_management",
                severity="medium",
                source="SecretManager",
                details={"action": "rotate", "secret_name": name},
            ))
        return result

    # ── Access Control ─────────────────────────────────────────────

    async def check_access(self, token: str, tool_name: str, args: Optional[Dict[str, Any]] = None) -> bool:
        """Check if a token has access to a tool.

        Args:
            token: The authentication token.
            tool_name: The tool name.
            args: Optional tool arguments.

        Returns:
            True if access is granted.
        """
        if not self.access_control:
            raise RuntimeError("SecurityService not initialized")
        granted = self.access_control.check_access(token, tool_name, args)
        self._metrics.counter("access_checks", 1)
        if not granted:
            self._metrics.counter("access_denied", 1)
        return granted

    async def register_tool_scope(self, tool_name: str, required_scope: str) -> None:
        """Register the required scope for a tool.

        Args:
            tool_name: The tool name.
            required_scope: Required scope.
        """
        if not self.access_control:
            raise RuntimeError("SecurityService not initialized")
        self.access_control.register_tool_scope(tool_name, required_scope)

    async def get_tool_scopes(self) -> Dict[str, str]:
        """Get the current tool-to-scope mapping.

        Returns:
            Dict of tool_name -> required_scope.
        """
        if not self.access_control:
            raise RuntimeError("SecurityService not initialized")
        return self.access_control.get_tool_scopes()

    # ── Health & Stats ─────────────────────────────────────────────

    async def health(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "service_name": self.name,
            "version": self.version,
            "initialized": self._initialized,
            "uptime_seconds": round(uptime, 1),
        }

    async def stats(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        return {
            "service": self.name,
            "version": self.version,
            "uptime_seconds": round(uptime, 1),
            "metrics": self._metrics.snapshot(),
        }
