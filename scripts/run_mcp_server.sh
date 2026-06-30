#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# AND9 — MCP Server Runner
# ─────────────────────────────────────────────────────────────
# Usage:
#   ./scripts/run_mcp_server.sh            # stdio mode (default)
#   ./scripts/run_mcp_server.sh --sse 8001 # SSE mode (network)
# ─────────────────────────────────────────────────────────────
set -euo pipefail
cd "$(dirname "$0")/.."

# Activate venv if present
if [ -d .venv ]; then
  source .venv/bin/activate
fi

MODE="${1:-stdio}"
PORT="${2:-8001}"

case "$MODE" in
  stdio|--stdio)
    exec python -m app.mcp.server
    ;;
  sse|--sse)
    exec python -m app.mcp.server --transport sse --port "$PORT"
    ;;
  *)
    echo "Usage: $0 [stdio|sse] [port]"
    exit 1
    ;;
esac
