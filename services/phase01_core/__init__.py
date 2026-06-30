"""
Phase 1 — Project Vision & Core Rules
======================================

Base framework for the JARVIS AI Operating System.

Design principles:
    - Modularity: each component is independently testable
    - Local-first: works offline, no cloud dependency
    - Deterministic execution: same input → same output
    - Security: all inputs validated, no injection surfaces
    - Logging: structured JSON logs with rotation
    - Testing: unit tests for every public method

Deliverables:
    - API specification (api_spec.md)
    - Shared error hierarchy
    - Structured logging setup
    - Core Pydantic models (BrainResult, ProcessingResult)
    - Core service entry point
"""

from .service import CoreService
from .models import BrainResult, ProcessingResult, ServiceStatus, BrainType, IntentType
from .errors import JarvisError, ServiceError, ProcessingError, ValidationError, ConfigError
from .config import CoreConfig

__all__ = [
    "CoreService",
    "BrainResult",
    "ProcessingResult",
    "ServiceStatus",
    "BrainType",
    "IntentType",
    "JarvisError",
    "ServiceError",
    "ProcessingError",
    "ValidationError",
    "ConfigError",
    "CoreConfig",
]
