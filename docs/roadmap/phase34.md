# Phase 34: Error Recovery

## Purpose
Resilience framework with circuit breaker, retry handler, fallback chains, rollback manager, and multi-step recovery workflows. `CircuitBreaker` implements a three-state machine (closed/open/half-open) that prevents calls to failing operations and auto-recovers after a timeout. `RetryHandler` executes operations with exponential backoff and jitter. `FallbackHandler` manages ordered fallback chains for graceful degradation. `RollbackManager` tracks compensating actions for rollback. `RecoveryWorkflow` orchestrates multi-step recovery with per-step retry policies (skip/retry/rollback/stop) and progress tracking.

## Architecture
```
CircuitBreaker
  ├── call(operation, fallback) → result (handles closed/open/half-open states)
  ├── reset() / is_available() / get_status()
  └── threshold failures → open, timeout → half-open, success → closed

RetryHandler
  ├── execute_with_retry(operation, max_retries, backoff_ms) → (success, result, attempts)
  └── Exponential backoff + jitter

FallbackHandler
  ├── register_fallback(operation_name, fallback_fn)
  ├── execute_with_fallback(operation, fallback_ops) → result
  └── Ordered fallback chain with max depth

RollbackManager
  ├── register_compensation(step_name, compensation_fn)
  ├── rollback(step_name) → bool
  └── has_compensation(step_name) → bool

RecoveryWorkflow
  ├── add_step(name, func, retry_policy, max_retries)
  ├── execute(context) → (success, context)
  ├── get_progress() / rollback() / reset()
  └── Multi-step workflow with conditional branching
```

## Code
```python
class CircuitBreaker:
    def call(self, operation, fallback=None):
        if self.state == "open":
            if time.time() - self.last_failure_time >= self.reset_timeout:
                self.state = "half-open"
            else:
                return fallback() if fallback else None
        try:
            result = operation()
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            return fallback() if fallback else None

class RetryHandler:
    def execute_with_retry(self, operation, max_retries=None, backoff_ms=None) -> Tuple[bool, Any, int]:
        for attempt in range(1, max_retries + 2):
            try:
                result = operation()
                return True, result, attempt
            except Exception as e:
                if attempt <= max_retries:
                    sleep_ms = backoff_ms * (self._backoff_multiplier ** (attempt - 1))
                    time.sleep((sleep_ms + random.uniform(0, sleep_ms * 0.1)) / 1000)
        return False, last_exception, max_retries + 1

class RecoveryWorkflow:
    def execute(self, context) -> Tuple[bool, ErrorContext]:
        for step in self._steps:
            try:
                step.result = step.func(context)
                step.state = StepState.SUCCESS
            except Exception as e:
                if step.retry_policy == "rollback": self.rollback(); return False, context
                if step.retry_policy == "stop": return False, context
        return True, context
```

## Location
`app/core/errors/` — circuit breaker, retry handler, fallback handler, rollback manager, recovery workflow, error analyzer, user messages
