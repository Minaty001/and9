"""
AND9 — Dependency Graph (Graph Data Structure).

Pure-Python directed graph for dependency analysis.
Implements PageRank, transitive closure (impact analysis),
shortest paths, and community detection without external
dependencies.

Used by the DependencyAnalyzer to model code dependencies.
"""

import logging
from collections import deque
from typing import Any, Optional

logger = logging.getLogger(__name__)


class DependencyGraph:
    """A directed, weighted dependency graph.

    Nodes represent files or modules. Edges represent dependency
    relationships (imports, function calls, class inheritance).
    """

    def __init__(self):
        self._nodes: dict[str, dict[str, Any]] = {}
        self._edges: dict[str, dict[str, float]] = {}
        self._reverse_edges: dict[str, dict[str, float]] = {}

    # ── Node Operations ──────────────────────────────────────────

    def add_node(self, node_id: str, **attrs) -> None:
        """Add or update a node with optional metadata."""
        if node_id not in self._nodes:
            self._nodes[node_id] = {"id": node_id}
            self._edges[node_id] = {}
            self._reverse_edges[node_id] = {}
        self._nodes[node_id].update(attrs)

    def remove_node(self, node_id: str) -> None:
        """Remove a node and all its edges."""
        self._nodes.pop(node_id, None)
        out_edges = self._edges.pop(node_id, {})
        for target in out_edges:
            self._reverse_edges.get(target, {}).pop(node_id, None)
        for source in list(self._reverse_edges.get(node_id, {})):
            self._edges.get(source, {}).pop(node_id, None)
        self._reverse_edges.pop(node_id, None)

    def has_node(self, node_id: str) -> bool:
        return node_id in self._nodes

    def get_node(self, node_id: str) -> Optional[dict]:
        return self._nodes.get(node_id)

    def get_nodes(self) -> dict[str, dict]:
        return dict(self._nodes)

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    # ── Edge Operations ──────────────────────────────────────────

    def add_edge(self, source: str, target: str,
                 weight: float = 1.0, edge_type: str = "import") -> None:
        """Add a directed edge from source to target.

        Args:
            source: The depending node (importer).
            target: The depended node (importee).
            weight: Edge weight (default 1.0).
            edge_type: Type of dependency ('import', 'call', 'inherit', etc.).
        """
        if source not in self._nodes:
            self.add_node(source)
        if target not in self._nodes:
            self.add_node(target)

        prev = self._edges[source].get(target, 0.0)
        self._edges[source][target] = prev + weight
        prev_rev = self._reverse_edges[target].get(source, 0.0)
        self._reverse_edges[target][source] = prev_rev + weight

        # Store edge type on nodes
        types = self._nodes[source].setdefault("edge_types", {})
        types[target] = edge_type

    def remove_edge(self, source: str, target: str) -> None:
        self._edges.get(source, {}).pop(target, None)
        self._reverse_edges.get(target, {}).pop(source, None)

    def has_edge(self, source: str, target: str) -> bool:
        return target in self._edges.get(source, {})

    def edge_weight(self, source: str, target: str) -> float:
        return self._edges.get(source, {}).get(target, 0.0)

    @property
    def edge_count(self) -> int:
        return sum(len(outs) for outs in self._edges.values())

    # ── Queries ──────────────────────────────────────────────────

    def get_dependents(self, node_id: str) -> dict[str, float]:
        """Who depends on this node? (reverse edges / callers).

        Returns dict of {source_node: weight}.
        """
        return dict(self._reverse_edges.get(node_id, {}))

    def get_dependencies(self, node_id: str) -> dict[str, float]:
        """What does this node depend on? (outgoing edges / callees).

        Returns dict of {target_node: weight}.
        """
        return dict(self._edges.get(node_id, {}))

    def get_transitive_dependents(self, node_id: str,
                                   max_depth: int = 10) -> dict[str, int]:
        """Get all transitive dependents of a node (impact analysis).

        Returns dict of {node: depth}.
        """
        visited = {}
        queue = deque([(node_id, 0)])
        while queue:
            current, depth = queue.popleft()
            if depth >= max_depth:
                continue
            for source in self._reverse_edges.get(current, {}):
                new_depth = depth + 1
                if source not in visited or visited[source] > new_depth:
                    visited[source] = new_depth
                    queue.append((source, new_depth))
        return visited

    def get_transitive_dependencies(self, node_id: str,
                                     max_depth: int = 10) -> dict[str, int]:
        """Get all transitive dependencies of a node.

        Returns dict of {node: depth}.
        """
        visited = {}
        queue = deque([(node_id, 0)])
        while queue:
            current, depth = queue.popleft()
            if depth >= max_depth:
                continue
            for target in self._edges.get(current, {}):
                new_depth = depth + 1
                if target not in visited or visited[target] > new_depth:
                    visited[target] = new_depth
                    queue.append((target, new_depth))
        return visited

    def find_orphans(self) -> list[str]:
        """Find nodes with no incoming edges (no one depends on them)."""
        orphans = []
        for node_id in self._nodes:
            if not self._reverse_edges.get(node_id):
                orphans.append(node_id)
        return sorted(orphans)

    def find_leaves(self) -> list[str]:
        """Find nodes that depend on nothing (no outgoing edges)."""
        leaves = []
        for node_id in self._nodes:
            if not self._edges.get(node_id):
                leaves.append(node_id)
        return sorted(leaves)

    def find_shortest_path(self, source: str, target: str) -> Optional[list[str]]:
        """BFS shortest path from source to target."""
        if source not in self._nodes or target not in self._nodes:
            return None
        if source == target:
            return [source]

        visited = {source}
        queue = deque([(source, [source])])
        while queue:
            current, path = queue.popleft()
            for neighbor in self._edges.get(current, {}):
                if neighbor == target:
                    return path + [neighbor]
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        return None

    def pagerank(self, damping: float = 0.85,
                 max_iter: int = 100, tol: float = 1e-6) -> dict[str, float]:
        """Compute PageRank scores for all nodes.

        Args:
            damping: Damping factor (default 0.85).
            max_iter: Maximum iterations.
            tol: Convergence tolerance.

        Returns:
            Dict of {node_id: pagerank_score}.
        """
        n = self.node_count
        if n == 0:
            return {}

        scores = {nid: 1.0 / n for nid in self._nodes}
        dangling = [nid for nid in self._nodes if not self._edges.get(nid)]

        for _ in range(max_iter):
            prev = scores.copy()
            sum(prev.values())
            dangling_contrib = sum(prev[nid] for nid in dangling) / n if n else 0

            for nid in self._nodes:
                inbound = 0.0
                for source in self._reverse_edges.get(nid, {}):
                    out_degree = len(self._edges.get(source, {}))
                    if out_degree > 0:
                        inbound += prev[source] / out_degree
                scores[nid] = (1 - damping) / n + damping * (inbound + dangling_contrib)

            # Check convergence
            diff = sum(abs(scores[nid] - prev[nid]) for nid in self._nodes)
            if diff < tol:
                break

        return scores

    def to_dict(self) -> dict:
        """Serialize the full graph to a dict."""
        nodes = {}
        for nid, attrs in self._nodes.items():
            nodes[nid] = {
                **attrs,
                "dependents": len(self._reverse_edges.get(nid, {})),
                "dependencies": len(self._edges.get(nid, {})),
                "dependent_list": list(self._reverse_edges.get(nid, {})),
                "dependency_list": list(self._edges.get(nid, {})),
            }

        edges = []
        for source in self._edges:
            for target, weight in self._edges[source].items():
                etype = self._nodes.get(source, {}).get("edge_types", {}).get(target, "import")
                edges.append({
                    "source": source,
                    "target": target,
                    "weight": weight,
                    "type": etype,
                })

        return {
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "nodes": nodes,
            "edges": edges,
        }

    def to_mermaid(self) -> str:
        """Export as Mermaid.js flowchart."""
        lines = ["flowchart LR"]
        for source in self._edges:
            for target, weight in self._edges[source].items():
                label = f"|{weight:.1f}|" if weight != 1.0 else ""
                # Sanitize node IDs for Mermaid
                src = source.replace("/", "_").replace(".", "_").replace("-", "_")
                tgt = target.replace("/", "_").replace(".", "_").replace("-", "_")
                lines.append(f"    {src} -->{label} {tgt}")
        return "\n".join(lines)

    def to_d3_json(self) -> dict:
        """Export as D3.js force-directed graph JSON."""
        nodes = []
        for nid, attrs in self._nodes.items():
            nodes.append({
                "id": nid,
                "group": attrs.get("module", "unknown"),
                "pagerank": attrs.get("pagerank", 0),
                "type": attrs.get("type", "module"),
            })

        links = []
        for source in self._edges:
            for target, weight in self._edges[source].items():
                etype = self._nodes.get(source, {}).get("edge_types", {}).get(target, "import")
                links.append({
                    "source": source,
                    "target": target,
                    "weight": weight,
                    "type": etype,
                })

        return {"nodes": nodes, "links": links}
