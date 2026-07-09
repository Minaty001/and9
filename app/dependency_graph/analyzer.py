"""
AND9 — Dependency Analyzer (AST-based code analysis).

Parses Python source files using the built-in `ast` module to extract:

  - Import dependencies (direct and transitive)
  - Function definitions and calls
  - Class definitions and inheritance
  - Module-level constants and variables

Builds a DependencyGraph that can be queried via MCP tools.

Zero external dependencies. Supports Python 3.11+.
"""

import ast
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

from app.dependency_graph.graph import DependencyGraph

logger = logging.getLogger(__name__)

# File extensions to analyze
PYTHON_EXTENSIONS = {".py"}
# Directories to skip
SKIP_DIRS = {
    "__pycache__", ".git", ".pytest_cache", ".mypy_cache",
    ".tox", ".venv", "venv", "env", "node_modules",
    "__pycache__", "*.egg-info", ".eggs",
}


class FileVisitor(ast.NodeVisitor):
    """AST visitor that extracts dependency information from a single file."""

    def __init__(self, filepath: str, module_path: str):
        self.filepath = filepath
        self.module_path = module_path
        self.imports: list[str] = []
        self.functions: list[dict] = []
        self.classes: list[dict] = []
        self.calls: list[str] = []
        self.inheritance: list[str] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        for alias in node.names:
            full_import = f"{module}.{alias.name}" if module else alias.name
            self.imports.append(full_import)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.functions.append({
            "name": node.name,
            "lineno": node.lineno,
            "end_lineno": getattr(node, "end_lineno", node.lineno),
            "decorators": [
                self._get_call_name(d) for d in node.decorator_list
            ],
            "docstring": ast.get_docstring(node) or "",
        })
        # Walk body for calls inside this function
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                call_name = self._get_call_name(child.func)
                if call_name:
                    self.calls.append(call_name)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.visit_FunctionDef(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        bases = []
        for base in node.bases:
            base_name = self._get_call_name(base)
            if base_name:
                bases.append(base_name)
                self.inheritance.append(base_name)
        self.classes.append({
            "name": node.name,
            "bases": bases,
            "lineno": node.lineno,
            "end_lineno": getattr(node, "end_lineno", node.lineno),
            "docstring": ast.get_docstring(node) or "",
            "methods": [
                {"name": item.name, "lineno": item.lineno}
                for item in ast.iter_child_nodes(node)
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
            ],
        })
        # Walk for calls inside the class
        for child in ast.walk(node):
            if isinstance(child, ast.Call) and not isinstance(
                getattr(child, "func", None), ast.Attribute
            ):
                pass  # Skip attribute calls inside class
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        call_name = self._get_call_name(node.func)
        if call_name:
            self.calls.append(call_name)
        self.generic_visit(node)

    @staticmethod
    def _get_call_name(node: ast.AST) -> Optional[str]:
        """Extract the full name of a called function/class."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name):
                return f"{node.value.id}.{node.attr}"
            elif isinstance(node.value, ast.Attribute):
                inner = FileVisitor._get_call_name(node.value)
                return f"{inner}.{node.attr}" if inner else None
            return node.attr
        elif isinstance(node, ast.Subscript):
            return FileVisitor._get_call_name(node.value)
        return None


class DependencyAnalyzer:
    """Analyzes Python source code and builds a dependency graph.

    Usage:
        analyzer = DependencyAnalyzer("/path/to/project")
        graph = analyzer.analyze()
        print(graph.to_dict())
    """

    def __init__(self, root_path: str,
                 include_patterns: Optional[list[str]] = None,
                 exclude_patterns: Optional[list[str]] = None,
                 max_workers: int = 4):
        self.root_path = os.path.abspath(root_path)
        self.include_patterns = include_patterns
        self.exclude_patterns = exclude_patterns
        self.max_workers = max_workers
        self._graph = DependencyGraph()

    def analyze(self) -> DependencyGraph:
        """Run full dependency analysis on the project.

        Returns:
            Populated DependencyGraph.
        """
        logger.info("Analyzing dependencies in %s", self.root_path)
        self._graph = DependencyGraph()

        # 1. Find all Python files
        py_files = self._find_python_files()
        logger.info("Found %d Python files", len(py_files))

        if not py_files:
            return self._graph

        # 2. Parse each file in parallel
        file_data: dict[str, dict] = {}
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            fut_to_path = {
                executor.submit(self._parse_file, fp): fp
                for fp in py_files
            }
            for future in as_completed(fut_to_path):
                fp = fut_to_path[future]
                try:
                    data = future.result()
                    if data:
                        file_data[fp] = data
                except Exception as e:
                    logger.debug("Error parsing %s: %s", fp, e)

        logger.info("Parsed %d files successfully", len(file_data))

        # 3. Add nodes to graph
        for fp, data in file_data.items():
            rel_path = self._relative_path(fp)
            module_name = self._path_to_module(rel_path)
            self._graph.add_node(
                rel_path,
                module=module_name,
                type="module",
                functions=data.get("functions", []),
                classes=data.get("classes", []),
                file_size=os.path.getsize(fp),
                line_count=data.get("line_count", 0),
            )

        # 4. Add edges for imports
        for fp, data in file_data.items():
            rel_path = self._relative_path(fp)
            for imp in data.get("imports", []):
                target = self._resolve_import(imp, file_data)
                if target and target != rel_path:
                    self._graph.add_edge(rel_path, target, weight=1.0, edge_type="import")
                    logger.debug("  import: %s -> %s", rel_path, target)

        # 5. Add edges for function calls (across files)
        for fp, data in file_data.items():
            rel_path = self._relative_path(fp)
            for call_name in data.get("calls", []):
                target = self._resolve_call_target(call_name, file_data)
                if target and target != rel_path:
                    self._graph.add_edge(rel_path, target, weight=0.5, edge_type="call")

        # 6. Add edges for class inheritance
        for fp, data in file_data.items():
            rel_path = self._relative_path(fp)
            for base in data.get("inheritance", []):
                target = self._resolve_call_target(base, file_data)
                if target and target != rel_path:
                    self._graph.add_edge(rel_path, target, weight=0.8, edge_type="inherit")

        logger.info("Graph built: %d nodes, %d edges",
                    self._graph.node_count, self._graph.edge_count)
        return self._graph

    def _find_python_files(self) -> list[str]:
        """Recursively find all Python files under root_path."""
        py_files = []
        root = Path(self.root_path)

        for entry in root.rglob("*.py"):
            # Skip directories
            if any(skip in entry.parts for skip in SKIP_DIRS):
                continue
            fp = str(entry)
            # Apply include/exclude patterns if specified
            if self.include_patterns:
                if not any(entry.match(p) for p in self.include_patterns):
                    continue
            if self.exclude_patterns:
                if any(entry.match(p) for p in self.exclude_patterns):
                    continue
            py_files.append(fp)

        return sorted(py_files)

    def _parse_file(self, filepath: str) -> Optional[dict]:
        """Parse a single Python file and extract dependency info."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                source = f.read()

            tree = ast.parse(source, filename=filepath)
            visitor = FileVisitor(filepath, self._path_to_module(
                self._relative_path(filepath)
            ))
            visitor.visit(tree)

            return {
                "imports": self._dedupe(visitor.imports),
                "functions": visitor.functions,
                "classes": visitor.classes,
                "calls": self._dedupe(visitor.calls),
                "inheritance": self._dedupe(visitor.inheritance),
                "line_count": len(source.splitlines()),
            }
        except SyntaxError as e:
            logger.debug("Syntax error in %s: %s", filepath, e)
            return None
        except Exception as e:
            logger.debug("Error reading %s: %s", filepath, e)
            return None

    def _resolve_import(self, import_name: str,
                        file_data: dict[str, dict]) -> Optional[str]:
        """Resolve a Python import name to a file path in the project."""
        # Direct module match
        module_path = import_name.replace(".", "/")

        for fp in file_data:
            rel = self._relative_path(fp)
            mod = self._path_to_module(rel)

            # Exact module match
            if mod == import_name:
                return rel

            # Match module/__init__.py
            if mod == import_name and fp.endswith("__init__.py"):
                return rel
            if f"{import_name}/__init__" == mod:
                return rel

            # Parent module match (from x import y)
            parent = ".".join(import_name.split(".")[:-1])
            if parent and mod == parent:
                return rel

            # Check if this file is the module file
            module_path + ".py"
            if mod == import_name:
                return rel

            # Fuzzy: the file's module name starts with the import
            if mod.startswith(import_name + "."):
                return rel

        return None

    def _resolve_call_target(self, call_name: str,
                              file_data: dict[str, dict]) -> Optional[str]:
        """Resolve a function call name to a file that defines it."""
        for fp, data in file_data.items():
            rel = self._relative_path(fp)
            # Check functions
            for func in data.get("functions", []):
                if func["name"] == call_name:
                    return rel
                full_name = f"{self._path_to_module(rel)}.{func['name']}"
                if full_name == call_name:
                    return rel
            # Check methods
            for cls in data.get("classes", []):
                for method in cls.get("methods", []):
                    full_name = f"{cls['name']}.{method['name']}"
                    if full_name == call_name:
                        return rel
                    module_full = f"{self._path_to_module(rel)}.{full_name}"
                    if module_full == call_name:
                        return rel

        return None

    @staticmethod
    def _path_to_module(rel_path: str) -> str:
        """Convert a relative file path to a Python module path."""
        mod = rel_path.replace("/", ".").replace("\\", ".")
        if mod.endswith(".py"):
            mod = mod[:-3]
        if mod.endswith(".__init__"):
            mod = mod[:-9]
        return mod

    def _relative_path(self, abs_path: str) -> str:
        """Get the relative path from root_path."""
        return os.path.relpath(abs_path, self.root_path)

    @staticmethod
    def _dedupe(items: list[str]) -> list[str]:
        """Remove duplicates while preserving order."""
        seen = set()
        result = []
        for item in items:
            if item not in seen:
                seen.add(item)
                result.append(item)
        return result
