"""
Phase 2 — Module Registry.

Responsible for service discovery and dependency injection.
Modules register themselves with metadata, and the registry
resolves dependencies and manages module lifecycle.

Usage:
    registry = ModuleRegistry()
    registry.register("tokenizer", tokenizer_service, ["config"])
    registry.register("intent", intent_service, ["tokenizer", "embedding"])
    deps = registry.resolve_dependencies("intent")  # ["config", "tokenizer", "embedding"]
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from services.base import ServiceBase
from .errors import ModuleNotFoundError, ModuleRegistrationError, CircularDependencyError
from .models import ModuleRegistration, ModuleStatus

logger = logging.getLogger(__name__)


@dataclass
class ModuleInfo:
    """Information about a registered module."""

    name: str
    service: ServiceBase
    registration: ModuleRegistration


class ModuleRegistry:
    """Central registry for all JARVIS modules.

    Provides dependency resolution, lifecycle management,
    and module discovery.
    """

    def __init__(self, max_modules: int = 50):
        self._modules: Dict[str, ModuleInfo] = {}
        self._max_modules = max_modules

    # ── Registration ────────────────────────────────────────────

    def register(
        self,
        name: str,
        service: ServiceBase,
        dependencies: Optional[List[str]] = None,
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ModuleRegistration:
        """Register a module with the system.

        Args:
            name: Unique module name.
            service: ServiceBase instance.
            dependencies: List of module names this module depends on.
            description: Human-readable description.
            metadata: Arbitrary metadata.

        Returns:
            ModuleRegistration instance.

        Raises:
            ModuleRegistrationError: If module name already exists or limit reached.
        """
        if name in self._modules:
            raise ModuleRegistrationError(f"Module '{name}' is already registered")

        if len(self._modules) >= self._max_modules:
            raise ModuleRegistrationError(
                f"Module limit ({self._max_modules}) reached"
            )

        registration = ModuleRegistration(
            name=name,
            description=description,
            dependencies=dependencies or [],
            status=ModuleStatus.REGISTERED,
            metadata=metadata or {},
        )

        self._modules[name] = ModuleInfo(
            name=name,
            service=service,
            registration=registration,
        )

        logger.info("Registered module: '%s' (deps: %s)", name, dependencies or [])
        return registration

    def get(self, name: str) -> ServiceBase:
        """Retrieve a registered module by name.

        Raises ModuleNotFoundError if not found.
        """
        info = self._modules.get(name)
        if info is None:
            raise ModuleNotFoundError(name)
        return info.service

    def get_info(self, name: str) -> ModuleRegistration:
        """Get registration metadata for a module."""
        info = self._modules.get(name)
        if info is None:
            raise ModuleNotFoundError(name)
        return info.registration

    # ── Dependency Resolution ───────────────────────────────────

    def resolve_dependencies(self, name: str) -> List[str]:
        """Resolve full dependency chain for a module (topological order).

        Args:
            name: Module name to resolve dependencies for.

        Returns:
            List of module names in dependency order (dependencies first).

        Raises:
            ModuleNotFoundError: If a dependency module is not registered.
            CircularDependencyError: If a circular dependency is detected.
        """
        result: List[str] = []
        visited: Set[str] = set()
        in_stack: Set[str] = set()

        def dfs(current: str):
            if current in in_stack:
                raise CircularDependencyError(list(in_stack))
            if current in visited:
                return

            if current not in self._modules:
                raise ModuleNotFoundError(current)

            in_stack.add(current)
            info = self._modules[current]
            for dep in info.registration.dependencies:
                dfs(dep)
            in_stack.remove(current)
            visited.add(current)
            result.append(current)

        dfs(name)
        return result

    def check_dependencies(self, name: str) -> bool:
        """Check if all dependencies of a module are initialized.

        Args:
            name: Module name to check.

        Returns:
            True if all dependencies are initialized.
        """
        info = self._modules.get(name)
        if info is None:
            raise ModuleNotFoundError(name)

        for dep_name in info.registration.dependencies:
            dep_info = self._modules.get(dep_name)
            if dep_info is None:
                return False
            if dep_info.registration.status != ModuleStatus.INITIALIZED:
                return False
        return True

    # ── Status Management ───────────────────────────────────────

    def set_status(self, name: str, status: ModuleStatus) -> None:
        """Update the status of a registered module."""
        info = self._modules.get(name)
        if info is None:
            raise ModuleNotFoundError(name)
        info.registration.status = status

    def get_status(self, name: str) -> ModuleStatus:
        """Get the current status of a module."""
        info = self._modules.get(name)
        if info is None:
            raise ModuleNotFoundError(name)
        return info.registration.status

    # ── Discovery ───────────────────────────────────────────────

    def list_modules(
        self, status_filter: Optional[ModuleStatus] = None
    ) -> List[Dict[str, Any]]:
        """List all registered modules, optionally filtered by status.

        Args:
            status_filter: Optional ModuleStatus to filter by.

        Returns:
            List of module summary dicts.
        """
        result = []
        for name, info in sorted(self._modules.items()):
            reg = info.registration
            if status_filter is None or reg.status == status_filter:
                result.append({
                    "name": name,
                    "version": reg.version,
                    "description": reg.description,
                    "status": reg.status.value,
                    "dependencies": reg.dependencies,
                    "events_subscribed": reg.events_subscribed,
                    "events_published": reg.events_published,
                })
        return result

    @property
    def count(self) -> int:
        """Return the number of registered modules."""
        return len(self._modules)

    def unregister(self, name: str) -> bool:
        """Remove a module from the registry.

        Args:
            name: Module name to unregister.

        Returns:
            True if removed, False if not found.
        """
        if name in self._modules:
            del self._modules[name]
            logger.info("Unregistered module: '%s'", name)
            return True
        return False

    def clear(self) -> None:
        """Remove all modules from the registry."""
        self._modules.clear()
        logger.info("Module registry cleared")
