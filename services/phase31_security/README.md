# Phase 31: Security Layer

## Overview

Input validation, sanitization, authentication, encryption, SQL injection/XSS prevention, and audit logging.

## Architecture

```
User Input
     │
     ▼
┌─────────────────┐
│ InputValidator   │  ◄── Length check, blocked chars, dangerous patterns
│                  │       Returns risk score (0-1)
└────────┬────────┘
         │ if valid
         ▼
┌─────────────────┐
│ InputSanitizer   │  ◄── Strip null bytes, HTML encode, normalize
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ SecurityService  │  ◄── ServiceBase wrapper
│                  │
│  ┌───────────┐  │
│  │ AuthManager│  │  ◄── Token generation, validation, revocation
│  └───────────┘  │
│  ┌───────────┐  │
│  │ Encryption │  │  ◄── AES-256-GCM encrypt/decrypt
│  └───────────┘  │
│  ┌───────────┐  │
│  │ AuditLogger│  │  ◄── Event logging, query, export
│  └───────────┘  │
└─────────────────┘
```

## Components

- **InputValidator**: Validates input for length, blocked characters, SQL injection, XSS, shell injection patterns. Returns a risk score 0-1.
- **InputSanitizer**: Strips null bytes, HTML-encodes entities, removes dangerous characters, normalizes whitespace.
- **AuthManager**: Mock token-based authentication with generate/validate/revoke and scope checking.
- **EncryptionManager**: AES-256-GCM symmetric encryption with key persistence.
- **AuditLogger**: Structured event logging with query, user-based filtering, and JSON/CSV export.

## Usage

```python
from services.phase31_security import SecurityService
svc = SecurityService()
await svc.initialize()

# Validate input
result = await svc.validate("user input")
if result.is_valid:
    clean = await svc.sanitize(result.sanitized_input)

# Authentication
token = await svc.authenticate_user("user123", scope=["read", "write"])
if await svc.authenticate(token):
    user = await svc.get_user_id(token)

# Encryption
cipher, iv = await svc.encrypt("sensitive data")
plain = await svc.decrypt(cipher, iv)
```

## Test Coverage

24+ tests covering all components and the service wrapper.
