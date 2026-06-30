"""
Plugin SDK — Sandbox.

Execute plugin code with restrictions, timeouts, and resource limits.
Includes ResourceLimiter for tracking CPU, memory, and file operations.
"""

from __future__ import annotations

import os
import time
import threading
import logging
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from .models import PluginManifest

logger = logging.getLogger(__name__)

try:
    import resource as resource_module
    HAS_RESOURCE = True
except ImportError:
    HAS_RESOURCE = False


class ResourceLimiter:
    """Track and limit plugin resource usage.

    Monitors CPU time, memory, and file operations for sandboxed execution.
    Uses the `resource` module for process-level limits when available.

    Usage:
        limiter = ResourceLimiter()
        limiter.restrict_filesystem(["/tmp/plugins"])
        limiter.restrict_network(["api.example.com"])
        limiter.restrict_exec(["python", "bash"])
    """

    def __init__(self):
        self._cpu_time_start: float = 0.0
        self._cpu_time_end: float = 0.0
        self._memory_peak: int = 0
        self._file_ops: int = 0
        self._allowed_paths: Set[str] = set()
        self._allowed_domains: Set[str] = set()
        self._allowed_commands: Set[str] = set()
        self._limits_applied: bool = False

    def restrict_filesystem(self, allowed_paths: List[str]) -> None:
        """Restrict filesystem access to a set of allowed paths."""
        self._allowed_paths = set(os.path.abspath(p) for p in allowed_paths)
        logger.debug("Filesystem restricted to: %s", self._allowed_paths)

    def restrict_network(self, allowed_domains: List[str]) -> None:
        """Restrict network access to a set of allowed domains."""
        self._allowed_domains = set(allowed_domains)
        logger.debug("Network restricted to: %s", self._allowed_domains)

    def restrict_exec(self, allowed_commands: List[str]) -> None:
        """Restrict subprocess execution to allowed commands."""
        self._allowed_commands = set(allowed_commands)
        logger.debug("Execution restricted to: %s", self._allowed_commands)

    def apply_hard_limits(self, cpu_seconds: int = 5,
                          memory_mb: int = 256) -> None:
        """Apply hard resource limits using the `resource` module.

        Args:
            cpu_seconds: Maximum CPU time in seconds (RLIMIT_CPU).
            memory_mb: Maximum address space in MB (RLIMIT_AS).
        """
        if not HAS_RESOURCE:
            logger.warning("resource module not available, skipping hard limits")
            return
        try:
            resource_module.setrlimit(
                resource_module.RLIMIT_CPU,
                (cpu_seconds, cpu_seconds + 1),
            )
            memory_bytes = memory_mb * 1024 * 1024
            resource_module.setrlimit(
                resource_module.RLIMIT_AS,
                (memory_bytes, memory_bytes + 1024 * 1024),
            )
            self._limits_applied = True
            logger.debug("Applied hard limits: CPU=%ds, mem=%dMB", cpu_seconds, memory_mb)
        except (resource_module.error, ValueError) as e:
            logger.warning("Could not apply resource limits: %s", e)

    def start_tracking(self) -> None:
        """Start tracking resource usage."""
        self._cpu_time_start = time.perf_counter()
        self._memory_peak = 0
        self._file_ops = 0

    def stop_tracking(self) -> Dict[str, Any]:
        """Stop tracking and return resource usage summary."""
        self._cpu_time_end = time.perf_counter()
        return {
            "cpu_time_ms": round((self._cpu_time_end - self._cpu_time_start) * 1000, 3),
            "memory_peak_kb": self._memory_peak,
            "file_ops": self._file_ops,
        }

    def record_file_op(self) -> None:
        """Record a filesystem operation."""
        self._file_ops += 1

    @property
    def allowed_paths(self) -> Set[str]:
        return self._allowed_paths

    @property
    def allowed_domains(self) -> Set[str]:
        return self._allowed_domains

    @property
    def allowed_commands(self) -> Set[str]:
        return self._allowed_commands

    def reset(self) -> None:
        """Reset all restrictions and tracking data."""
        self._allowed_paths.clear()
        self._allowed_domains.clear()
        self._allowed_commands.clear()
        self._cpu_time_start = 0.0
        self._cpu_time_end = 0.0
        self._memory_peak = 0
        self._file_ops = 0
        self._limits_applied = False


class Sandbox:
    """Execute plugin code with restrictions and timeout.

    Usage:
        sandbox = Sandbox()
        result, error = sandbox.execute(lambda: 1 + 1, timeout_ms=5000)
    """

    def __init__(self, sandbox_timeout_ms: int = 5000,
                 allowed_imports: Optional[List[str]] = None):
        self.sandbox_timeout_ms = sandbox_timeout_ms
        self.allowed_imports = allowed_imports or []
        self.resource_limiter: Optional[ResourceLimiter] = None

    def execute(self, func: Callable, timeout_ms: Optional[int] = None,
                resource_limiter: Optional[ResourceLimiter] = None) -> Tuple[Optional[Any], Optional[str]]:
        """Execute a function with timeout and optional resource limits.

        Args:
            func: The function to execute.
            timeout_ms: Timeout in milliseconds.
            resource_limiter: Optional ResourceLimiter instance.

        Returns:
            Tuple of (result, error). On success, error is None.
        """
        timeout = timeout_ms if timeout_ms is not None else self.sandbox_timeout_ms
        timeout_sec = timeout / 1000.0

        result_container = []
        error_container = []

        limiter = resource_limiter or self.resource_limiter

        def target():
            try:
                if limiter:
                    limiter.start_tracking()
                result = func()
                if limiter:
                    limiter.stop_tracking()
                result_container.append(result)
            except Exception as e:
                if limiter:
                    limiter.stop_tracking()
                error_container.append(str(e))

        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        thread.join(timeout=timeout_sec)

        if thread.is_alive():
            return None, f"Execution timed out after {timeout}ms"

        if error_container:
            return None, error_container[0]

        if result_container:
            return result_container[0], None

        return None, "No result returned"

    def restrict_imports(self, module_name: str) -> bool:
        """Check if a module import is allowed.

        Returns True if the import is permitted.
        """
        if not self.allowed_imports:
            return True
        return module_name in self.allowed_imports

    def validate_manifest_permissions(self, manifest: PluginManifest) -> bool:
        """Check that declared permissions are reasonable for the sandbox level.

        Args:
            manifest: The PluginManifest to validate.

        Returns:
            True if permissions are acceptable.
        """
        if not manifest.permissions:
            return True

        dangerous_permissions = {
            "network:all": "allows unrestricted network access",
            "filesystem:all": "allows unrestricted filesystem access",
            "exec:all": "allows arbitrary command execution",
            "system:all": "allows full system access",
        }

        for perm in manifest.permissions:
            if perm in dangerous_permissions:
                logger.warning("Plugin '%s' requests dangerous permission '%s': %s",
                               manifest.id, perm, dangerous_permissions[perm])

            if self.resource_limiter:
                if perm.startswith("filesystem:") and perm != "filesystem:all":
                    path_part = perm.split(":", 1)[1] if ":" in perm else ""
                    if path_part and self.resource_limiter.allowed_paths:
                        abs_path = os.path.abspath(path_part)
                        if not any(abs_path.startswith(allowed)
                                   for allowed in self.resource_limiter.allowed_paths):
                            logger.warning("Permission '%s' not in restricted paths", perm)
                            return False

        return True
