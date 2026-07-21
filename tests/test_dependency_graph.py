"""
Tests for the AND9 Dependency Graph Analyzer.

Covers:
  1. Graph data structure operations
  2. AST-based dependency analysis
  3. PageRank computation
  4. Impact analysis (transitive dependents)
  5. MCP server tool handlers
  6. Edge cases (empty project, single file, circular deps)
"""

import json
import os
import tempfile
import pytest

from app.dependency_graph.graph import DependencyGraph
from app.dependency_graph.analyzer import DependencyAnalyzer, FileVisitor
from app.dependency_graph.mcp_server import DependencyGraphMCPServer


# ── Helper ───────────────────────────────────────────────────────

def create_temp_py_file(dirpath: str, name: str, content: str) -> str:
    """Create a temporary Python file and return its path."""
    os.makedirs(dirpath, exist_ok=True)
    filepath = os.path.join(dirpath, name)
    with open(filepath, "w") as f:
        f.write(content)
    return filepath


SAMPLE_PROJECT = {
    "main.py": """
from utils.helper import parse_data
from models.user import User

def run():
    user = User("Alice")
    data = parse_data(user.name)
    print(data)

class App:
    def start(self):
        run()
""",
    "utils/__init__.py": "",
    "utils/helper.py": """
def parse_data(text):
    return text.upper()

def validate(value):
    return value is not None
""",
    "models/__init__.py": "",
    "models/user.py": """
from utils.helper import validate

class User:
    def __init__(self, name):
        self.name = name
        self._valid = validate(name)

    def greet(self):
        return f"Hello, {self.name}"
""",
    "controllers/__init__.py": "",
    "controllers/api.py": """
from models.user import User
from utils.helper import parse_data

def handle_request(username):
    user = User(username)
    return parse_data(user.greet())
""",
    "orphan_module.py": """
# This module has no dependents
VERSION = "1.0.0"

def utility():
    pass
""",
}


# ── Test 1: Graph Data Structure ─────────────────────────────────

class TestDependencyGraph:
    def test_add_node(self):
        g = DependencyGraph()
        g.add_node("main.py", module="main", type="module")
        assert g.has_node("main.py")
        assert g.get_node("main.py")["module"] == "main"

    def test_add_edge(self):
        g = DependencyGraph()
        g.add_node("a.py")
        g.add_node("b.py")
        g.add_edge("a.py", "b.py", weight=1.0, edge_type="import")
        assert g.has_edge("a.py", "b.py")
        assert g.edge_weight("a.py", "b.py") == 1.0

    def test_dependents_and_dependencies(self):
        g = DependencyGraph()
        g.add_edge("main.py", "utils.py")
        g.add_edge("api.py", "utils.py")
        deps = g.get_dependents("utils.py")
        assert "main.py" in deps
        assert "api.py" in deps
        assert g.get_dependencies("main.py") == {"utils.py": 1.0}

    def test_transitive_dependents(self):
        g = DependencyGraph()
        g.add_edge("a.py", "b.py")
        g.add_edge("b.py", "c.py")
        g.add_edge("d.py", "a.py")
        impact = g.get_transitive_dependents("c.py")
        assert "b.py" in impact
        assert "a.py" in impact
        assert "d.py" in impact

    def test_find_orphans(self):
        g = DependencyGraph()
        g.add_node("a.py")
        g.add_node("b.py")
        g.add_edge("a.py", "b.py")
        orphans = g.find_orphans()
        assert "a.py" in orphans  # a.py depends on b.py, but no one depends on a.py... 
        # Actually: a.py has no incoming edges because it's the source
        # b.py has incoming from a.py, so b.py is NOT an orphan
        # a.py has NO incoming edges -> orphan
        assert len(orphans) == 1

    def test_find_leaves(self):
        g = DependencyGraph()
        g.add_edge("a.py", "b.py")
        g.add_edge("b.py", "c.py")
        leaves = g.find_leaves()
        assert "c.py" in leaves  # c.py has no outgoing edges

    def test_shortest_path(self):
        g = DependencyGraph()
        g.add_edge("a.py", "b.py")
        g.add_edge("b.py", "c.py")
        g.add_edge("a.py", "c.py")
        path = g.find_shortest_path("a.py", "c.py")
        assert path == ["a.py", "c.py"]  # Direct edge is shorter

    def test_pagerank_scores(self):
        g = DependencyGraph()
        g.add_edge("a.py", "b.py")
        g.add_edge("b.py", "c.py")
        g.add_edge("c.py", "a.py")
        scores = g.pagerank()
        assert len(scores) == 3
        for nid in ("a.py", "b.py", "c.py"):
            assert nid in scores
            assert scores[nid] > 0

    def test_remove_node(self):
        g = DependencyGraph()
        g.add_edge("a.py", "b.py")
        g.add_edge("b.py", "c.py")
        g.remove_node("b.py")
        assert not g.has_node("b.py")
        assert "b.py" not in g.get_dependents("c.py")

    def test_to_mermaid(self):
        g = DependencyGraph()
        g.add_edge("main.py", "utils.py")
        g.add_edge("main.py", "models.py")
        mermaid = g.to_mermaid()
        assert "main_" in mermaid
        assert "utils_" in mermaid


# ── Test 2: AST Analyzer ─────────────────────────────────────────

class TestAnalyzer:
    def test_simple_file_analysis(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fp = create_temp_py_file(tmpdir, "test_mod.py", """
import os
import sys
from datetime import datetime

def greet(name):
    return f"Hello, {name}"

class Calculator:
    def add(self, a, b):
        return a + b
""")
            analyzer = DependencyAnalyzer(tmpdir)
            graph = analyzer.analyze()
            # Should find the file
            rel = os.path.relpath(fp, tmpdir)
            assert graph.has_node(rel), f"Node {rel} not found in graph"
            node = graph.get_node(rel)
            assert len(node.get("functions", [])) == 2  # greet + Calculator.add
            assert node["functions"][0]["name"] == "greet"
            assert len(node.get("classes", [])) == 1
            assert node["classes"][0]["name"] == "Calculator"

    def test_import_resolution(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            create_temp_py_file(tmpdir, "main.py", """
from mylib.utils import helper
import mylib.models
""")
            os.makedirs(os.path.join(tmpdir, "mylib"), exist_ok=True)
            create_temp_py_file(tmpdir, "mylib/__init__.py", "")
            create_temp_py_file(tmpdir, "mylib/utils.py", """
def helper():
    pass
""")
            create_temp_py_file(tmpdir, "mylib/models.py", """
X = 1
""")
            analyzer = DependencyAnalyzer(tmpdir)
            graph = analyzer.analyze()
            rel_main = "main.py"
            # main.py should depend on utils and models
            deps = graph.get_dependencies(rel_main)
            assert len(deps) >= 2, f"Expected >=2 dependencies, got {deps}"

    def test_empty_project(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            analyzer = DependencyAnalyzer(tmpdir)
            graph = analyzer.analyze()
            assert graph.node_count == 0
            assert graph.edge_count == 0

    def test_single_file_no_deps(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            create_temp_py_file(tmpdir, "standalone.py", """
X = 42
print("Hello")
""")
            analyzer = DependencyAnalyzer(tmpdir)
            graph = analyzer.analyze()
            assert graph.node_count == 1
            assert graph.edge_count == 0

    def test_project_analysis(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            for path, content in SAMPLE_PROJECT.items():
                full_path = os.path.join(tmpdir, path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, "w") as f:
                    f.write(content)

            analyzer = DependencyAnalyzer(tmpdir)
            graph = analyzer.analyze()
            assert graph.node_count >= 5
            assert graph.edge_count >= 3

    def test_file_visitor_imports(self):
        import ast
        source = "import os\nimport sys\nfrom typing import Optional\n"
        tree = ast.parse(source)
        visitor = FileVisitor("test.py", "test")
        visitor.visit(tree)
        assert "os" in visitor.imports
        assert "sys" in visitor.imports
        assert "typing.Optional" in visitor.imports

    def test_file_visitor_functions(self):
        import ast
        source = """
def add(a, b):
    return a + b

async def fetch(url):
    return None
"""
        tree = ast.parse(source)
        visitor = FileVisitor("test.py", "test")
        visitor.visit(tree)
        names = [f["name"] for f in visitor.functions]
        assert "add" in names
        assert "fetch" in names

    def test_file_visitor_classes(self):
        import ast
        source = """
class Animal:
    def speak(self):
        pass

class Dog(Animal):
    def bark(self):
        pass
"""
        tree = ast.parse(source)
        visitor = FileVisitor("test.py", "test")
        visitor.visit(tree)
        names = [c["name"] for c in visitor.classes]
        assert "Animal" in names
        assert "Dog" in names
        # Dog inherits from Animal
        dog = [c for c in visitor.classes if c["name"] == "Dog"][0]
        assert "Animal" in dog.get("bases", [])


# ── Test 3: MCP Server ──────────────────────────────────────────

class TestMCPServer:
    def test_tools_list(self):
        server = DependencyGraphMCPServer("/tmp")
        resp = server.handle_request({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {},
        })
        assert resp is not None
        assert "result" in resp
        assert "tools" in resp["result"]
        tool_names = [t["name"] for t in resp["result"]["tools"]]
        assert "get_dependency_graph" in tool_names
        assert "get_callers" in tool_names
        assert "get_callees" in tool_names
        assert "impact_analysis" in tool_names
        assert "find_orphans" in tool_names
        assert "pagerank" in tool_names
        assert "module_info" in tool_names

    def test_initialize(self):
        server = DependencyGraphMCPServer("/tmp")
        resp = server.handle_request({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {},
        })
        assert resp is not None
        assert resp["result"]["serverInfo"]["name"] == "and9-dependency-graph"

    def test_unknown_method(self):
        server = DependencyGraphMCPServer("/tmp")
        resp = server.handle_request({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "unknown_method",
            "params": {},
        })
        assert resp is not None
        assert "error" in resp
        assert resp["error"]["code"] == -32601

    def test_unknown_tool(self):
        server = DependencyGraphMCPServer("/tmp")
        resp = server.handle_request({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "nonexistent_tool",
                "arguments": {},
            },
        })
        assert resp is not None
        assert "error" in resp

    def test_tool_call_with_project(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            for path, content in SAMPLE_PROJECT.items():
                full_path = os.path.join(tmpdir, path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, "w") as f:
                    f.write(content)

            server = DependencyGraphMCPServer(tmpdir)
            # Test get_graph
            resp = server.handle_request({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "get_dependency_graph",
                    "arguments": {"reanalyze": True},
                },
            })
            assert resp is not None
            assert resp["result"]["content"][0]["type"] == "text"
            data = json.loads(resp["result"]["content"][0]["text"])
            assert data["node_count"] >= 5

            # Test find_orphans
            resp = server.handle_request({
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "find_orphans",
                    "arguments": {},
                },
            })
            data = json.loads(resp["result"]["content"][0]["text"])
            assert data["orphan_count"] >= 1  # orphan_module.py


# ── Test 4: Integration with the Project ────────────────────────

class TestProjectIntegration:
    def test_analyze_self(self):
        """Analyze the AND9 project itself."""
        project_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..")
        )
        analyzer = DependencyAnalyzer(project_root)
        graph = analyzer.analyze()
        assert graph.node_count > 0
        assert graph.edge_count >= 0
        # Should find the dialogue_manager package
        has_dm = any("dialogue_manager" in n for n in graph.get_nodes())
        assert has_dm, "Should find dialogue_manager package"

    def test_dialogue_manager_dependencies(self):
        """Check that the dialogue_manager modules are properly connected."""
        project_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..")
        )
        analyzer = DependencyAnalyzer(project_root)
        graph = analyzer.analyze()
        dm_files = [
            n for n in graph.get_nodes()
            if "dialogue_manager" in n and n.endswith(".py")
        ]
        assert len(dm_files) >= 5, f"Expected >=5 DM files, found {len(dm_files)}"


if __name__ == "__main__":
    import json
    pytest.main([__file__, "-v", "--tb=short"])
