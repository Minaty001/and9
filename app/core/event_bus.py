"""
app/core/event_bus.py — Async event bus for AND9 v5.0

All inter-module communication goes through here.
No module should import another module's class directly.

Usage:
    bus = get_event_bus()
    bus.subscribe("intent.detected", my_handler)
    bus.publish("intent.detected", {"intent": "open_app", "app": "youtube"})
"""

import threading
import logging
from typing import Callable, Dict, List, Any
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class Event:
    name: str
    payload: Dict[str, Any]
    source: str = "system"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    event_id: str = field(default_factory=lambda: __import__('uuid').uuid4().hex[:12])


class EventBus:
    """
    Thread-safe publish/subscribe event bus.

    Events are dispatched synchronously in the calling thread.
    Handlers must be fast (< 50 ms) or they should enqueue tasks.
    """

    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._lock = threading.Lock()
        self._history: List[Event] = []   # last 100 events for debug
        self._max_history = 100

    def subscribe(self, event_name: str, handler: Callable[["Event"], None]) -> None:
        """Register a handler for an event."""
        with self._lock:
            if handler not in self._handlers[event_name]:
                self._handlers[event_name].append(handler)
        logger.debug(f"EventBus: subscribed {handler.__name__} to '{event_name}'")

    def unsubscribe(self, event_name: str, handler: Callable) -> None:
        """Remove a handler."""
        with self._lock:
            self._handlers[event_name] = [
                h for h in self._handlers[event_name] if h != handler
            ]

    def publish(self, event_name: str, payload: dict,
                source: str = "system") -> None:
        """Dispatch event to all subscribers."""
        event = Event(name=event_name, payload=payload, source=source)
        self._record(event)

        with self._lock:
            handlers = list(self._handlers.get(event_name, []))

        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"EventBus: handler {handler.__name__} failed "
                             f"for '{event_name}': {e}", exc_info=True)
                self._record(Event(
                    name="event.handler.failed",
                    payload={"event": event_name, "handler": handler.__name__,
                             "error": str(e)},
                    source="event_bus"
                ))

    def _record(self, event: Event) -> None:
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history.pop(0)

    def get_history(self) -> List[Event]:
        return list(self._history)


# Singleton
_bus: EventBus | None = None

def get_event_bus() -> EventBus:
    global _bus
    if _bus is None:
        _bus = EventBus()
    return _bus