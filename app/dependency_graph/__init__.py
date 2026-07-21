"""
app/dependency_graph — Code dependency graph analysis.

AST-based dependency analysis.
"""

from app.dependency_graph.analyzer import DependencyAnalyzer
from app.dependency_graph.graph import DependencyGraph

__all__ = [
    "DependencyAnalyzer",
    "DependencyGraph",
]
