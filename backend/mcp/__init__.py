"""
AND9 — MCP (Model Context Protocol) Server Package.

Exposes tools (search, filesystem, etc.) as MCP tools
that the AI brain can call during execution.

Current tools:
  - DuckDuckGo Web Search
"""

from backend.mcp.server import mcp

__all__ = ["mcp"]
