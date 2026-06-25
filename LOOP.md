# JARVIS PCOS — Loop Engineering Configuration

## Purpose
Apply loop-engineering patterns to continuously discover, triage, and fix bugs
in the JARVIS PCOS codebase. This file documents the loop cadence, limits, and
safety gates.

## Cadence

| Loop | Cadence | Level | Description |
|------|---------|-------|-------------|
| Bug Hunt | Weekly (Mon 09:00) | L1 (Report) | Scan for new bugs, update STATE.md |
| PR Review | On-demand | L2 (Assisted) | Code review with verifier |
| Changelog | After releases | L1 (Report) | Draft changelog from git log |

## Budget & Limits

| Resource | Limit | Action |
|----------|-------|--------|
| Tokens per loop | 5000 | Hard cap — escalate if exceeded |
| Attempts per fix | 3 | Escalate to human after 3 failed attempts |
| Max files per fix | 5 | Break into multiple loops if more needed |

## Safety Gates

1. **Path denylist** (never auto-edit):
   - `.env` / `.env.*`
   - `**/secrets/**`
   - `**/credentials/**`
   - `android/**` (requires human review)

2. **No auto-merge**: All fixes require human review.

3. **Verifier**: Manual verification via `pytest` before commit.

## State

See [STATE.md](./STATE.md) for current state and known issues.

## Connectors

| Connector | Scope | Permission |
|-----------|-------|------------|
| GitHub | Read issues, create PRs | Read + Pull (no direct push) |
| Filesystem | `app/`, `scripts/`, `tests/` | Read + Write (denylist enforced) |
