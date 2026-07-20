"""
AND9 — Dependency Graph API Routes.

FastAPI/Flask-compatible routes exposing the dependency graph
analyzer and MCP server over HTTP.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.dependency_graph.mcp_server import DependencyGraphMCPServer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dependency-graph", tags=["dependency-graph"])

# Global server instance (initialized lazily)
_server: Optional[DependencyGraphMCPServer] = None


def get_server() -> DependencyGraphMCPServer:
    """Get or create the dependency graph MCP server.
    
    Uses the project root as the analysis target.
    """
    global _server
    if _server is None:
        import os
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
        _server = DependencyGraphMCPServer(root_path=root)
    return _server


# ── Request/Response Models ──────────────────────────────────────

class AnalyzeResponse(BaseModel):
    node_count: int
    edge_count: int
    status: str
    message: str


class FileQuery(BaseModel):
    filepath: str


class ImpactQuery(BaseModel):
    filepath: str
    max_depth: int = 10


class PageRankQuery(BaseModel):
    top_n: int = 20


# ── Routes ───────────────────────────────────────────────────────

@router.get("/analyze", response_model=AnalyzeResponse)
async def analyze(reanalyze: bool = Query(False, description="Force reanalysis")):
    """Analyze the project and build the dependency graph."""
    server = get_server()
    graph = server.ensure_graph(reanalyze=reanalyze)
    return AnalyzeResponse(
        node_count=graph.node_count,
        edge_count=graph.edge_count,
        status="ok",
        message=f"Graph built with {graph.node_count} nodes and {graph.edge_count} edges",
    )


@router.get("/graph")
async def get_graph(reanalyze: bool = Query(False)):
    """Get the full dependency graph."""
    server = get_server()
    return server.handle_tool_call("get_dependency_graph", {"reanalyze": reanalyze})


@router.post("/callers")
async def get_callers(query: FileQuery):
    """Get all files that depend on the given file."""
    server = get_server()
    return server.handle_tool_call("get_callers", {"filepath": query.filepath})


@router.post("/callees")
async def get_callees(query: FileQuery):
    """Get all files that the given file depends on."""
    server = get_server()
    return server.handle_tool_call("get_callees", {"filepath": query.filepath})


@router.post("/impact")
async def impact_analysis(query: ImpactQuery):
    """Analyze the impact of changes to a file (transitive dependents)."""
    server = get_server()
    return server.handle_tool_call(
        "impact_analysis",
        {"filepath": query.filepath, "max_depth": query.max_depth},
    )


@router.get("/orphans")
async def find_orphans():
    """Find files with no dependents."""
    server = get_server()
    return server.handle_tool_call("find_orphans", {})


@router.get("/leaves")
async def find_leaves():
    """Find files with no dependencies."""
    server = get_server()
    return server.handle_tool_call("find_leaves", {})


@router.get("/pagerank")
async def pagerank(top_n: int = Query(20, description="Number of top results")):
    """Compute PageRank scores for all files."""
    server = get_server()
    return server.handle_tool_call("pagerank", {"top_n": top_n})


@router.get("/export/mermaid")
async def export_mermaid():
    """Export the dependency graph as Mermaid.js flowchart."""
    server = get_server()
    return server.handle_tool_call("export_mermaid", {})


@router.get("/export/d3")
async def export_d3():
    """Export as D3.js force-directed graph JSON."""
    server = get_server()
    return server.handle_tool_call("export_d3", {})


@router.post("/module")
async def module_info(query: FileQuery):
    """Get detailed information about a specific module."""
    server = get_server()
    return server.handle_tool_call("module_info", {"filepath": query.filepath})
