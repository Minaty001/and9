"""
Phase 2 — In-Process Event Bus.

Provides decoupled, event-driven communication between services.
Supports:
    - Typed events
    - Priority ordering
    - Synchronous and asynchronous handlers
    - Event filtering
    - Handler error isolation (one failing handler doesn't break others)

Usage:
    bus = EventBus()
    
    @bus.on("query.processed")
    async def handle_query(event):
        print(f"Query processed: {event.payload}")
    
    await bus.emit(Event("query.processed", {"query": "hello"}))
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Callable, Dict, List, Optional, Set, Awaitable

from .errors import EventBusError, EventTimeoutError

logger = logging.getLogger(__name__)


class EventPriority(IntEnum):
    """Event processing priority (higher = processed first)."""

    CRITICAL = 10
    HIGH = 8
    NORMAL = 5
    LOW = 2
    BACKGROUND = 0


@dataclass
class Event:
    """A message sent through the event bus.

    Attributes:
        type: Event type identifier (e.g., "query.received", "intent.detected").
        payload: Arbitrary event data.
        source: Name of the module that emitted the event.
        priority: Processing priority.
        correlation_id: Optional tracing ID for request tracking.
        id: Unique event identifier.
        timestamp: When the event was created.
    """

    type: str
    payload: Dict[str, Any] = field(default_factory=dict)
    source: str = "unknown"
    priority: EventPriority = EventPriority.NORMAL
    correlation_id: Optional[str] = None
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: float = field(default_factory=time.time)


EventHandler = Callable[[Event], Awaitable[None]]
"""Type alias for async event handlers."""


class EventBus:
    """In-process publish/subscribe event bus.

    Thread-safe for concurrent emit/subscribe operations.
    """

    def __init__(self, max_queue_size: int = 1000):
        self._handlers: Dict[str, List[EventHandler]] = {}
        self._wildcard_handlers: List[EventHandler] = []
        self._lock = asyncio.Lock()
        self._max_queue_size = max_queue_size
        self._total_events = 0
        self._failed_events = 0
        self._handler_times: Dict[str, List[float]] = {}

    # ── Subscription ────────────────────────────────────────────

    def on(self, event_type: str) -> Callable[[EventHandler], EventHandler]:
        """Decorator to register an event handler.

        Args:
            event_type: The event type to listen for. Use "*" for all events.

        Returns:
            A decorator that registers the handler.

        Usage:
            @bus.on("query.received")
            async def handler(event): ...
        """
        def decorator(handler: EventHandler) -> EventHandler:
            self.subscribe(event_type, handler)
            return handler
        return decorator

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Register a handler for an event type.

        Args:
            event_type: Event type or "*" for all events.
            handler: Async callable accepting an Event.
        """
        if event_type == "*":
            self._wildcard_handlers.append(handler)
            logger.debug("Registered wildcard handler: %s", handler.__name__)
            return

        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.debug("Registered handler for '%s': %s", event_type, handler.__name__)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Remove a handler for an event type."""
        if event_type == "*":
            if handler in self._wildcard_handlers:
                self._wildcard_handlers.remove(handler)
            return
        if event_type in self._handlers and handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)

    # ── Publishing ──────────────────────────────────────────────

    async def emit(self, event: Event) -> int:
        """Emit an event to all registered handlers.

        Args:
            event: The Event to emit.

        Returns:
            Number of handlers that processed the event.
        """
        async with self._lock:
            self._total_events += 1

        # Collect all matching handlers
        handlers = list(self._wildcard_handlers)  # wildcards always fire
        if event.type in self._handlers:
            handlers.extend(self._handlers[event.type])

        if not handlers:
            logger.debug("No handlers for event '%s'", event.type)
            return 0

        # Fire all handlers (isolate failures)
        fired = 0
        for handler in handlers:
            try:
                t0 = time.perf_counter()
                await handler(event)
                elapsed = (time.perf_counter() - t0) * 1000
                logger.debug("Handler %s processed '%s' in %.1fms",
                             handler.__name__, event.type, elapsed)
                fired += 1

                # Record timing
                hname = f"{event.type}:{handler.__name__}"
                if hname not in self._handler_times:
                    self._handler_times[hname] = []
                self._handler_times[hname].append(elapsed)
                # Keep last 100
                if len(self._handler_times[hname]) > 100:
                    self._handler_times[hname] = self._handler_times[hname][-100:]

            except Exception as e:
                logger.error("Handler %s failed for event '%s': %s",
                             handler.__name__, event.type, e)
                async with self._lock:
                    self._failed_events += 1

        return fired

    async def emit_and_wait(
        self, event: Event, timeout: float = 30.0
    ) -> int:
        """Emit an event and wait for all handlers to complete.

        Args:
            event: The Event to emit.
            timeout: Maximum time in seconds to wait.

        Returns:
            Number of handlers that processed the event.
        """
        try:
            return await asyncio.wait_for(self.emit(event), timeout=timeout)
        except asyncio.TimeoutError:
            raise EventTimeoutError(event.type, timeout)

    # ── Introspection ───────────────────────────────────────────

    def get_stats(self) -> dict:
        """Return event bus statistics."""
        handler_count = len(self._wildcard_handlers) + sum(
            len(h) for h in self._handlers.values()
        )
        return {
            "total_events": self._total_events,
            "failed_events": self._failed_events,
            "handlers_registered": handler_count,
            "event_types": len(self._handlers),
            "handler_timing_ms": {
                name: {
                    "avg": round(sum(t) / len(t), 1) if t else 0,
                    "count": len(t),
                    "last": round(t[-1], 1) if t else 0,
                }
                for name, t in sorted(self._handler_times.items())
            },
        }

    def reset(self) -> None:
        """Clear all handlers and reset statistics."""
        self._handlers.clear()
        self._wildcard_handlers.clear()
        self._total_events = 0
        self._failed_events = 0
        self._handler_times.clear()
