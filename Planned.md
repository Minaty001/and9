# AND9 — Full Implementation Plan

> **Status:** Active Development
> **Current Phase:** Phase 1 — Core Foundation
> **Architecture Target:** AND9 v5.0 AI Operating System

---

## Quick Reference

| Layer | Component | Status |
| :--- | :--- | :--- |
| AI Kernel | `app/core/kernel.py` | 🔴 Not started |
| Event Bus | `app/core/event_bus.py` | 🔴 Not started |
| Service Manager | `app/core/service_manager.py` | 🔴 Not started |
| Subconscious Brain | `app/brain/subconscious.py` | 🔴 Not started |
| Conscious Brain | `app/brain/conscious.py` | 🔴 Not started |
| Brain Manager | `app/brain/manager.py` | 🟡 Partial (orchestrator.py) |
| Intent Router | `app/core/understanding.py` | 🟢 Exists |
| Memory System | `app/core/memory.py` | 🟢 Exists |
| Plugin Registry | `app/plugins/__init__.py` | 🔴 Not started |
| Task Queue | `app/core/task_queue.py` | 🔴 Not started |
| Resource Manager | `app/core/resource_manager.py` | 🔴 Not started |
| Security Manager | `app/core/security_manager.py` | 🔴 Not started |
| Observability | `app/core/observability.py` | 🔴 Not started |
| Android Services | `app/android/` | 🟡 Partial |
| Skill System | `app/skills/` | 🟡 Partial |

---

## Phase 1 — Core Foundation

### Step 1.1 — AI Kernel

**File:** `app/core/kernel.py`

**Responsibilities:**
- Boot and stop all services in order
- Maintain a service registry
- Route requests to the Event Bus
- Monitor memory via Resource Manager
- Recover from service failures

```python
# Target Interface
class AND9Kernel:
    def boot() -> None          # Start all services
    def shutdown() -> None      # Graceful shutdown
    def health() -> dict        # Service health map
    def route(request) -> any   # Route to event bus
    def restart_service(name)   # Recover a failed service
```

**Implementation Notes:**
- Singleton pattern — only one kernel per process
- Services start lazily to save RAM
- If a service crashes, kernel retries once then marks it degraded

---

### Step 1.2 — Event Bus

**File:** `app/core/event_bus.py`

**Purpose:** Replace all direct module-to-module calls with async event passing.

**Flow:**
```
Voice Input → publish("voice.input", payload)
Event Bus   → dispatch to Intent Router
Intent      → publish("intent.detected", intent_data)
Event Bus   → dispatch to Planner
Planner     → publish("plan.ready", task_list)
Event Bus   → dispatch to Executor
```

**Target Interface:**
```python
class EventBus:
    def subscribe(event: str, handler: callable) -> None
    def publish(event: str, payload: dict) -> None
    def unsubscribe(event: str, handler: callable) -> None
```

**Standard Events:**
```
voice.input
text.input
intent.detected
intent.routed
plan.created
task.started
task.completed
task.failed
response.ready
memory.updated
service.started
service.stopped
service.failed
```

---

### Step 1.3 — Service Manager

**File:** `app/core/service_manager.py`

**Purpose:** Register, start, stop, and dynamically load/unload services.

**Service Lifecycle:**
```
Registered → Initializing → Ready → Running → Stopping → Stopped
                                  ↘ Failed
```

**Built-in Services (Phase 1):**
```
VoiceService
ChatService
MemoryService
IntentService
LoggingService
```

**Interface:**
```python
class ServiceManager:
    def register(service: BaseService) -> None
    def start(name: str) -> None
    def stop(name: str) -> None
    def status() -> dict              # All service statuses
    def get(name: str) -> BaseService
```

**BaseService Contract:**
```python
class BaseService:
    name: str
    def initialize() -> None
    def health_check() -> bool
    def shutdown() -> None
```

---

### Step 1.4 — Task Queue

**File:** `app/core/task_queue.py`

**Purpose:** Every request enters a priority queue instead of executing directly.

**Priority Levels:**
```
CRITICAL  = 0   # Emergency stop, auth
HIGH      = 1   # Voice commands, app launch
MEDIUM    = 2   # File operations
LOW       = 3   # Cleanup, indexing
```

**Task Lifecycle:**
```
Received → Validated → Queued → Executing → Retrying? → Completed / Failed
```

**Interface:**
```python
class TaskQueue:
    def enqueue(task: Task, priority: int) -> str  # returns task_id
    def get_status(task_id: str) -> dict
    def cancel(task_id: str) -> bool
    def drain() -> None                            # Shutdown flush
```

---

### Step 1.5 — Resource Manager

**File:** `app/core/resource_manager.py`

**Purpose:** Keep Render Free Tier alive by enforcing RAM limits.

**RAM Budget:**
```
Web server:      40 MB
AI client:       30 MB
Memory manager:  20 MB
Cache:           40 MB
Active request: 100 MB
Safety margin:   70 MB
────────────────────
Idle target:   < 180 MB
Peak target:   < 280 MB
```

**Responsibilities:**
- Poll RAM every 30 seconds
- Evict LRU cache when RAM > 200 MB
- Shut down idle services when RAM > 230 MB
- Emit `system.memory.warning` event at 250 MB
- Force garbage collect at 270 MB

**Interface:**
```python
class ResourceManager:
    def get_memory_mb() -> float
    def get_cpu_percent() -> float
    def enforce_limits() -> None
    def evict_cache() -> None
```

---

## Phase 2 — Brain System

### Step 2.1 — Subconscious Brain

**File:** `app/brain/subconscious.py`

**Purpose:** Fast, rule-based handler for instant device commands.

**Target Latency:** < 300 ms

**Handles:**
```
open_app, close_app, volume_up, volume_down
brightness_up, brightness_down
wifi_on, wifi_off, bluetooth_on, bluetooth_off
flashlight_on, flashlight_off
play_music, pause_music, next_track
set_alarm, set_timer, set_reminder
camera_open, gallery_open
call_contact, send_sms (with confirmation)
```

**Decision Logic:**
```python
class SubconsciousBrain:
    def can_handle(intent: str) -> bool
    def execute(intent: str, entities: dict) -> dict
    # Returns within 300ms or raises TimeoutError
```

**Implementation Notes:**
- No LLM calls — pure Python logic and device APIs
- If execution fails, emit `brain.subconscious.failed` event
- Conscious brain never receives subconscious tasks

---

### Step 2.2 — Conscious Brain

**File:** `app/brain/conscious.py`

**Purpose:** Deep reasoning, research, coding, planning via LLM.

**Target Latency:** 1–10 seconds

**Handles:**
```
research, coding, debugging
writing, summarizing, translating
complex planning, decision-making
multi-step workflows
long conversations
```

**Interface:**
```python
class ConsciousBrain:
    def think(query: str, context: dict) -> dict
    def plan(goal: str) -> list[Task]
    def reflect(session: dict) -> str
```

**LLM Chain:**
```
Query → Context Builder → Prompt → Groq (primary) → Opencode (fallback) → Response
```

---

### Step 2.3 — Brain Manager

**File:** `app/brain/manager.py`

**Purpose:** Decides which brain handles each request.

```
Request
   │
   ├── is_instant_action? → SubconsciousBrain (< 300ms)
   │
   └── is_complex_task?  → ConsciousBrain (1-10s)
```

**Routing Rules:**
- If intent confidence > 0.85 AND in subconscious skill list → Subconscious
- If requires LLM reasoning → Conscious
- If ambiguous → ask user OR use Subconscious with fallback message

---

## Phase 3 — Plugin System

### Step 3.1 — Plugin Registry

**File:** `app/plugins/__init__.py`

**Purpose:** Install and load skills as isolated plugins.

**Plugin Structure:**
```
app/plugins/
├── __init__.py             # Registry
├── base_plugin.py          # Base class
├── spotify/
│   ├── __init__.py
│   ├── plugin.py
│   └── manifest.json
├── whatsapp/
├── telegram/
├── weather/
├── calculator/
├── ocr/
└── camera/
```

**Manifest Format:**
```json
{
  "name": "spotify",
  "version": "1.0",
  "description": "Play music on Spotify",
  "intents": ["play_music", "pause_music", "next_track"],
  "permissions": ["INTERNET"],
  "ram_mb": 5,
  "lazy_load": true
}
```

**Base Plugin Contract:**
```python
class BasePlugin:
    name: str
    intents: list[str]

    def initialize() -> None
    def handle(intent: str, entities: dict) -> dict
    def health_check() -> bool
    def shutdown() -> None
```

---

## Phase 4 — Memory & Learning

### Step 4.1 — Memory Hierarchy

**Files:** `app/core/memory.py` (extend existing)

**Memory Tiers:**
```
Working Memory      ← current conversation (max 50 items, TTL: session)
Conversation Memory ← recent exchanges (max 500 items, TTL: 7 days)
Long-Term Memory    ← important facts (persistent, compressed monthly)
Knowledge Base      ← user preferences, learned patterns (persistent)
Archive             ← compressed old memories (Supabase cold storage)
```

**Cleanup Policy:**
- Working memory cleared every session
- Conversation memory pruned weekly
- Long-term memory compressed monthly
- Archive reviewed quarterly

---

### Step 4.2 — Learning Engine

**File:** `app/core/learning.py`

**Purpose:** Track patterns, store preferences, improve responses over time.

**What It Learns:**
- Frequently used apps
- Preferred response style
- Recurring tasks and times
- User corrections to JARVIS
- Common command phrasing

**Interface:**
```python
class LearningEngine:
    def observe(query: str, response: str, feedback: str) -> None
    def get_preferences() -> dict
    def get_patterns() -> list
    def suggest(context: dict) -> list[str]
```

---

## Phase 5 — Security Layer

### Step 5.1 — Security Manager

**File:** `app/core/security_manager.py`

**Every request passes through:**
```
Input → Sanitize → Validate → Permission Check → Risk Score → Execute → Audit Log
```

**Risk Levels:**
```
SAFE       - No confirmation needed (open app, check time)
LOW_RISK   - Proceed with toast notification
MEDIUM     - Single confirmation dialog
HIGH       - Explicit typed confirmation required
BLOCKED    - Rejected with reason
```

**Sensitive Actions (require confirmation):**
```
delete_file, send_sms, make_call
send_email, modify_settings
access_contacts, access_location
purchase_action
```

---

## Phase 6 — Observability

### Step 6.1 — Metrics & Health

**File:** `app/core/observability.py`

**Each service exposes:**
```python
{
  "name": "MemoryService",
  "status": "running",
  "ram_mb": 22.4,
  "cpu_percent": 1.2,
  "request_count": 1842,
  "error_count": 3,
  "avg_latency_ms": 45
}
```

**Health endpoint:** `GET /health` → returns kernel health map

---

## Implementation Order

```
Week 1
  └── Step 1.1: AI Kernel
  └── Step 1.2: Event Bus
  └── Step 1.3: Service Manager

Week 2
  └── Step 1.4: Task Queue
  └── Step 1.5: Resource Manager

Week 3
  └── Step 2.1: Subconscious Brain
  └── Step 2.2: Conscious Brain
  └── Step 2.3: Brain Manager

Week 4
  └── Step 3.1: Plugin Registry
  └── First plugins: Weather, Calculator

Week 5
  └── Step 4.1: Memory Hierarchy (extend existing)
  └── Step 4.2: Learning Engine

Week 6
  └── Step 5.1: Security Manager
  └── Step 6.1: Observability
  └── Full integration test
  └── Render deployment check (< 280 MB peak RAM)
```

---

## File Creation Checklist

### New Files to Create

```
app/core/kernel.py              ← AI Kernel
app/core/event_bus.py           ← Event Bus
app/core/service_manager.py     ← Service Manager
app/core/task_queue.py          ← Priority Task Queue
app/core/resource_manager.py    ← RAM / CPU Monitor
app/core/security_manager.py    ← Security Layer
app/core/observability.py       ← Health & Metrics
app/core/learning.py            ← Learning Engine

app/brain/__init__.py           ← Brain package
app/brain/manager.py            ← Brain Manager (router)
app/brain/subconscious.py       ← Fast reflex brain
app/brain/conscious.py          ← Deep reasoning brain
app/brain/planner.py            ← Multi-step planner

app/plugins/__init__.py         ← Plugin registry
app/plugins/base_plugin.py      ← Plugin base class
app/plugins/weather/plugin.py   ← Weather plugin
app/plugins/calculator/plugin.py

app/services/__init__.py        ← Service base package
app/services/voice_service.py
app/services/chat_service.py
app/services/memory_service.py
```

### Existing Files to Refactor

```
app/core/orchestrator.py        ← Migrate to Brain Manager + Event Bus
app/core/understanding.py       ← Plug into Event Bus as IntentService
app/core/memory.py              ← Add tier hierarchy and cleanup
app/api/routes.py               ← Route through Kernel instead of directly
app/main.py                     ← Boot Kernel on app start
```

---

## Success Metrics

| Metric | Target |
| :--- | :--- |
| Command recognition rate | ≥ 95% |
| Intent accuracy | ≥ 95% |
| Subconscious response time | < 300 ms |
| Conscious response time | < 10 s |
| Crash rate | < 1 per 1,000 requests |
| Idle RAM | < 180 MB |
| Peak RAM | < 280 MB |
| Uptime | ≥ 99% |

---

## Notes

- All new files follow the `BaseService` / `BasePlugin` contract.
- No module calls another directly — all communication is through the Event Bus.
- The Kernel is the only global singleton.
- Resources are always cleaned up in `shutdown()` hooks.
- Every action is logged to the audit trail.
