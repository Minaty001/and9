"""
Phase 2 — Architecture Error Definitions.
"""

from typing import Any, Optional
from services.phase01_core.errors import ServiceError


class ArchitectureError(ServiceError):
    """Base architecture error."""

    def __init__(self, message: str, code: str = "ARCHITECTURE_ERROR", details: Any = None):
        super().__init__(message, code, details)


class ModuleNotFoundError(ArchitectureError):
    """Raised when a module is not found in the registry."""

    def __init__(self, module_name: str):
        super().__init__(
            f"Module '{module_name}' not found",
            code="MODULE_NOT_FOUND",
            details={"module": module_name},
        )


class ModuleRegistrationError(ArchitectureError):
    """Raised when module registration fails."""

    def __init__(self, message: str, details: Any = None):
        super().__init__(message, "MODULE_REGISTRATION_ERROR", details)


class EventBusError(ArchitectureError):
    """Raised when an event bus operation fails."""

    def __init__(self, message: str, details: Any = None):
        super().__init__(message, "EVENT_BUS_ERROR", details)


class EventTimeoutError(ArchitectureError):
    """Raised when an event handler times out."""

    def __init__(self, event_type: str, timeout: float):
        super().__init__(
            f"Event '{event_type}' handler timed out after {timeout}s",
            code="EVENT_TIMEOUT",
            details={"event_type": event_type, "timeout": timeout},
        )


class CircularDependencyError(ArchitectureError):
    """Raised when module dependencies form a cycle."""

    def __init__(self, modules: list):
        super().__init__(
            f"Circular dependency detected between modules: {modules}",
            code="CIRCULAR_DEPENDENCY",
            details={"modules": modules},
        )
