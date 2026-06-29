"""
AND9 — MCP Server.

Exposes tools for the AI brain via the Model Context Protocol.
Can run as a stdio server (for subprocess integration) or
as an SSE server (for networked deployment).

Usage (stdio — default):
    python -m backend.mcp.server

Usage (SSE — for Render / networked):
    python -m backend.mcp.server --transport sse --port 8001
"""

import logging
import argparse

from mcp.server import FastMCP

from backend.integrations.duckduckgo import web_search

logger = logging.getLogger(__name__)

# ── MCP Instance ────────────────────────────────────────────────
mcp = FastMCP("AND9 DuckDuckGo Search")


# ── Tools ────────────────────────────────────────────────────────

@mcp.tool()
def search_web(query: str, max_results: int = 5) -> str:
    """Search the web using DuckDuckGo (no API key required).

    Use this tool when the user asks a question that requires
    up-to-date information from the internet — news, facts,
    weather, recent events, etc.

    Args:
        query: The search term or question.
        max_results: Number of results to return (1–10, default 5).

    Returns:
        A formatted string of search results with title, URL, and snippet.
    """
    results = web_search(query, max_results=max_results)
    if not results:
        return "No search results found."

    lines = []
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. {r['title']}")
        lines.append(f"   URL: {r['href']}")
        lines.append(f"   {r['body']}")
        lines.append("")
    return "\n".join(lines).strip()


# ── Run ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="AND9 MCP Server")
    parser.add_argument("--transport", choices=["stdio", "sse"], default="stdio")
    parser.add_argument("--port", type=int, default=8001, help="Port for SSE transport")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    if args.transport == "sse":
        logger.info("Starting MCP SSE server on port %d", args.port)
        mcp.run(transport="sse", port=args.port)
    else:
        logger.info("Starting MCP stdio server")
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
