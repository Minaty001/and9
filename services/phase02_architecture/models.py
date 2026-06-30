"""
Phase 2 — Architecture Models.

Data structures for module registration and event messages.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ModuleStatus(str, Enum):
    """Status of a registered module."""

    REGISTERED = "registered"
    INITIALIZED = "initialized"
    ACTIVE = "active"
    DEGRADED = "degraded"
    ERROR = "error"
    SHUTDOWN = "shutdown"


class ModuleRegistration(BaseModel):
    """Metadata for a module registered in the system."""

    name: str = Field(..., description="Unique module name")
    version: str = Field(default="1.0.0", description="Module version")
    description: str = Field(default="", description="Module description")
    dependencies: List[str] = Field(default_factory=list, description="Module dependencies")
    status: ModuleStatus = Field(default=ModuleStatus.REGISTERED, description="Current status")
    events_subscribed: List[str] = Field(default_factory=list, description="Events this module listens to")
    events_published: List[str] = Field(default_factory=list, description="Events this module emits")
    initialized_at: Optional[str] = Field(default=None, description="ISO timestamp of initialization")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary module metadata")


class EventMessage(BaseModel):
    """A structured event message flowing through the event bus."""

    event_type: str = Field(..., description="Event type identifier")
    source: str = Field(..., description="Module that emitted the event")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Event data payload")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="Event timestamp")
    correlation_id: Optional[str] = Field(default=None, description="Correlation ID for tracing")
    priority: int = Field(default=0, ge=0, le=10, description="Event priority (0=lowest, 10=highest)")
    ttl_seconds: Optional[int] = Field(default=None, description="Time-to-live before event expires")


class SystemStatus(BaseModel):
    """Overall system status from the architecture layer."""

    status: str = Field(default="healthy", description="System status")
    uptime_seconds: float = Field(default=0.0, description="System uptime")
    modules_count: int = Field(default=0, description="Registered modules count")
    active_modules: int = Field(default=0, description="Active modules count")
    events_processed: int = Field(default=0, description="Total events processed")
    modules: Dict[str, ModuleRegistration] = Field(default_factory=dict, description="Registered modules")
    last_event: Optional[str] = Field(default=None, description="Last processed event type")
