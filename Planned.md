# AND9 — Full Detailed Implementation Plan

> **Project:** AND9 (Jarvis-like Android AI Assistant)
> **Target Architecture:** AND9 v5.0 — AI Operating System
> **Deployment:** Render Free Tier (300 MB RAM hard limit)
> **LLM Stack:** Groq (primary) → Opencode Zen (fallback)
> **Database:** Supabase (PostgreSQL) + in-memory fallback
> **Last Updated:** 2026-07-09

---

## Table of Contents

1. [Current State](#current-state)
2. [Implementation Strategy](#implementation-strategy)
3. [Phase 1 — AI Kernel & Core Infrastructure](#phase-1--ai-kernel--core-infrastructure)
4. [Phase 2 — Brain System](#phase-2--brain-system)
5. [Phase 3 — Android Services Layer](#phase-3--android-services-layer)
6. [Phase 4 — Plugin System](#phase-4--plugin-system)
7. [Phase 5 — Memory & Learning](#phase-5--memory--learning)
8. [Phase 6 — Security Layer](#phase-6--security-layer)
9. [Phase 7 — Observability](#phase-7--observability)
10. [Phase 8 — API Refactor](#phase-8--api-refactor)
11. [Refactor Plan for Existing Files](#refactor-plan-for-existing-files)
12. [Final File Tree](#final-file-tree)
13. [Week-by-Week Schedule](#week-by-week-schedule)
14. [Success Metrics](#success-metrics)

---

## Current State

### What Already Exists

| File | Purpose | Quality |
| :--- | :--- | :--- |
| `app/core/orchestrator.py` | Central request pipeline (655 lines) | 🟡 Works but monolithic |
| `app/core/understanding.py` | Intent + entity extraction (482 lines) | 🟢 Good |
| `app/core/memory.py` | Supabase + in-memory memory (31 KB) | 🟢 Good |
| `app/core/brain.py` | Groq → Opencode LLM calls | 🟢 Good |
| `app/core/events.py` | Reminder + event system | 🟢 Good |
| `app/core/working_memory.py` | Session state | 🟢 Good |
| `app/core/config.py` | Environment config | 🟢 Clean |
| `app/android/action_registry.py` | Android action dispatch | 🟡 Needs Event Bus |
| `app/android/actions/*.py` | Alarm, App, Call, Timer, YouTube etc. | 🟢 Exists |
| `app/core/goal_tracker.py` | Goal management | 🟡 Works |
| `app/core/reflection.py` | Reflection engine | 🟡 Works |
| `app/api/routes.py` | REST API endpoints | 🟡 Tightly coupled |

### What is Missing (To Build)

```
app/core/kernel.py            ← AI Kernel (service boot/stop/health)
app/core/event_bus.py         ← Event Bus (decoupled messaging)
app/core/service_manager.py   ← Service Manager (lifecycle control)
app/core/task_queue.py        ← Priority Task Queue
app/core/resource_manager.py  ← RAM/CPU watchdog
app/core/security_manager.py  ← Security + audit log
app/core/observability.py     ← Health + metrics endpoint
app/core/learning.py          ← Pattern learning engine

app/brain/manager.py          ← Brain router
app/brain/subconscious.py     ← Fast reflex brain (< 300 ms)
app/brain/conscious.py        ← Deep reasoning brain (1–10 s)
app/brain/planner.py          ← Multi-step task decomposer

app/plugins/__init__.py       ← Plugin registry
app/plugins/base_plugin.py    ← Plugin contract
app/plugins/weather/          ← Weather plugin
app/plugins/calculator/       ← Calculator plugin
app/plugins/spotify/          ← Spotify plugin

app/services/base_service.py  ← Service contract
app/services/voice_service.py
app/services/chat_service.py
app/services/memory_service.py
```

---

## Implementation Strategy

### Core Principle

> Never add a feature without a home. Every piece of logic belongs to exactly one layer.

```
Request comes in
       │
       ▼
  API Layer              ← Validate HTTP, parse JSON
       │
       ▼
  AI Kernel              ← Route to Event Bus
       │
       ▼
  Event Bus              ← Publish to subscribers
       │
       ▼
  Brain Manager          ← Decide: Subconscious or Conscious
       │
  ┌────┴────┐
  ▼         ▼
Sub       Conscious
brain      brain
  │         │
  └────┬────┘
       │
       ▼
  Task Queue             ← All execution goes through queue
       │
       ▼
  Executor               ← Calls plugin or android service
       │
       ▼
  Memory                 ← Save result + update context
       │
       ▼
  Response               ← Format and return to user
```

---

## Phase 1 — AI Kernel & Core Infrastructure

### 1.1 Event Bus

**File:** `app/core/event_bus.py`

**Purpose:** Central nervous system. No module talks to another directly.

**Why:** The current code calls modules directly (orchestrator imports brain, memory, understanding, events all at once). This creates tight coupling and makes testing/scaling hard.

**Full Implementation Plan:**

```python
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
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class Event:
    name: str
    payload: Dict[str, Any]
    source: str = "system"
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
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

    def subscribe(self, event_name: str, handler: Callable[[Event], None]) -> None:
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
                # Publish failure event (no recursion guard needed as
                # handler.failed is never subscribed by itself)
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
```

**Standard Event Names to Register:**
```
# Input events
input.voice                   # Raw voice transcript received
input.text                    # Raw text command received

# Understanding events
intent.detected               # Intent + entities extracted
intent.routed                 # Brain decision made (sub/conscious)

# Planning events
plan.created                  # Task list ready from Planner
plan.step.started             # Individual step started
plan.step.completed           # Individual step done
plan.step.failed              # Step failed (trigger retry)
plan.completed                # All steps done

# Execution events
task.queued                   # Task added to queue
task.started                  # Task picked up by executor
task.completed                # Task succeeded
task.failed                   # Task failed after retries

# Brain events
brain.subconscious.started
brain.subconscious.completed
brain.subconscious.failed
brain.conscious.started
brain.conscious.completed
brain.conscious.failed

# Memory events
memory.saved
memory.recalled
memory.cleared

# System events
service.started
service.stopped
service.failed
service.degraded
system.memory.warning         # RAM > 250 MB
system.memory.critical        # RAM > 270 MB
system.startup.complete
system.shutdown.started

# Response events
response.ready                # Final response ready to send
```

---

### 1.2 AI Kernel

**File:** `app/core/kernel.py`

**Purpose:** Single boot point for the entire AND9 OS. Starts all services in order, monitors health, and handles recovery.

**Full Implementation Plan:**

```python
"""
app/core/kernel.py — AND9 AI Kernel

The kernel is the single entry point for booting AND9.
All requests route through the kernel to the event bus.

Singleton — only one kernel per process.

Boot order:
  1. ResourceManager (must start first — monitors RAM)
  2. EventBus       (needed by everything else)
  3. ServiceManager (registers and starts all services)
  4. BrainManager   (connects sub/conscious brains)
  5. TaskQueue      (starts worker thread)
  6. SecurityManager
  7. Observability

Shutdown order: reverse of boot.
"""

import logging
import threading
import time
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class AND9Kernel:
    """AND9 AI Operating System Kernel — Singleton."""

    _instance: Optional["AND9Kernel"] = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def boot(self) -> None:
        """
        Boot AND9. Called once from app/main.py create_app().
        """
        if self._initialized:
            logger.warning("Kernel already booted — skipping.")
            return

        self._start_time = datetime.utcnow()
        logger.info("AND9 Kernel booting...")

        # 1. Resource Manager (first — so we know RAM before loading anything)
        from app.core.resource_manager import ResourceManager
        self.resource_manager = ResourceManager()
        self.resource_manager.start()

        # 2. Event Bus
        from app.core.event_bus import get_event_bus
        self.event_bus = get_event_bus()

        # 3. Service Manager
        from app.core.service_manager import ServiceManager
        self.service_manager = ServiceManager(self.event_bus)
        self._register_services()
        self.service_manager.start_all()

        # 4. Task Queue
        from app.core.task_queue import TaskQueue
        self.task_queue = TaskQueue(self.event_bus)
        self.task_queue.start()

        # 5. Brain Manager
        from app.brain.manager import BrainManager
        self.brain_manager = BrainManager(self.event_bus, self.task_queue)

        # 6. Security Manager
        from app.core.security_manager import SecurityManager
        self.security_manager = SecurityManager()

        # 7. Observability
        from app.core.observability import Observability
        self.observability = Observability(self)

        self._initialized = True
        self.event_bus.publish("system.startup.complete", {
            "boot_time_ms": int((datetime.utcnow() - self._start_time)
                                .total_seconds() * 1000)
        }, source="kernel")
        logger.info("AND9 Kernel boot complete.")

    def _register_services(self) -> None:
        """Register all AND9 services with the ServiceManager."""
        from app.services.memory_service import MemoryService
        from app.services.chat_service import ChatService
        from app.services.intent_service import IntentService

        self.service_manager.register(MemoryService())
        self.service_manager.register(ChatService())
        self.service_manager.register(IntentService())
        # More services added as phases progress

    def handle_request(self, text: str, source: str = "text") -> dict:
        """
        Main entry point for all user requests.
        Routes through Event Bus → Brain Manager → Task Queue → Response.
        """
        if not self._initialized:
            return {"response": "AND9 is starting up. Please wait.", "status": "booting"}

        request_id = __import__('uuid').uuid4().hex[:12]
        self.event_bus.publish(f"input.{source}", {
            "text": text,
            "request_id": request_id,
        }, source="kernel")

        # Brain Manager handles the event and returns a result
        return self.brain_manager.process(text, request_id=request_id)

    def health(self) -> dict:
        """Return kernel + all service health."""
        if not self._initialized:
            return {"status": "booting"}
        return {
            "status": "running",
            "uptime_seconds": int((datetime.utcnow() - self._start_time).total_seconds()),
            "services": self.service_manager.status(),
            "resources": self.resource_manager.snapshot(),
            "queue_depth": self.task_queue.depth(),
        }

    def shutdown(self) -> None:
        """Graceful shutdown. Called on app teardown."""
        logger.info("AND9 Kernel shutting down...")
        self.event_bus.publish("system.shutdown.started", {}, source="kernel")
        self.task_queue.drain()
        self.service_manager.stop_all()
        self.resource_manager.stop()
        self._initialized = False
        logger.info("AND9 Kernel stopped.")


# Module-level singleton accessor
_kernel: AND9Kernel | None = None

def get_kernel() -> AND9Kernel:
    global _kernel
    if _kernel is None:
        _kernel = AND9Kernel()
    return _kernel
```

---

### 1.3 Service Manager

**File:** `app/core/service_manager.py`

**Purpose:** Register, start, stop, and health-check all named services.

**Implementation Plan:**

```python
"""
app/core/service_manager.py — Service lifecycle manager

Every AND9 feature is a named BaseService.
The ServiceManager owns the lifecycle of every service.

Service states:
  REGISTERED → STARTING → RUNNING → STOPPING → STOPPED
                        ↘ FAILED → (restart attempt)
"""

import logging
import threading
from enum import Enum
from typing import Dict, Optional
from app.core.event_bus import EventBus, Event

logger = logging.getLogger(__name__)


class ServiceState(Enum):
    REGISTERED = "registered"
    STARTING   = "starting"
    RUNNING    = "running"
    STOPPING   = "stopping"
    STOPPED    = "stopped"
    FAILED     = "failed"
    DEGRADED   = "degraded"


class BaseService:
    """
    Contract that every AND9 service must implement.

    Subclass this and implement initialize(), health_check(), shutdown().
    """
    name: str = "unnamed"
    lazy: bool = False          # If True, starts only when first requested
    ram_estimate_mb: int = 5    # Expected RAM usage (for budget tracking)

    def initialize(self) -> None:
        """Start the service. Raise on failure."""
        raise NotImplementedError

    def health_check(self) -> bool:
        """Return True if service is healthy."""
        return True

    def shutdown(self) -> None:
        """Clean up resources."""
        pass


class ServiceManager:
    def __init__(self, event_bus: EventBus):
        self._bus = event_bus
        self._services: Dict[str, BaseService] = {}
        self._states: Dict[str, ServiceState] = {}
        self._lock = threading.Lock()

    def register(self, service: BaseService) -> None:
        with self._lock:
            self._services[service.name] = service
            self._states[service.name] = ServiceState.REGISTERED
        logger.debug(f"ServiceManager: registered '{service.name}'")

    def start_all(self) -> None:
        for name, service in self._services.items():
            if not service.lazy:
                self.start(name)

    def start(self, name: str) -> bool:
        service = self._services.get(name)
        if not service:
            logger.error(f"ServiceManager: unknown service '{name}'")
            return False
        try:
            self._states[name] = ServiceState.STARTING
            service.initialize()
            self._states[name] = ServiceState.RUNNING
            self._bus.publish("service.started", {"service": name}, source="service_manager")
            logger.info(f"ServiceManager: '{name}' started.")
            return True
        except Exception as e:
            self._states[name] = ServiceState.FAILED
            self._bus.publish("service.failed", {"service": name, "error": str(e)},
                              source="service_manager")
            logger.error(f"ServiceManager: '{name}' failed to start: {e}")
            return False

    def stop(self, name: str) -> None:
        service = self._services.get(name)
        if not service:
            return
        try:
            self._states[name] = ServiceState.STOPPING
            service.shutdown()
            self._states[name] = ServiceState.STOPPED
            self._bus.publish("service.stopped", {"service": name}, source="service_manager")
        except Exception as e:
            logger.error(f"ServiceManager: error stopping '{name}': {e}")

    def stop_all(self) -> None:
        for name in reversed(list(self._services.keys())):
            if self._states.get(name) == ServiceState.RUNNING:
                self.stop(name)

    def status(self) -> dict:
        return {name: state.value for name, state in self._states.items()}

    def get(self, name: str) -> Optional[BaseService]:
        return self._services.get(name)
```

---

### 1.4 Task Queue

**File:** `app/core/task_queue.py`

**Purpose:** All execution goes through a priority queue. No direct function calls for tasks.

```python
"""
app/core/task_queue.py — Priority task queue for AND9

No task executes directly. Every action is enqueued here.

Priority levels:
  0 = CRITICAL  (emergency stop, auth failures)
  1 = HIGH      (voice commands, app launch, timers)
  2 = MEDIUM    (file operations, web search)
  3 = LOW       (cache cleanup, memory compression)
"""

import logging
import threading
import queue
import uuid
from dataclasses import dataclass, field
from typing import Callable, Dict, Any, Optional
from enum import IntEnum
from app.core.event_bus import EventBus

logger = logging.getLogger(__name__)

class Priority(IntEnum):
    CRITICAL = 0
    HIGH     = 1
    MEDIUM   = 2
    LOW      = 3


@dataclass(order=True)
class Task:
    priority: int
    task_id: str = field(compare=False, default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = field(compare=False, default="")
    fn: Callable = field(compare=False, default=None)
    args: tuple = field(compare=False, default_factory=tuple)
    kwargs: dict = field(compare=False, default_factory=dict)
    retries: int = field(compare=False, default=2)
    timeout_sec: int = field(compare=False, default=30)

    # Internal state
    attempts: int = field(compare=False, default=0)
    status: str = field(compare=False, default="queued")


class TaskQueue:
    def __init__(self, event_bus: EventBus):
        self._bus = event_bus
        self._queue: queue.PriorityQueue = queue.PriorityQueue()
        self._results: Dict[str, Any] = {}
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._running = True
        self._worker_thread = threading.Thread(
            target=self._worker_loop, daemon=True, name="TaskQueue-Worker"
        )
        self._worker_thread.start()
        logger.info("TaskQueue: worker started.")

    def enqueue(self, fn: Callable, name: str = "",
                priority: int = Priority.MEDIUM,
                args: tuple = (), kwargs: dict = None,
                retries: int = 2, timeout_sec: int = 30) -> str:
        """Add a task to the queue. Returns task_id."""
        task = Task(
            priority=priority, name=name, fn=fn,
            args=args, kwargs=kwargs or {},
            retries=retries, timeout_sec=timeout_sec
        )
        self._queue.put(task)
        self._bus.publish("task.queued", {
            "task_id": task.task_id, "name": name, "priority": priority
        }, source="task_queue")
        return task.task_id

    def get_result(self, task_id: str) -> Optional[Any]:
        return self._results.get(task_id)

    def depth(self) -> int:
        return self._queue.qsize()

    def drain(self) -> None:
        """Shutdown: wait for queue to empty, then stop worker."""
        self._queue.join()
        self._running = False

    def _worker_loop(self) -> None:
        while self._running:
            try:
                task: Task = self._queue.get(timeout=1)
            except queue.Empty:
                continue

            task.status = "running"
            task.attempts += 1
            self._bus.publish("task.started", {
                "task_id": task.task_id, "name": task.name,
                "attempt": task.attempts
            }, source="task_queue")

            try:
                result = task.fn(*task.args, **task.kwargs)
                task.status = "completed"
                self._results[task.task_id] = result
                self._bus.publish("task.completed", {
                    "task_id": task.task_id, "name": task.name
                }, source="task_queue")
            except Exception as e:
                logger.warning(f"TaskQueue: task '{task.name}' failed: {e} "
                               f"(attempt {task.attempts}/{task.retries+1})")
                if task.attempts <= task.retries:
                    # Re-queue with same priority
                    self._queue.put(task)
                else:
                    task.status = "failed"
                    self._bus.publish("task.failed", {
                        "task_id": task.task_id, "name": task.name,
                        "error": str(e)
                    }, source="task_queue")
            finally:
                self._queue.task_done()
```

---

### 1.5 Resource Manager

**File:** `app/core/resource_manager.py`

**Purpose:** Monitor RAM, CPU, and enforce hard limits to prevent Render OOM kills.

```python
"""
app/core/resource_manager.py — RAM and CPU watchdog for Render

Polls system resources every 30 seconds.
Takes automated action before Render kills the process.

Thresholds (MB):
  200 → evict LRU cache
  230 → shutdown idle services
  250 → publish system.memory.warning
  270 → force garbage collect + publish system.memory.critical
  290 → emergency: reject new requests until RAM drops
"""

import gc
import logging
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False


class ResourceManager:
    EVICT_CACHE_MB     = 200
    IDLE_SHUTDOWN_MB   = 230
    WARNING_MB         = 250
    CRITICAL_MB        = 270
    EMERGENCY_MB       = 290
    POLL_INTERVAL_SEC  = 30

    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._event_bus = None   # Set lazily after kernel boots event bus
        self._emergency = False  # If True, reject new requests

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(
            target=self._poll_loop, daemon=True, name="ResourceManager"
        )
        self._thread.start()
        logger.info("ResourceManager: started.")

    def stop(self) -> None:
        self._running = False

    def get_ram_mb(self) -> float:
        """Return current process RAM in MB."""
        if _HAS_PSUTIL:
            import os
            proc = psutil.Process(os.getpid())
            return proc.memory_info().rss / 1024 / 1024
        return 0.0

    def get_cpu_percent(self) -> float:
        if _HAS_PSUTIL:
            return psutil.cpu_percent(interval=0.1)
        return 0.0

    def snapshot(self) -> dict:
        return {
            "ram_mb": round(self.get_ram_mb(), 1),
            "cpu_percent": round(self.get_cpu_percent(), 1),
            "emergency_mode": self._emergency,
        }

    def is_emergency(self) -> bool:
        return self._emergency

    def _poll_loop(self) -> None:
        while self._running:
            try:
                self._enforce_limits()
            except Exception as e:
                logger.error(f"ResourceManager poll error: {e}")
            time.sleep(self.POLL_INTERVAL_SEC)

    def _enforce_limits(self) -> None:
        ram = self.get_ram_mb()
        if ram == 0:
            return

        if ram >= self.EMERGENCY_MB:
            self._emergency = True
            logger.critical(f"ResourceManager: EMERGENCY — RAM {ram:.0f} MB, rejecting requests")
            gc.collect()
            self._publish("system.memory.critical", {"ram_mb": ram, "emergency": True})

        elif ram >= self.CRITICAL_MB:
            self._emergency = False
            logger.error(f"ResourceManager: CRITICAL — RAM {ram:.0f} MB, force GC")
            gc.collect()
            self._publish("system.memory.critical", {"ram_mb": ram})

        elif ram >= self.WARNING_MB:
            self._emergency = False
            logger.warning(f"ResourceManager: WARNING — RAM {ram:.0f} MB")
            self._publish("system.memory.warning", {"ram_mb": ram})

        elif ram >= self.IDLE_SHUTDOWN_MB:
            logger.info(f"ResourceManager: idle services check — RAM {ram:.0f} MB")
            self._publish("system.idle.check", {"ram_mb": ram})

        elif ram >= self.EVICT_CACHE_MB:
            logger.info(f"ResourceManager: evicting cache — RAM {ram:.0f} MB")
            self._publish("system.cache.evict", {"ram_mb": ram})

        else:
            if self._emergency:
                self._emergency = False
                logger.info(f"ResourceManager: RAM recovered to {ram:.0f} MB")

    def _publish(self, event: str, payload: dict) -> None:
        if self._event_bus is None:
            try:
                from app.core.event_bus import get_event_bus
                self._event_bus = get_event_bus()
            except Exception:
                return
        try:
            self._event_bus.publish(event, payload, source="resource_manager")
        except Exception as e:
            logger.warning(f"ResourceManager: could not publish event: {e}")
```

---

## Phase 2 — Brain System

### 2.1 Subconscious Brain

**File:** `app/brain/subconscious.py`

**Handles:** All instant actions — no LLM, no waiting. Pure Python.

**Target Latency:** < 300 ms

```python
"""
app/brain/subconscious.py — Fast reflex brain for AND9

Handles all instant device commands without LLM calls.
If it can handle the intent, it executes immediately.

Intent mapping to handler:
  open_app        → app_actions.launch_app()
  close_app       → app_actions.close_app()
  play_music      → youtube_actions.play_music() / spotify
  set_alarm       → alarm_actions.set_alarm()
  set_timer       → timer_actions.set_timer()
  set_reminder    → reminder_actions.set_reminder()
  make_call       → call_actions.make_call()
  volume_up       → device_actions.volume_up()
  volume_down     → device_actions.volume_down()
  wifi_on/off     → device_actions.toggle_wifi()
  bluetooth_on/off→ bluetooth_actions.toggle_bluetooth()
  flashlight_on/off → device_actions.toggle_flashlight()
  brightness      → device_actions.set_brightness()
  camera_open     → app_actions.launch_camera()
"""

import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

# All intents that can be handled without LLM
SUBCONSCIOUS_INTENTS = {
    "open_app", "close_app", "launch_app",
    "play_music", "pause_music", "stop_music", "next_track", "prev_track",
    "set_alarm", "cancel_alarm",
    "set_timer", "cancel_timer",
    "set_reminder",
    "make_call", "end_call",
    "volume_up", "volume_down", "mute", "unmute",
    "brightness_up", "brightness_down", "set_brightness",
    "wifi_on", "wifi_off",
    "bluetooth_on", "bluetooth_off",
    "flashlight_on", "flashlight_off",
    "camera_open", "gallery_open",
    "send_sms",           # Requires confirmation → still subconscious routing
    "contacts_open",
    "calculator_open",
    "settings_open",
    "go_home",
    "go_back",
    "take_screenshot",
}


class SubconsciousBrain:
    """
    Instant, rule-based handler.
    No LLM. No network. Response within 300 ms.
    """

    def can_handle(self, intent: str) -> bool:
        return intent in SUBCONSCIOUS_INTENTS

    def execute(self, intent: str, entities: dict,
                user_id: str = "default") -> dict:
        """
        Execute a device action.
        Returns: {"success": bool, "response": str, "action": str, "latency_ms": int}
        """
        t_start = time.time()
        try:
            result = self._dispatch(intent, entities)
            latency_ms = int((time.time() - t_start) * 1000)
            return {
                "success": result.get("success", True),
                "response": result.get("response", "Done."),
                "action": intent,
                "latency_ms": latency_ms,
                "brain": "subconscious",
            }
        except Exception as e:
            logger.error(f"SubconsciousBrain: failed to execute '{intent}': {e}")
            return {
                "success": False,
                "response": f"Could not execute {intent}. Please try again.",
                "action": intent,
                "latency_ms": int((time.time() - t_start) * 1000),
                "brain": "subconscious",
                "error": str(e),
            }

    def _dispatch(self, intent: str, entities: dict) -> dict:
        """Map intent to the correct android action handler."""
        from app.android.actions import (
            app_actions, alarm_actions, timer_actions,
            reminder_actions, call_actions, device_actions,
            bluetooth_actions, youtube_actions
        )

        dispatch_map = {
            "open_app":       lambda: app_actions.launch_app(entities.get("app", "")),
            "play_music":     lambda: youtube_actions.play_music(entities.get("query", "")),
            "set_alarm":      lambda: alarm_actions.set_alarm(entities),
            "set_timer":      lambda: timer_actions.set_timer(entities),
            "set_reminder":   lambda: reminder_actions.set_reminder(entities),
            "make_call":      lambda: call_actions.make_call(entities.get("contact", "")),
            "volume_up":      lambda: device_actions.volume_up(),
            "volume_down":    lambda: device_actions.volume_down(),
            "wifi_on":        lambda: device_actions.toggle_wifi(True),
            "wifi_off":       lambda: device_actions.toggle_wifi(False),
            "bluetooth_on":   lambda: bluetooth_actions.toggle_bluetooth(True),
            "bluetooth_off":  lambda: bluetooth_actions.toggle_bluetooth(False),
            "flashlight_on":  lambda: device_actions.toggle_flashlight(True),
            "flashlight_off": lambda: device_actions.toggle_flashlight(False),
            "camera_open":    lambda: app_actions.launch_camera(),
            "go_home":        lambda: device_actions.go_home(),
            "take_screenshot":lambda: device_actions.take_screenshot(),
        }

        handler = dispatch_map.get(intent)
        if handler:
            return handler() or {"success": True, "response": "Done."}
        return {"success": False, "response": f"No handler for intent: {intent}"}
```

---

### 2.2 Conscious Brain

**File:** `app/brain/conscious.py`

**Handles:** Complex reasoning, LLM calls, multi-step planning. Uses existing `brain.py`.

```python
"""
app/brain/conscious.py — Deep reasoning brain for AND9

Wraps the existing LLM pipeline (app/core/brain.py).
Used for: research, coding, writing, complex planning,
          long conversations, multi-step workflows.

Target latency: 1–10 seconds depending on task.
"""

import logging
from typing import Optional
from app.core.brain import ask_llm
from app.core.memory import get_memory
from app.core.context_builder import ContextBuilder
from app.core.understanding import MessageAnalysis

logger = logging.getLogger(__name__)


class ConsciousBrain:
    """
    LLM-powered deep reasoning engine.
    Uses Groq (primary) → Opencode Zen (fallback).
    """

    def __init__(self):
        self._memory = get_memory()
        self._context_builder = ContextBuilder()

    def think(self, query: str, analysis: Optional[MessageAnalysis] = None,
              session_id: int = 0) -> dict:
        """
        Process a complex query using the LLM.
        Returns: {"success": bool, "response": str, "brain": "conscious", ...}
        """
        import time
        t_start = time.time()

        try:
            # Build context from memory
            context = self._context_builder.build(
                query=query,
                session_id=session_id,
                intent=analysis.intent if analysis else "chat",
                memory=self._memory
            )

            # Ask LLM
            response = ask_llm(
                messages=context.get("messages", []),
                query=query,
                task=analysis.intent if analysis else "chat"
            )

            latency_ms = int((time.time() - t_start) * 1000)
            return {
                "success": True,
                "response": response or "I couldn't generate a response. Please try again.",
                "brain": "conscious",
                "latency_ms": latency_ms,
            }

        except Exception as e:
            logger.error(f"ConsciousBrain.think failed: {e}", exc_info=True)
            return {
                "success": False,
                "response": "I encountered an error processing your request.",
                "brain": "conscious",
                "error": str(e),
                "latency_ms": int((time.time() - t_start) * 1000),
            }
```

---

### 2.3 Brain Manager

**File:** `app/brain/manager.py`

**Purpose:** Decides which brain handles each request. Routes through Event Bus.

```python
"""
app/brain/manager.py — Brain routing and coordination for AND9

Receives processed intent → decides routing:
  - Subconscious: instant device actions (< 300 ms)
  - Conscious:    LLM reasoning (1–10 s)

Routing logic:
  1. Extract intent from UnderstandingEngine
  2. If intent in SubconsciousBrain.SUBCONSCIOUS_INTENTS → SubconsciousBrain
  3. Else if 'device' route from IntentRouter → SubconsciousBrain
  4. Else → ConsciousBrain
"""

import logging
from typing import Optional
from app.core.understanding import UnderstandingEngine
from app.core.event_bus import EventBus, Event
from app.core.task_queue import TaskQueue, Priority
from app.brain.subconscious import SubconsciousBrain
from app.brain.conscious import ConsciousBrain

logger = logging.getLogger(__name__)


class BrainManager:
    def __init__(self, event_bus: EventBus, task_queue: TaskQueue):
        self._bus = event_bus
        self._queue = task_queue
        self._understanding = UnderstandingEngine()
        self._subconscious = SubconsciousBrain()
        self._conscious = ConsciousBrain()

        # Subscribe to input events
        self._bus.subscribe("input.text", self._on_input)
        self._bus.subscribe("input.voice", self._on_input)

    def process(self, text: str, request_id: str = "",
                session_id: int = 0) -> dict:
        """
        Main entry point called by the Kernel.
        Analyzes → routes → executes → returns result.
        """
        # 1. Understand the input
        analysis = self._understanding.analyze(text)

        self._bus.publish("intent.detected", {
            "request_id": request_id,
            "intent": analysis.intent,
            "entities": analysis.entities,
        }, source="brain_manager")

        # 2. Route decision
        if self._subconscious.can_handle(analysis.intent):
            brain = "subconscious"
            priority = Priority.HIGH
        else:
            brain = "conscious"
            priority = Priority.MEDIUM

        self._bus.publish("intent.routed", {
            "request_id": request_id,
            "brain": brain,
        }, source="brain_manager")

        # 3. Execute through Task Queue
        if brain == "subconscious":
            fn = lambda: self._subconscious.execute(
                analysis.intent, analysis.entities
            )
        else:
            fn = lambda: self._conscious.think(
                text, analysis, session_id=session_id
            )

        task_id = self._queue.enqueue(
            fn=fn,
            name=f"{brain}.{analysis.intent}",
            priority=priority
        )

        # 4. Wait for result (synchronous for now — async in v6.0)
        # Simple polling since task queue is in-process
        import time
        deadline = time.time() + 15  # 15s max wait
        while time.time() < deadline:
            result = self._queue.get_result(task_id)
            if result is not None:
                return result
            time.sleep(0.05)

        return {
            "success": False,
            "response": "Request timed out. Please try again.",
            "brain": brain,
        }

    def _on_input(self, event: Event) -> None:
        """Event handler for input events (called by Event Bus)."""
        text = event.payload.get("text", "")
        if text:
            self.process(text, request_id=event.payload.get("request_id", ""))
```

---

## Phase 3 — Android Services Layer

### 3.1 Services to Create

**Files:** `app/services/`

Each service wraps existing android action files as a `BaseService`.

```
app/services/
├── base_service.py         ← BaseService (already defined in Step 1.3)
├── memory_service.py       ← Wraps app/core/memory.py
├── chat_service.py         ← Wraps app/brain/conscious.py
├── intent_service.py       ← Wraps app/core/understanding.py
├── android_service.py      ← Wraps app/android/executor.py
├── timer_service.py        ← Wraps app/core/timer.py
└── event_service.py        ← Wraps app/core/events.py
```

**Example — MemoryService:**

```python
"""app/services/memory_service.py"""
from app.core.service_manager import BaseService
from app.core.memory import get_memory

class MemoryService(BaseService):
    name = "MemoryService"
    lazy = False
    ram_estimate_mb = 20

    def initialize(self):
        self._mem = get_memory()

    def health_check(self) -> bool:
        return self._mem is not None

    def shutdown(self):
        pass  # Memory persists across requests
```

---

## Phase 4 — Plugin System

### 4.1 Plugin Registry

**File:** `app/plugins/__init__.py`

```python
"""
app/plugins/__init__.py — Plugin registry for AND9

Plugins extend AND9 without modifying the kernel.
Each plugin declares which intents it handles.

Auto-discovery: all folders in app/plugins/ with a plugin.py
are auto-loaded on startup.
"""

import importlib
import logging
import os
from typing import Dict, Optional
from app.plugins.base_plugin import BasePlugin

logger = logging.getLogger(__name__)
_registry: Dict[str, BasePlugin] = {}
_intent_map: Dict[str, str] = {}   # intent → plugin name


def load_all_plugins() -> None:
    """Auto-discover and load all plugins."""
    plugins_dir = os.path.dirname(__file__)
    for folder in os.listdir(plugins_dir):
        plugin_py = os.path.join(plugins_dir, folder, "plugin.py")
        if os.path.isfile(plugin_py):
            _load_plugin(folder)


def _load_plugin(name: str) -> None:
    try:
        mod = importlib.import_module(f"app.plugins.{name}.plugin")
        plugin: BasePlugin = mod.Plugin()
        plugin.initialize()
        _registry[plugin.name] = plugin
        for intent in plugin.intents:
            _intent_map[intent] = plugin.name
        logger.info(f"Plugin loaded: {plugin.name}")
    except Exception as e:
        logger.error(f"Failed to load plugin '{name}': {e}")


def get_plugin_for_intent(intent: str) -> Optional[BasePlugin]:
    name = _intent_map.get(intent)
    return _registry.get(name) if name else None
```

**File:** `app/plugins/base_plugin.py`

```python
"""app/plugins/base_plugin.py — Plugin contract"""

class BasePlugin:
    name: str = "unnamed_plugin"
    version: str = "1.0"
    intents: list = []
    ram_estimate_mb: int = 5
    lazy: bool = True

    def initialize(self) -> None:
        pass

    def handle(self, intent: str, entities: dict) -> dict:
        raise NotImplementedError

    def health_check(self) -> bool:
        return True

    def shutdown(self) -> None:
        pass
```

---

## Phase 5 — Memory & Learning

### 5.1 Memory Tier Enforcement

**File:** `app/core/memory.py` — Extend existing with tier limits.

**Add these constants and cleanup methods to memory.py:**

```python
# Memory tier limits
WORKING_MEMORY_LIMIT    = 50    # items per session
CONVERSATION_LIMIT      = 500   # messages per user
LONG_TERM_LIMIT         = 5000  # facts per user (compressed if exceeded)
CACHE_LIMIT_MB          = 40    # in-memory cache max

# Cleanup schedules
WORKING_MEMORY_TTL_HOURS     = 24
CONVERSATION_MEMORY_TTL_DAYS = 7
CACHE_TTL_SECONDS            = 3600

# Add to Memory class:
def enforce_working_memory_limit(self, session_id: int) -> None:
    """Drop oldest working memory items when limit exceeded."""

def enforce_conversation_limit(self, user_id: str) -> None:
    """Archive oldest conversations when limit exceeded."""

def compress_long_term_memory(self, user_id: str) -> None:
    """Summarize and compress old memories to save tokens."""

def evict_cache(self) -> None:
    """LRU eviction of in-memory cache items."""
```

### 5.2 Learning Engine

**File:** `app/core/learning.py`

```python
"""
app/core/learning.py — Pattern learning engine for AND9

Tracks user behaviour to provide better suggestions and
automate repetitive tasks.

What it learns:
  - Frequently used apps (top 10 tracked)
  - Typical alarm times ("user usually sets alarm at 7 AM")
  - Common phrases ("play music" → user prefers YouTube)
  - User corrections (wrong answer → store correction)
  - Command shortcuts ("YT" means "open YouTube")
"""

import logging
from collections import defaultdict, Counter
from typing import Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


class LearningEngine:
    def __init__(self, memory):
        self._mem = memory
        self._app_usage: Counter = Counter()
        self._command_patterns: Dict[str, int] = defaultdict(int)
        self._corrections: List[dict] = []

    def observe(self, query: str, intent: str,
                response: str, success: bool) -> None:
        """Record an interaction for learning."""
        self._command_patterns[intent] += 1

    def record_app_open(self, app_name: str) -> None:
        """Track which apps are opened most often."""
        self._app_usage[app_name] += 1

    def record_correction(self, wrong: str, correct: str,
                          query: str) -> None:
        """User corrected JARVIS — remember this."""
        self._corrections.append({
            "query": query, "wrong": wrong,
            "correct": correct,
            "timestamp": datetime.utcnow().isoformat()
        })

    def get_frequent_apps(self, top_n: int = 5) -> List[str]:
        """Return top N most used apps."""
        return [app for app, _ in self._app_usage.most_common(top_n)]

    def get_patterns(self) -> Dict[str, int]:
        return dict(self._command_patterns)

    def suggest(self, context: dict) -> List[str]:
        """Suggest likely next actions based on context."""
        suggestions = []
        hour = datetime.now().hour
        if 6 <= hour <= 9:
            suggestions.append("Set morning alarm")
        frequent_apps = self.get_frequent_apps(3)
        for app in frequent_apps:
            suggestions.append(f"Open {app}")
        return suggestions
```

---

## Phase 6 — Security Layer

**File:** `app/core/security_manager.py`

```python
"""
app/core/security_manager.py — Security layer for AND9

All actions pass through security before execution.

Risk levels:
  SAFE      → execute immediately
  LOW       → execute + notify
  MEDIUM    → single confirmation required
  HIGH      → typed confirmation required
  BLOCKED   → reject with reason

Sensitive intents that require confirmation:
  delete_file, send_sms, make_call (to unknown contacts)
  send_email, modify_settings, access_private_data
  purchase_action, clear_all_data
"""

import logging
import re
from enum import Enum
from typing import Tuple

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    SAFE    = 0
    LOW     = 1
    MEDIUM  = 2
    HIGH    = 3
    BLOCKED = 4


# Actions and their risk levels
RISK_MAP = {
    "delete_file":       RiskLevel.HIGH,
    "clear_all_data":    RiskLevel.HIGH,
    "send_sms":          RiskLevel.MEDIUM,
    "make_call":         RiskLevel.MEDIUM,
    "send_email":        RiskLevel.MEDIUM,
    "modify_settings":   RiskLevel.MEDIUM,
    "purchase_action":   RiskLevel.HIGH,
    "access_contacts":   RiskLevel.LOW,
    "access_location":   RiskLevel.LOW,
    "take_screenshot":   RiskLevel.LOW,
    "open_app":          RiskLevel.SAFE,
    "play_music":        RiskLevel.SAFE,
    "set_alarm":         RiskLevel.SAFE,
    "set_timer":         RiskLevel.SAFE,
    "volume_up":         RiskLevel.SAFE,
    "volume_down":       RiskLevel.SAFE,
    "wifi_on":           RiskLevel.SAFE,
    "wifi_off":          RiskLevel.SAFE,
}


class SecurityManager:
    def assess(self, intent: str, entities: dict) -> Tuple[RiskLevel, str]:
        """
        Returns (risk_level, reason_string).
        Caller decides whether to execute or prompt for confirmation.
        """
        # 1. Validate input
        if not intent or not isinstance(intent, str):
            return RiskLevel.BLOCKED, "Invalid intent."

        # 2. Sanitize entities
        for key, val in (entities or {}).items():
            if isinstance(val, str) and self._looks_dangerous(val):
                return RiskLevel.BLOCKED, f"Dangerous value in '{key}'."

        # 3. Look up risk map
        risk = RISK_MAP.get(intent, RiskLevel.LOW)
        reason = self._build_reason(intent, risk)
        return risk, reason

    def _looks_dangerous(self, value: str) -> bool:
        """Detect potential injection or traversal attempts."""
        patterns = [r"\.\.\/", r";\s*rm\s", r"<script", r"DROP TABLE",
                    r"eval\(", r"exec\("]
        return any(re.search(p, value, re.IGNORECASE) for p in patterns)

    def _build_reason(self, intent: str, risk: RiskLevel) -> str:
        reasons = {
            RiskLevel.SAFE:    "Safe to execute.",
            RiskLevel.LOW:     f"'{intent}' accesses personal data.",
            RiskLevel.MEDIUM:  f"'{intent}' requires your confirmation.",
            RiskLevel.HIGH:    f"'{intent}' is a high-risk action. Type CONFIRM to proceed.",
            RiskLevel.BLOCKED: f"'{intent}' is not allowed.",
        }
        return reasons.get(risk, "Unknown risk.")

    def audit_log(self, intent: str, entities: dict,
                  risk: RiskLevel, executed: bool) -> None:
        """Write every action to the audit trail."""
        logger.info(
            f"AUDIT | intent={intent} | risk={risk.name} | "
            f"executed={executed} | entities_keys={list((entities or {}).keys())}"
        )
```

---

## Phase 7 — Observability

**File:** `app/core/observability.py`

```python
"""
app/core/observability.py — Health + metrics for AND9

Exposes a /health endpoint with:
  - Kernel status
  - All service statuses
  - RAM + CPU snapshot
  - Task queue depth
  - Request counters
  - Error rates
"""

import logging
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.core.kernel import AND9Kernel

logger = logging.getLogger(__name__)
_request_count = 0
_error_count = 0


class Observability:
    def __init__(self, kernel: "AND9Kernel"):
        self._kernel = kernel

    def report(self) -> dict:
        """Full health report for /health endpoint."""
        global _request_count, _error_count
        kernel_health = self._kernel.health()
        return {
            "and9_version": "5.0",
            "status": "running",
            "requests_total": _request_count,
            "errors_total": _error_count,
            "error_rate": round(_error_count / max(_request_count, 1), 4),
            **kernel_health,
        }

    @staticmethod
    def record_request() -> None:
        global _request_count
        _request_count += 1

    @staticmethod
    def record_error() -> None:
        global _error_count
        _error_count += 1
```

---

## Phase 8 — API Refactor

**File:** `app/api/routes.py` — Route all requests through the Kernel.

```python
# Replace direct Orchestrator calls with Kernel routing:

# OLD (before v5.0):
result = get_orch().run(message)

# NEW (v5.0):
from app.core.kernel import get_kernel
result = get_kernel().handle_request(message)
```

**File:** `app/main.py` — Boot Kernel on app start.

```python
# Add to create_app() after blueprints:
from app.core.kernel import get_kernel
kernel = get_kernel()
kernel.boot()
```

**File:** `app/api/web_routes.py` — Add /health route:

```python
@web_bp.route("/api/v5/health")
def kernel_health():
    from app.core.kernel import get_kernel
    return jsonify(get_kernel().health())
```

---

## Refactor Plan for Existing Files

| File | Action | Reason |
| :--- | :--- | :--- |
| `orchestrator.py` | Keep + gradually delegate to BrainManager | Backward compat |
| `understanding.py` | Wrap in IntentService | Plug into Event Bus |
| `memory.py` | Add tier limits + cleanup | Prevent OOM |
| `brain.py` | No change — called by ConsciousBrain | Already good |
| `events.py` | Wrap in EventService | Lifecycle control |
| `working_memory.py` | No change | Already well structured |
| `action_registry.py` | Subscribe to Event Bus events | Decouple from orchestrator |
| `api/routes.py` | Route through Kernel | Remove orchestrator dependency |
| `main.py` | Boot Kernel | Single boot point |

---

## Final File Tree

```
and9/
├── app/
│   ├── core/
│   │   ├── kernel.py              ← NEW — AI Kernel
│   │   ├── event_bus.py           ← NEW — Event Bus
│   │   ├── service_manager.py     ← NEW — Service lifecycle
│   │   ├── task_queue.py          ← NEW — Priority queue
│   │   ├── resource_manager.py    ← NEW — RAM watchdog
│   │   ├── security_manager.py    ← NEW — Security + audit
│   │   ├── observability.py       ← NEW — Health + metrics
│   │   ├── learning.py            ← NEW — Pattern learning
│   │   ├── orchestrator.py        ← KEEP + delegate to BrainManager
│   │   ├── understanding.py       ← KEEP (wrap in IntentService)
│   │   ├── memory.py              ← EXTEND (tier limits)
│   │   ├── brain.py               ← KEEP (already good)
│   │   ├── working_memory.py      ← KEEP
│   │   ├── events.py              ← KEEP (wrap in EventService)
│   │   ├── goal_tracker.py        ← KEEP
│   │   ├── reflection.py          ← KEEP
│   │   ├── config.py              ← KEEP
│   │   └── truth_engine.py        ← KEEP
│   │
│   ├── brain/
│   │   ├── __init__.py            ← NEW
│   │   ├── manager.py             ← NEW — Brain router
│   │   ├── subconscious.py        ← NEW — Fast reflex brain
│   │   ├── conscious.py           ← NEW — Deep reasoning
│   │   └── planner.py             ← NEW — Multi-step planner
│   │
│   ├── services/
│   │   ├── base_service.py        ← NEW (or inline in service_manager)
│   │   ├── memory_service.py      ← NEW
│   │   ├── chat_service.py        ← NEW
│   │   ├── intent_service.py      ← NEW
│   │   ├── android_service.py     ← NEW
│   │   ├── timer_service.py       ← NEW
│   │   └── event_service.py       ← NEW
│   │
│   ├── plugins/
│   │   ├── __init__.py            ← NEW — Plugin registry
│   │   ├── base_plugin.py         ← NEW
│   │   ├── weather/plugin.py      ← NEW
│   │   ├── calculator/plugin.py   ← NEW
│   │   └── spotify/plugin.py      ← NEW
│   │
│   ├── android/                   ← KEEP existing (actions/, apps/, etc.)
│   ├── api/                       ← REFACTOR routes.py
│   ├── templates/                 ← KEEP
│   ├── static/                    ← KEEP
│   └── main.py                    ← EXTEND (boot kernel)
│
├── Planned.md                     ← This file
├── ROADMAP.md                     ← Architecture blueprint
└── requirements.txt               ← Add psutil
```

---

## Week-by-Week Schedule

### Week 1 — Core Infrastructure
- [ ] `app/core/event_bus.py`
- [ ] `app/core/kernel.py`
- [ ] `app/core/service_manager.py`
- [ ] Boot kernel from `app/main.py`

### Week 2 — Execution Engine
- [ ] `app/core/task_queue.py`
- [ ] `app/core/resource_manager.py`
- [ ] Add `psutil` to `requirements.txt`

### Week 3 — Brain System
- [ ] `app/brain/__init__.py`
- [ ] `app/brain/subconscious.py`
- [ ] `app/brain/conscious.py`
- [ ] `app/brain/manager.py`
- [ ] Update `app/api/routes.py` to route through Kernel

### Week 4 — Services & Plugins
- [ ] `app/services/` (all 6 service files)
- [ ] `app/plugins/__init__.py`
- [ ] `app/plugins/base_plugin.py`
- [ ] First plugin: `app/plugins/weather/plugin.py`

### Week 5 — Memory & Security
- [ ] Extend `app/core/memory.py` with tier limits
- [ ] `app/core/learning.py`
- [ ] `app/core/security_manager.py`

### Week 6 — Observability & Deployment
- [ ] `app/core/observability.py`
- [ ] `/api/v5/health` endpoint
- [ ] RAM budget test on Render (idle < 180 MB, peak < 280 MB)
- [ ] Full integration test
- [ ] Push v5.0 tag

---

## Success Metrics

| Metric | Target | How to Measure |
| :--- | :--- | :--- |
| Command recognition rate | ≥ 95% | Test suite: 100 sample commands |
| Subconscious response time | < 300 ms | `latency_ms` field in response |
| Conscious response time | < 10 s | `latency_ms` field in response |
| Crash rate | < 1 per 1,000 requests | Error count in Observability |
| Idle RAM (Render) | < 180 MB | ResourceManager snapshot |
| Peak RAM (Render) | < 280 MB | ResourceManager peak tracking |
| Service startup time | < 5 seconds | Kernel boot log |
| Uptime | ≥ 99% | Render dashboard |
| Test coverage | ≥ 80% | pytest --cov |

---

## Dependencies to Add

```
# requirements.txt additions:
psutil>=5.9.0          # RAM + CPU monitoring for ResourceManager
```

---

> **Next Action:** Start with `app/core/event_bus.py` — the foundation everything else builds on.
