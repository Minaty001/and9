# Phase 33: Error Recovery

## Overview

Graceful degradation, retry policies, circuit breaker, fallback mechanisms, and exception categorization with suggested remedies.

## Architecture

```
Operation Call
     │
     ▼
┌──────────────────────┐
│ Circuit Breaker       │  ◄── closed → open → half-open
│ (State Machine)       │      Auto-recover after timeout
└─────────┬────────────┘
          │ (if closed/half-open)
          ▼
┌──────────────────────┐
│ RetryHandler          │  ◄── Exponential backoff with jitter
│ (Exponential Backoff) │      Configurable max retries
└─────────┬────────────┘
          │ (if failed)
          ▼
┌──────────────────────┐
│ FallbackHandler       │  ◄── Chain of fallback operations
│ (Fallback Chain)      │      Graceful degradation
└─────────┬────────────┘
          │
          ▼
┌──────────────────────┐
│ ErrorAnalyzer         │  ◄── Classify: timeout/resource/validation/auth/system
│ (Classification)      │      Suggest remedy, assess severity
└──────────────────────┘
```

## Components

- **CircuitBreaker**: Three-state machine (closed/open/half-open). Opens after N consecutive failures. Auto-transitions to half-open after reset timeout. Success in half-open closes the circuit.
- **RetryHandler**: Executes with exponential backoff and jitter. Configurable max retries and backoff multiplier. Tracks success/failure stats.
- **FallbackHandler**: Chain of fallback operations for graceful degradation. Configurable max depth.
- **ErrorAnalyzer**: Classifies errors (timeout/resource/validation/auth/system/unknown). Suggests remedies. Assesses severity (low/medium/high/critical).

## Usage

```python
from services.phase33_error_recovery import ErrorRecoveryService
svc = ErrorRecoveryService()
await svc.initialize()

success, result, ctx = await svc.execute_with_recovery(
    "api_call",
    lambda: risky_api_call(),
    fallback_operations=[lambda: cached_result()],
    max_retries=3,
)
if success:
    print(f"Result: {result}")
else:
    print(f"Failed: {ctx.suggested_remedy}")
```

## Test Coverage

22+ tests covering all components and the service wrapper.
