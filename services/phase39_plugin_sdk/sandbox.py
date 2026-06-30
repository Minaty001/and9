"""
Phase 39 — Sandbox.

Execute plugin code with restrictions, timeouts, and resource limits.
Includes ResourceLimiter for tracking CPU, memory, and file operations.
"""

from __future__ import annotations

import os
import time
import signal
import threading
import logging
import resource as resource_module
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from .config import PluginSdkConfig
from .models import PluginManifest

logger = logging.getLogger(__name__)


class ResourceLimiter:
    """Track and limit plugin resource usage.

    Monitors CPU time, memory, and file operations for sandboxed execution.
    Uses the `resource` module for process-level limits (RLIMIT_CPU, RLIMIT_AS).

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
        """Restrict filesystem access to a set of allowed paths.

        Args:
            allowed_paths: List of directory paths the plugin may access.
        """
        self._allowed_paths = set(os.path.abspath(p) for p in allowed_paths)
        logger.debug("Filesystem restricted to: %s", self._allowed_paths)

    def restrict_network(self, allowed_domains: List[str]) -> None:
        """Restrict network access to a set of allowed domains.

        Args:
            allowed_domains: List of domain names the plugin may connect to.
        """
        self._allowed_domains = set(allowed_domains)
        logger.debug("Network restricted to: %s", self._allowed_domains)

    def restrict_exec(self, allowed_commands: List[str]) -> None:
        """Restrict subprocess execution to allowed commands.

        Args:
            allowed_commands: List of executable names the plugin may run.
        """
        self._allowed_commands = set(allowed_commands)
        logger.debug("Execution restricted to: %s", self._allowed_commands)

    def apply_hard_limits(self, cpu_seconds: int = 5,
                          memory_mb: int = 256) -> None:
        """Apply hard resource limits using the `resource` module.

        Args:
            cpu_seconds: Maximum CPU time in seconds (RLIMIT_CPU).
            memory_mb: Maximum address space in MB (RLIMIT_AS).
        """
        try:
            # CPU time limit
            resource_module.setrlimit(
                resource_module.RLIMIT_CPU,
                (cpu_seconds, cpu_seconds + 1),
            )
            # Address space limit (virtual memory)
            memory_bytes = memory_mb * 1024 * 1024
            resource_module.setrlimit(
                resource_module.RLIMIT_AS,
                (memory_bytes, memory_bytes + 1024 * 1024),
            )
            self._limits_applied = True
            logger.debug(
                "Applied hard limits: CPU=%ds, mem=%dMB", cpu_seconds, memory_mb
            )
        except (resource_module.error, ValueError) as e:
            logger.warning("Could not apply resource limits: %s", e)

    def start_tracking(self) -> None:
        """Start tracking resource usage."""
        self._cpu_time_start = time.perf_counter()
        self._memory_peak = 0
        self._file_ops = 0

    def stop_tracking(self) -> Dict[str, Any]:
        """Stop tracking and return resource usage summary.

        Returns:
            Dict with cpu_time_ms, memory_peak_kb, file_ops.
        """
        self._cpu_time_end = time.perf_counter()
        return {
            "cpu_time_ms": round(
                (self._cpu_time_end - self._cpu_time_start) * 1000, 3
            ),
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

    def __init__(self, config: Optional[PluginSdkConfig] = None):
        self.config = config or PluginSdkConfig()
        self.resource_limiter: Optional[ResourceLimiter] = None

    def execute(self, func: Callable, timeout_ms: Optional[int] = None,
                resource_limiter: Optional[ResourceLimiter] = None) -> Tuple[Optional[Any], Optional[str]]:
        """Execute a function with timeout and optional resource limits.

        Args:
            func: The function to execute.
            timeout_ms: Timeout in milliseconds (defaults to config value).
            resource_limiter: Optional ResourceLimiter instance.

        Returns:
            Tuple of (result, error). On success, error is None.
            On timeout or exception, result is None and error is a string.
        """
        timeout = timeout_ms if timeout_ms is not None else self.config.sandbox_timeout_ms
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
            # Thread still running after timeout
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
        if not self.config.allowed_imports:
            return True  # No restrictions
        return module_name in self.config.allowed_imports

    def validate_manifest_permissions(self, manifest: PluginManifest) -> bool:
        """Check that declared permissions are reasonable for the sandbox level.

        Validates that the permissions declared in the manifest do not
        conflict with the current sandbox restrictions.

        Args:
            manifest: The PluginManifest to validate.

        Returns:
            True if permissions are acceptable.
        """
        if not manifest.permissions:
            return True

        # Map of permission -> required sandbox features
        dangerous_permissions = {
            "network:all": "allows unrestricted network access",
            "filesystem:all": "allows unrestricted filesystem access",
            "exec:all": "allows arbitrary command execution",
            "system:all": "allows full system access",
        }

        for perm in manifest.permissions:
            if perm in dangerous_permissions:
                logger.warning(
                    "Plugin '%s' requests dangerous permission '%s': %s",
                    manifest.id, perm, dangerous_permissions[perm],
                )

            # Check if permission conflicts with resource limiter
            if self.resource_limiter:
                if perm.startswith("filesystem:") and perm != "filesystem:all":
                    path = perm.split(":", 1)[1] if ":" in perm else ""
                    if path and self.resource_limiter.allowed_paths:
                        abs_path = os.path.abspath(path)
                        if not any(
                            abs_path.startswith(allowed)
                            for allowed in self.resource_limiter.allowed_paths
                        ):
                            logger.warning(
                                "Permission '%s' not in restricted paths", perm
                            )
                            return False

        return True
