"""
Phase 2 — System Architecture
==============================

Event-driven communication and dependency inversion between modules.

Key components:
    - EventBus: In-process pub/sub for decoupled communication
    - ModuleRegistry: Service discovery and dependency injection
    - ArchitectureService: Coordinates module wiring

Design rules:
    - Modules communicate through events, not direct calls
    - Reasoning is separated from execution
    - Every module has a clear interface contract
"""

from .event_bus import EventBus, Event, EventPriority, EventHandler
from .module_registry import ModuleRegistry, ModuleInfo
from .service import ArchitectureService
from .config import ArchitectureConfig
from .models import ModuleRegistration, EventMessage, SystemStatus

__all__ = [
    "EventBus",
    "Event",
    "EventPriority",
    "EventHandler",
    "ModuleRegistry",
    "ModuleInfo",
    "ArchitectureService",
    "ArchitectureConfig",
    "ModuleRegistration",
    "EventMessage",
    "SystemStatus",
]
