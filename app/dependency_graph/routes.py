"""
AND9 — Dependency Graph API Routes.

FastAPI/Flask-compatible routes exposing the dependency graph
analyzer directly (no MCP layer).
"""

import logging
import os
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.dependency_graph.analyzer import DependencyAnalyzer
from app.dependency_graph.graph import DependencyGraph

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dependency-graph", tags=["dependency-graph"])

# Global graph cache (initialized lazily)
_graph: Optional[DependencyGraph] = None
_analyzer: Optional[DependencyAnalyzer] = None


def _ensure_graph(reanalyze: bool = False) -> DependencyGraph:
    """Get or create the dependency graph."""
    global _graph, _analyzer
    if _graph is None or reanalyze:
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        _analyzer = DependencyAnalyzer(root_path=root)
        _graph = _analyzer.analyze()
    return _graph


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
    graph = _ensure_graph(reanalyze)
    return AnalyzeResponse(
        node_count=graph.node_count,
        edge_count=graph.edge_count,
        status="ok",
        message=f"Graph built with {graph.node_count} nodes and {graph.edge_count} edges",
    )


@router.get("/graph")
async def get_graph(reanalyze: bool = Query(False)):
    """Get the full dependency graph."""
    graph = _ensure_graph(reanalyze)
    return graph.to_dict()


@router.post("/callers")
async def get_callers(query: FileQuery):
    """Get all files that depend on the given file."""
    graph = _ensure_graph()
    dependents = graph.get_dependents(query.filepath)
    return {
        "file": query.filepath,
        "caller_count": len(dependents),
        "callers": dependents,
    }


@router.post("/callees")
async def get_callees(query: FileQuery):
    """Get all files that the given file depends on."""
    graph = _ensure_graph()
    dependencies = graph.get_dependencies(query.filepath)
    return {
        "file": query.filepath,
        "dependency_count": len(dependencies),
        "dependencies": dependencies,
    }


@router.post("/impact")
async def impact_analysis(query: ImpactQuery):
    """Analyze the impact of changes to a file (transitive dependents)."""
    graph = _ensure_graph()
    transitive = graph.get_transitive_dependents(query.filepath, query.max_depth)
    return {
        "file": query.filepath,
        "max_depth": query.max_depth,
        "affected_count": len(transitive),
        "affected_files": transitive,
    }


@router.get("/orphans")
async def find_orphans():
    """Find files with no dependents."""
    graph = _ensure_graph()
    orphans = graph.find_orphans()
    return {"orphan_count": len(orphans), "orphans": orphans}


@router.get("/leaves")
async def find_leaves():
    """Find files with no dependencies."""
    graph = _ensure_graph()
    leaves = graph.find_leaves()
    return {"leaf_count": len(leaves), "leaves": leaves}


@router.get("/pagerank")
async def pagerank(top_n: int = Query(20, description="Number of top results")):
    """Compute PageRank scores for all files."""
    graph = _ensure_graph()
    scores = graph.pagerank()
    sorted_scores = sorted(scores.items(), key=lambda x: -x[1])
    if top_n > 0:
        sorted_scores = sorted_scores[:top_n]
    return {
        "total_nodes": len(scores),
        "top_n": top_n if top_n > 0 else len(scores),
        "scores": {k: round(v, 6) for k, v in sorted_scores},
    }


@router.get("/export/mermaid")
async def export_mermaid():
    """Export the dependency graph as Mermaid.js flowchart."""
    graph = _ensure_graph()
    return graph.to_mermaid()


@router.get("/export/d3")
async def export_d3():
    """Export as D3.js force-directed graph JSON."""
    graph = _ensure_graph()
    return graph.to_d3_json()


@router.post("/module")
async def module_info(query: FileQuery):
    """Get detailed information about a specific module."""
    graph = _ensure_graph()
    node = graph.get_node(query.filepath)
    if not node:
        return {"error": f"File not found in graph: {query.filepath}"}
    callers = graph.get_dependents(query.filepath)
    callees = graph.get_dependencies(query.filepath)
    transitive_callers = graph.get_transitive_dependents(query.filepath)
    return {
        "file": query.filepath,
        "module": node.get("module", ""),
        "functions": node.get("functions", []),
        "classes": node.get("classes", []),
        "line_count": node.get("line_count", 0),
        "file_size": node.get("file_size", 0),
        "callers": callers,
        "callees": callees,
        "transitive_impact_count": len(transitive_callers),
    }
