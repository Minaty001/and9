"""
Tests for Phase 31 — Security Layer.
"""

import pytest
from services.phase31_security import (
    SecurityConfig,
    SecurityEvent,
    ValidationResult,
    InputValidator,
    InputSanitizer,
    AuthManager,
    EncryptionManager,
    AuditLogger,
    SecurityService,
)


class TestInputValidator:
    """Verify input validation."""

    def test_validate_clean_input(self):
        validator = InputValidator()
        result = validator.validate("hello world")
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validate_blocked_chars(self):
        validator = InputValidator()
        result = validator.validate("<script>alert('xss')</script>")
        assert len(result.blocked_chars_found) > 0

    def test_validate_sql_injection(self):
        validator = InputValidator()
        result = validator.validate("SELECT * FROM users")
        assert len(result.warnings) > 0
        assert result.risk_score > 0

    def test_validate_max_length(self):
        validator = InputValidator(SecurityConfig(max_input_length=10))
        result = validator.validate("a" * 20)
        assert result.is_valid is False
        assert "exceeds max length" in " ".join(result.errors).lower()

    def test_validate_risk_score(self):
        validator = InputValidator()
        result = validator.validate("hello")
        assert 0.0 <= result.risk_score <= 1.0


class TestInputSanitizer:
    """Verify input sanitization."""

    def test_sanitize_removes_html(self):
        sanitizer = InputSanitizer()
        result = sanitizer.sanitize("<script>alert('xss')</script>")
        assert "&lt;script&gt;" in result
        assert "<script>" not in result

    def test_sanitize_strips_null_bytes(self):
        sanitizer = InputSanitizer()
        result = sanitizer.sanitize("hello\x00world")
        assert "\x00" not in result

    def test_sanitize_normalizes_whitespace(self):
        sanitizer = InputSanitizer()
        result = sanitizer.sanitize("hello    world")
        assert "hello world" == result

    def test_sanitize_empty_string(self):
        sanitizer = InputSanitizer()
        assert sanitizer.sanitize("") == ""


class TestAuthManager:
    """Verify authentication and token management."""

    def test_generate_token(self):
        auth = AuthManager()
        token = auth.generate_token("user123")
        assert token is not None
        assert len(token) > 0

    def test_authenticate_valid(self):
        auth = AuthManager()
        token = auth.generate_token("user123")
        assert auth.authenticate(token) is True

    def test_authenticate_invalid(self):
        auth = AuthManager()
        assert auth.authenticate("invalid_token") is False

    def test_revoke_token(self):
        auth = AuthManager()
        token = auth.generate_token("user123")
        assert auth.revoke_token(token) is True
        assert auth.authenticate(token) is False

    def test_get_user_id(self):
        auth = AuthManager()
        token = auth.generate_token("user123")
        assert auth.get_user_id(token) == "user123"

    def test_validate_scope(self):
        auth = AuthManager()
        token = auth.generate_token("user123", scope=["read", "write"])
        assert auth.validate_scope(token, "read") is True
        assert auth.validate_scope(token, "admin") is False

    def test_revoke_nonexistent(self):
        auth = AuthManager()
        assert auth.revoke_token("nonexistent") is False


class TestEncryptionManager:
    """Verify encryption and decryption."""

    def test_encrypt_decrypt(self):
        mgr = EncryptionManager()
        ciphertext, iv = mgr.encrypt("sensitive data")
        plaintext = mgr.decrypt(ciphertext, iv)
        assert plaintext == "sensitive data"

    def test_encrypt_empty_string(self):
        mgr = EncryptionManager()
        ciphertext, iv = mgr.encrypt("")
        plaintext = mgr.decrypt(ciphertext, iv)
        assert plaintext == ""

    def test_decrypt_wrong_key_fails(self):
        mgr1 = EncryptionManager()
        mgr1._key = b"a" * 32
        mgr2 = EncryptionManager()
        mgr2._key = b"b" * 32
        ciphertext, iv = mgr1.encrypt("test")
        with pytest.raises(ValueError):
            mgr2.decrypt(ciphertext, iv)

    def test_generate_key(self):
        mgr = EncryptionManager()
        key = mgr.generate_key()
        assert len(key) > 0


class TestAuditLogger:
    """Verify audit logging."""

    def test_log_event(self):
        audit = AuditLogger()
        event = SecurityEvent(event_type="auth", severity="medium")
        audit.log_event(event)
        recent = audit.get_recent_events()
        assert len(recent) == 1

    def test_query_by_type(self):
        audit = AuditLogger()
        audit.log_event(SecurityEvent(event_type="auth", severity="low"))
        audit.log_event(SecurityEvent(event_type="validation", severity="medium"))
        results = audit.query({"event_type": "auth"})
        assert len(results) == 1

    def test_get_events_by_user(self):
        audit = AuditLogger()
        audit.log_event(SecurityEvent(event_type="auth", severity="low", user_id="user1"))
        audit.log_event(SecurityEvent(event_type="auth", severity="low", user_id="user2"))
        events = audit.get_events_by_user("user1")
        assert len(events) == 1

    def test_export_json(self):
        audit = AuditLogger()
        audit.log_event(SecurityEvent(event_type="auth", severity="low"))
        exported = audit.export_logs("json")
        assert '"event_type": "auth"' in exported

    def test_export_csv(self):
        audit = AuditLogger()
        audit.log_event(SecurityEvent(event_type="auth", severity="low"))
        exported = audit.export_logs("csv")
        assert "auth" in exported

    def test_clear(self):
        audit = AuditLogger()
        audit.log_event(SecurityEvent(event_type="auth", severity="low"))
        audit.clear()
        assert len(audit.get_recent_events()) == 0


class TestSecurityService:
    """Verify service wrapper."""

    @pytest.mark.asyncio
    async def test_initialize(self):
        svc = SecurityService()
        assert await svc.initialize() is True

    @pytest.mark.asyncio
    async def test_validate(self):
        svc = SecurityService()
        await svc.initialize()
        result = await svc.validate("hello world")
        assert result.is_valid is True

    @pytest.mark.asyncio
    async def test_sanitize(self):
        svc = SecurityService()
        await svc.initialize()
        result = await svc.sanitize("<script>alert(1)</script>")
        assert "&lt;" in result

    @pytest.mark.asyncio
    async def test_authenticate_user(self):
        svc = SecurityService()
        await svc.initialize()
        token = await svc.authenticate_user("user123")
        assert await svc.authenticate(token) is True

    @pytest.mark.asyncio
    async def test_encrypt_decrypt(self):
        svc = SecurityService()
        await svc.initialize()
        cipher, iv = await svc.encrypt("secret")
        plain = await svc.decrypt(cipher, iv)
        assert plain == "secret"

    @pytest.mark.asyncio
    async def test_audit_log(self):
        svc = SecurityService()
        await svc.initialize()
        event = SecurityEvent(event_type="test", severity="low")
        await svc.audit_log(event)
        events = await svc.get_recent_events()
        assert len(events) >= 1

    @pytest.mark.asyncio
    async def test_health(self):
        svc = SecurityService()
        await svc.initialize()
        health = await svc.health()
        assert health["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_shutdown(self):
        svc = SecurityService()
        await svc.initialize()
        await svc.shutdown()
        assert not svc.is_initialized()
