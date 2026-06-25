# OpenHands (agent-canvas) — Bugs & Issues

> Generated from GitHub Issues (https://github.com/OpenHands/agent-canvas/issues)
> Date: 2026-06-24

---

## Security Issues

### 1. SESSION_API_KEY leaked in automation run command logs
- **Issue**: [#1470](https://github.com/OpenHands/agent-canvas/issues/1470)
- **Severity**: **CRITICAL**
- **Status**: Open
- **Description**: `SESSION_API_KEY` (and potentially other secrets) are exposed in plain text in automation run command logs. When an automation run times out, the full shell command is recorded including `export SESSION_API_KEY=...`.
- **Impact**: Anyone with access to automation run logs (log aggregators, CI artifacts, monitoring dashboards) can read the session API key, granting full access to the agent-server API.
- **Suggested fixes**:
  - Mask secrets before logging (redact `export *KEY*=`, `*SECRET*=`, `*TOKEN*=`)
  - Pass secrets via subprocess `env` parameter, not inline in shell commands
  - Scrub timeout/error messages
  - Audit all log sites

---

## High-Severity Bugs

### 2. Workspace file preview returns 401 Unauthorized on non-HTTPS non-loopback hosts
- **Issue**: [#1437](https://github.com/OpenHands/agent-canvas/issues/1437)
- **Status**: Open
- **Description**: When running agent-canvas on a non-HTTPS hostname (e.g. VM with its own IP, container IP), workspace file preview fails with 401. The `oh_workspace_session_key` cookie gets `Secure` flag even when the browser uses plain HTTP on a non-loopback hostname, so the browser doesn't send the cookie.
- **Root cause**: `POST /api/auth/workspace-session` may mint cookies with `Secure=true` incorrectly.
- **Suggested fix**: Add a `--disable-secure` option to work with HTTP in such environments.

### 3. pickFallbackBackend ignores backend health & kind — "No backend is configured"
- **Issue**: [#1352](https://github.com/OpenHands/agent-canvas/issues/1352)
- **Status**: Open
- **Description**: When there's no valid backend selection, `pickFallbackBackend` returns `backends[0]` (first registered backend) ignoring both its `kind` and its recorded health. If index-0 is a cloud backend or dead local backend, local-protocol calls throw "No backend is configured."
- **Root cause**: `active-store.ts:36-38` — selection consults neither backend kind nor the health store.
- **Regression from**: #1093 (Docker/local fix in #1081).

### 4. LiteLLM auth error misrepresents database connectivity failure
- **Issue**: [#1284](https://github.com/OpenHands/agent-canvas/issues/1284)
- **Status**: Open
- **Description**: A conversation failed with `LLMAuthenticationError`, but the LiteLLM payload indicates a database infrastructure problem (`Can't reach database server at 127.0.0.1:5432`). Internal proxy/database connectivity failures are surfaced as misleading user-authentication errors.
- **Observed model**: `litellm_proxy/minimax-m2.7`
- **Expected**: Backend health/infrastructure failures should be distinguished from invalid user credentials.

### 5. `CURRENT_DATETIME` in system prompt becomes permanently stale after first settings save
- **Issue**: [#1371](https://github.com/OpenHands/agent-canvas/issues/1371)
- **Status**: Open
- **Description**: Saving settings causes `CURRENT_DATETIME` to be fixed and no longer updated in agent context output. It's passed in from settings instead of being generated fresh for every new conversation.
- **Fix PR**: #1370

---

## Functional Bugs

### 6. File tree viewer not working on cloud backends
- **Issue**: [#1366](https://github.com/OpenHands/agent-canvas/issues/1366)
- **Status**: Open
- **Description**: When a user clicks the file tree button to see workspace files, nothing appears. Works on local backends but not cloud backends.

### 7. ACP conversation messages disappear or move on reload
- **Issue**: [#1365](https://github.com/OpenHands/agent-canvas/issues/1365)
- **Status**: Open
- **Description**: Messages from ACP agents (e.g. Codex) display correctly during the conversation, but when the conversation is reloaded, these messages disappear from their original place and show up concatenated at the end instead.

### 8. Cmd-clicking a sidebar conversation opens on the wrong backend
- **Issue**: [#1422](https://github.com/OpenHands/agent-canvas/issues/1422)
- **Status**: Open
- **Description**: When a user cmd-clicks a conversation in the sidebar to open it in a new tab, the new tab may initialize with a different backend, showing "conversation not found."
- **Impact**: Multi-backend setups where conversations are scoped to specific backends.

### 9. Failed messages remain as the most recent message
- **Issue**: [#1196](https://github.com/OpenHands/agent-canvas/issues/1196)
- **Status**: Open
- **Description**: When a message fails to send, it remains as the most recent message. All subsequent messages appear above it, creating a confusing conversation flow.
- **Suggested fixes**:
  - Add a "Retry" button to failed messages
  - Auto-retry with exponential backoff
  - Allow users to dismiss failed messages

### 10. Cannot select existing conversation from collapsed side nav bar
- **Issue**: [#1194](https://github.com/OpenHands/agent-canvas/issues/1194)
- **Status**: Open
- **Description**: When the side navigation bar is collapsed, there is no button to view or select existing conversations. Users must expand the side nav to access previous conversations.

### 11. ChatGPT Subscription auth error when creating LLM Profile
- **Issue**: [#1408](https://github.com/OpenHands/agent-canvas/issues/1408)
- **Status**: Open
- **Description**: When creating an LLM Profile and selecting "ChatGPT subscription", an error appears: *"Subscription status is unavailable. Upgrade the agent server to a version with subscription auth endpoints."*

### 12. Agent creates redundant refs when working with PRs
- **Issue**: [#1174](https://github.com/OpenHands/agent-canvas/issues/1174)
- **Status**: Open
- **Description**: When an agent is asked to work with a PR, it uses `git fetch origin pull/<N>/head:pr-<N>` which creates redundant local refs instead of using the PR source branch name directly.

---

## Documentation / Process Issues

### 13. Code repo is moving
- **Reference**: README Note — [Agent Canvas transition FAQ](https://github.com/OpenHands/OpenHands/issues/14841)
- **Description**: The code in this repo is moving. Source for OpenHands Agent and Agent Server now lives in `OpenHands/software-agent-sdk`. Source for Agent Canvas now lives in `OpenHands/agent-canvas`.

### 14. Confusing dev script naming
- **Issue**: [#226](https://github.com/OpenHands/agent-canvas/issues/226)
- **Status**: Open
- **Description**: Current dev script naming is confusing (`dev:safe`, `dev:minimal` are ambiguous). Proposed renaming with clear conventions based on which services are included.

---

## Warnings from Documentation

### 15. Running without a sandbox gives full filesystem access
- **Reference**: README Option 1 (Without a Sandbox)
- **Warning**: Running the agent-server directly on the machine means the agent has full access to your filesystem.

### 16. Running from source also gives full filesystem access
- **Reference**: README Option 3 (From Source)
- **Warning**: Same warning applies — the agent-server runs directly on the machine.

### 17. Security hardening needed for cloud deployment
- **Reference**: README Quickstart / SELF_HOSTING.md
- **Note**: When running on a server in the cloud, security hardening is especially important.

---

## Issue Triage Guidelines (from main repo)

- **Reference**: [ISSUE_TRIAGE.md](https://github.com/OpenHands/OpenHands/blob/main/ISSUE_TRIAGE.md)
- All issues must be tagged with **enhancement**, **bug**, or **troubleshooting/help**.
- Severity levels: **High** (high visibility / many users), **Critical** (all users or security).
- Issues with no activity within 40 days are marked **Stale**; closed after 10 more days of inactivity.
- Unclear issues may be closed as **not planned** after a week without response.
- Issues with multiple requests are narrowed down to one request/fix for better tracking.
- **good first issue** label criteria: narrow scope, clear bug/outcome, bounded area, straightforward validation.

---

## Summary

| # | Issue | Type | Status |
|---|-------|------|--------|
| 1 | SESSION_API_KEY leaked in automation logs | Security | Open |
| 2 | Workspace file preview 401 on non-HTTPS | Bug | Open |
| 3 | pickFallbackBackend ignores health | Bug | Open |
| 4 | LiteLLM auth error misrepresents DB failure | Bug | Open |
| 5 | CURRENT_DATETIME stale after settings save | Bug | Open |
| 6 | File tree not working on cloud backends | Bug | Open |
| 7 | ACP messages disappear on reload | Bug | Open |
| 8 | Cmd-click opens wrong backend | Bug | Open |
| 9 | Failed messages remain at top | Bug | Open |
| 10 | Collapsed nav can't select conversations | Bug | Open |
| 11 | ChatGPT Subscription auth error | Bug | Open |
| 12 | Agent creates redundant PR refs | Bug | Open |
| 13 | Code repo is moving | Process | Note |
| 14 | Confusing dev script naming | Enhancement | Open |
| 15 | No-sandbox = full filesystem access | Warning | Doc |
| 16 | From-source = full filesystem access | Warning | Doc |
| 17 | Security hardening for cloud | Warning | Doc |
