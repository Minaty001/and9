"""
AND9 — Dependency Graph MCP Server.

A lightweight, pure-Python dependency graph analyzer and MCP server.
Parses Python source code using the built-in `ast` module, builds
a directed dependency graph, and exposes it via MCP tools and API
endpoints.

Designed for the JARVIS AI OS roadmap — Phase 9 (Tool System)
and Phase 14 (Coding Intelligence).

Zero external dependencies — works on any Python 3.11+.
Termux-compatible.
"""

from app.and9.dependency_graph.analyzer import DependencyAnalyzer
from app.and9.dependency_graph.graph import DependencyGraph

__all__ = [
    "DependencyAnalyzer",
    "DependencyGraph",
]
