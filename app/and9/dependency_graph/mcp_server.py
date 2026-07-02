"""
AND9 — Dependency Graph MCP Server.

Implements the Model Context Protocol (MCP) as a lightweight JSON-RPC 2.0
server over stdio. Provides tools for:

  - get_dependency_graph — Full project dependency graph
  - get_callers — Who imports/calls a given file
  - get_callees — What a given file imports/calls
  - impact_analysis — Transitive dependency impact
  - find_orphans — Files with no dependents
  - find_leaves — Files with no dependencies
  - pagerank — PageRank scores for all files
  - export_mermaid — Export graph as Mermaid.js
  - export_d3 — Export graph as D3.js JSON

Usage:
    from app.and9.dependency_graph.mcp_server import DependencyGraphMCPServer
    server = DependencyGraphMCPServer("/path/to/project")
    server.run()  # Reads from stdin, writes to stdout
"""

import json
import logging
import sys
import traceback
from typing import Any, Optional

from app.and9.dependency_graph.analyzer import DependencyAnalyzer
from app.and9.dependency_graph.graph import DependencyGraph

logger = logging.getLogger(__name__)


class DependencyGraphMCPServer:
    """Lightweight MCP server for dependency graph analysis.

    Implements the Model Context Protocol (JSON-RPC 2.0 over stdio).
    Caches the analyzed graph for subsequent queries.
    """

    def __init__(self, root_path: str,
                 include_patterns: Optional[list[str]] = None,
                 exclude_patterns: Optional[list[str]] = None):
        self.root_path = root_path
        self.include_patterns = include_patterns
        self.exclude_patterns = exclude_patterns
        self._graph: Optional[DependencyGraph] = None
        self._analyzer = DependencyAnalyzer(
            root_path=root_path,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
        )

    # ── Tool Definitions ─────────────────────────────────────────

    TOOLS = [
        {
            "name": "get_dependency_graph",
            "description": "Get the full project dependency graph",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "reanalyze": {
                        "type": "boolean",
                        "description": "Force reanalysis of the project",
                        "default": False,
                    }
                },
            },
        },
        {
            "name": "get_callers",
            "description": "Get all files that depend on a given file (who imports/calls it)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Relative file path (e.g. 'app/and9/dialogue_manager/dialogue_manager.py')",
                    }
                },
                "required": ["filepath"],
            },
        },
        {
            "name": "get_callees",
            "description": "Get all files that a given file depends on (what it imports/calls)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Relative file path",
                    }
                },
                "required": ["filepath"],
            },
        },
        {
            "name": "impact_analysis",
            "description": "Find all files transitively affected by changes to a given file",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Relative file path",
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "Maximum depth of transitive traversal",
                        "default": 10,
                    },
                },
                "required": ["filepath"],
            },
        },
        {
            "name": "find_orphans",
            "description": "Find files that have no dependents (no one imports/calls them)",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "find_leaves",
            "description": "Find files that have no dependencies (import nothing from the project)",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "pagerank",
            "description": "Compute PageRank scores for all files in the project",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "top_n": {
                        "type": "integer",
                        "description": "Return only top N results (0 = all)",
                        "default": 20,
                    }
                },
            },
        },
        {
            "name": "export_mermaid",
            "description": "Export the dependency graph as Mermaid.js flowchart syntax",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "export_d3",
            "description": "Export the dependency graph as D3.js force-directed graph JSON",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "module_info",
            "description": "Get detailed information about a specific module/file",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Relative file path",
                    }
                },
                "required": ["filepath"],
            },
        },
    ]

    # ── Lifecycle ────────────────────────────────────────────────

    def ensure_graph(self, reanalyze: bool = False) -> DependencyGraph:
        """Get the dependency graph, (re)analyzing if needed."""
        if self._graph is None or reanalyze:
            logger.info("Analyzing project: %s", self.root_path)
            self._graph = self._analyzer.analyze()
        return self._graph

    # ── Tool Handlers ────────────────────────────────────────────

    def handle_tool_call(self, tool_name: str, arguments: dict) -> Any:
        """Route a tool call to the appropriate handler."""
        handlers = {
            "get_dependency_graph": self._handle_get_graph,
            "get_callers": self._handle_get_callers,
            "get_callees": self._handle_get_callees,
            "impact_analysis": self._handle_impact_analysis,
            "find_orphans": self._handle_find_orphans,
            "find_leaves": self._handle_find_leaves,
            "pagerank": self._handle_pagerank,
            "export_mermaid": self._handle_export_mermaid,
            "export_d3": self._handle_export_d3,
            "module_info": self._handle_module_info,
        }
        handler = handlers.get(tool_name)
        if not handler:
            raise ValueError(f"Unknown tool: {tool_name}")
        return handler(**arguments)

    def _handle_get_graph(self, reanalyze: bool = False) -> dict:
        graph = self.ensure_graph(reanalyze)
        return graph.to_dict()

    def _handle_get_callers(self, filepath: str) -> dict:
        graph = self.ensure_graph()
        dependents = graph.get_dependents(filepath)
        return {
            "file": filepath,
            "caller_count": len(dependents),
            "callers": dependents,
        }

    def _handle_get_callees(self, filepath: str) -> dict:
        graph = self.ensure_graph()
        dependencies = graph.get_dependencies(filepath)
        return {
            "file": filepath,
            "dependency_count": len(dependencies),
            "dependencies": dependencies,
        }

    def _handle_impact_analysis(self, filepath: str,
                                 max_depth: int = 10) -> dict:
        graph = self.ensure_graph()
        transitive = graph.get_transitive_dependents(filepath, max_depth)
        return {
            "file": filepath,
            "max_depth": max_depth,
            "affected_count": len(transitive),
            "affected_files": transitive,
        }

    def _handle_find_orphans(self) -> dict:
        graph = self.ensure_graph()
        orphans = graph.find_orphans()
        return {"orphan_count": len(orphans), "orphans": orphans}

    def _handle_find_leaves(self) -> dict:
        graph = self.ensure_graph()
        leaves = graph.find_leaves()
        return {"leaf_count": len(leaves), "leaves": leaves}

    def _handle_pagerank(self, top_n: int = 20) -> dict:
        graph = self.ensure_graph()
        scores = graph.pagerank()
        sorted_scores = sorted(scores.items(), key=lambda x: -x[1])
        if top_n > 0:
            sorted_scores = sorted_scores[:top_n]
        return {
            "total_nodes": len(scores),
            "top_n": top_n if top_n > 0 else len(scores),
            "scores": {k: round(v, 6) for k, v in sorted_scores},
        }

    def _handle_export_mermaid(self) -> str:
        graph = self.ensure_graph()
        return graph.to_mermaid()

    def _handle_export_d3(self) -> dict:
        graph = self.ensure_graph()
        return graph.to_d3_json()

    def _handle_module_info(self, filepath: str) -> Optional[dict]:
        graph = self.ensure_graph()
        node = graph.get_node(filepath)
        if not node:
            return {"error": f"File not found in graph: {filepath}"}
        callers = graph.get_dependents(filepath)
        callees = graph.get_dependencies(filepath)
        transitive_callers = graph.get_transitive_dependents(filepath)
        return {
            "file": filepath,
            "module": node.get("module", ""),
            "functions": node.get("functions", []),
            "classes": node.get("classes", []),
            "line_count": node.get("line_count", 0),
            "file_size": node.get("file_size", 0),
            "callers": callers,
            "callees": callees,
            "transitive_impact_count": len(transitive_callers),
        }

    # ── MCP Protocol ─────────────────────────────────────────────

    def handle_request(self, request: dict) -> Optional[dict]:
        """Handle a single JSON-RPC 2.0 request."""
        req_id = request.get("id")
        method = request.get("method", "")
        params = request.get("params", {})

        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": self.TOOLS},
            }

        elif method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            try:
                result = self.handle_tool_call(tool_name, arguments)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(result, indent=2, default=str),
                            }
                        ],
                    },
                }
            except Exception as e:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32000,
                        "message": str(e),
                        "data": traceback.format_exc(),
                    },
                }

        elif method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {},
                    },
                    "serverInfo": {
                        "name": "and9-dependency-graph",
                        "version": "1.0.0",
                    },
                },
            }

        elif method == "notifications/initialized":
            return None  # No response for notifications

        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}",
                },
            }

    def run(self, input_stream=None, output_stream=None) -> None:
        """Run the MCP server, reading JSON-RPC from stdin and writing to stdout.

        Args:
            input_stream: Input stream (defaults to sys.stdin).
            output_stream: Output stream (defaults to sys.stdout).
        """
        if input_stream is None:
            input_stream = sys.stdin
        if output_stream is None:
            output_stream = sys.stdout

        logger.info("Dependency Graph MCP server starting (root=%s)", self.root_path)

        # Pre-analyze on startup
        try:
            self.ensure_graph()
            logger.info("Pre-analysis complete: %d nodes, %d edges",
                        self._graph.node_count, self._graph.edge_count)
        except Exception as e:
            logger.warning("Pre-analysis failed (will retry on first query): %s", e)

        for line in input_stream:
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
                response = self.handle_request(request)
                if response is not None:
                    output_stream.write(json.dumps(response) + "\n")
                    output_stream.flush()
            except json.JSONDecodeError:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": "Parse error"},
                }
                output_stream.write(json.dumps(error_response) + "\n")
                output_stream.flush()
            except Exception as e:
                logger.error("Unhandled error: %s", e)
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32603, "message": str(e)},
                }
                output_stream.write(json.dumps(error_response) + "\n")
                output_stream.flush()
