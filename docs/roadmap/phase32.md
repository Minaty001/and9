# Phase 32: Security

## Purpose
Comprehensive security framework with input validation, authentication, encryption, access control, audit logging, and secret management. `InputValidator` checks for SQL injection, XSS, shell injection, and prompt injection patterns with risk scoring. `AuthManager` provides token-based authentication with scope checking and revocation. `EncryptionManager` implements mock AES-256-GCM encryption with integrity verification. `AccessController` ties together token validation and audit logging for tool-level access decisions. `AuditLogger` records structured security events with query/export. `SecretManager` stores encrypted secrets in memory.

## Architecture
```
InputValidator
  ├── validate(input_text) → ValidationResult (risk_score, blocked_chars, prompt_injection detection)
  └── Pattern sets: SQL_INJECTION, XSS, SHELL_INJECTION, PROMPT_INJECTION

AuthManager
  ├── generate_token(user_id, scope) → token
  ├── authenticate(token) → bool
  ├── validate_scope(token, required_scope) → bool
  ├── revoke_token(token) → bool
  └── get_user_id(token) → str

EncryptionManager
  ├── encrypt(data) → (ciphertext_b64, iv_b64)
  ├── decrypt(ciphertext, iv) → plaintext
  └── generate_key() → b64 key string

AccessController
  └── check_access(token, tool_name, params) → bool (integrates AuthManager + AuditLogger)

AuditLogger
  ├── log_event(SecurityEvent)
  ├── query(filters) → List[SecurityEvent]
  └── get_recent_events(limit) / export_to_dict()

SecretManager
  ├── store_secret(name, value, scope)
  ├── get_secret(name) → decrypted value
  ├── list_secrets() / revoke_secret(name) / rotate_secret(name)
  └── Uses EncryptionManager for at-rest encryption
```

## Code
```python
class InputValidator:
    def validate(self, input_text) -> ValidationResult:
        risk_score = 0.0
        for char in self.blocked_chars:
            if char in input_text: risk_score = min(1.0, risk_score + 0.15)
        for pattern in SQL_INJECTION_PATTERNS:
            if pattern.search(input_text): risk_score = min(1.0, risk_score + 0.3)
        prompt_injection_detected, patterns = self._check_prompt_injection(input_text)
        if prompt_injection_detected: risk_score = min(1.0, risk_score + 0.4)
        return ValidationResult(is_valid=risk_score < 0.7, risk_score=round(risk_score, 2))

class AuthManager:
    def generate_token(self, user_id, scope=None) -> str:
        token = hashlib.sha256(f"{user_id}:{uuid.uuid4().hex}:{time.time()}".encode()).hexdigest()
        self._tokens[token] = {"user_id": user_id, "scope": scope or ["read"], "revoked": False}
        return token

class EncryptionManager:
    def encrypt(self, data) -> Tuple[str, str]:
        iv = os.urandom(12)
        plain_bytes = data.encode("utf-8")
        cipher = bytes([b ^ self._key[i % len(self._key)] for i, b in enumerate(plain_bytes)])
        return base64.b64encode(cipher).decode(), base64.b64encode(iv).decode()
```

## Location
`app/core/security/` — validator, auth, encryption, access controller, audit logger, secret manager
