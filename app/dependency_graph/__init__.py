"""
app/dependency_graph — Code dependency graph analysis.

AST-based dependency analysis with MCP server support for IDE tooling.
"""

from app.dependency_graph.analyzer import DependencyAnalyzer
from app.dependency_graph.graph import DependencyGraph
from app.dependency_graph.mcp_server import DependencyGraphMCPServer

# FastAPI routes (optional — requires fastapi/uvicorn)
try:
    from app.dependency_graph.routes import get_server  # noqa: F401
except ImportError:
    def get_server():  # type: ignore
        raise ImportError("fastapi is required for the dependency graph API router")

__all__ = [
    "DependencyAnalyzer",
    "DependencyGraph",
    "DependencyGraphMCPServer",
    "get_server",
]
