# 🧠 JARVIS PCOS (Personal Cognitive Operating System) — Definitive Repository

Welcome to the official production repository for **JARVIS PCOS (Neural Engine v4)**. This project contains the high-performance Flask AI orchestrator, dynamic intent execution engines, local custom Android client wrappers, an advanced multi-turn dialogue manager, and a code dependency graph analyzer.

> [!IMPORTANT]
> **Use the `and9` repository (`/root/and9`) always** for backend developments, intent executor tasks, custom permission overlays, and Android app updates.

---

## 📜 Constitution V3 — Truth-First Architecture

JARVIS operates under **JARVIS PROJECT CONSTITUTION V3**, a set of non-negotiable rules ensuring truth-centered AI behavior:

| Rule | Principle | Implementation |
|------|-----------|---------------|
| **Rule 1** | Never hallucinate — if info not in context, say "Mujhe nahi pata" | Truth Engine pre-LLM gate, personality prompt |
| **Rule 4** | Never claim memory you don't have | `verify_before_llm()` checks memory before any recall |
| **Rule 5** | Confidence map enforced on all writes | `cap_confidence()` caps by source type |
| **Rule 6** | No LLM inference stored as fact | `extract_facts_from_text()` removed everywhere |
| **Rule 7** | Whitelist-based action execution | Android `ACTION_WHITELIST` + parameter validation |
| **Rule 8** | Source tracking for all memory writes | `source`/`confidence`/`verified` on every record |

### Confidence Map (Rule 5)

| Source | Max Confidence | Example |
|--------|---------------|---------|
| `user_input` / `direct_statement` | 1.0 | User says "My name is Saif" |
| `observed` / `observed_pattern` | 0.7 | User consistently asks about coding |
| `regex_extraction` / `keyword_detection` | 0.3 | Regex matches "in Delhi" from message |
| `llm_inference` | 0.0 ❌ | **Never stored** — constitution violation |

### Processing Pipeline

```
User Input → Intent Router → Memory Retrieval → Truth Engine → Context Builder → LLM → Response → Memory Storage
                                                       │
                                                       └─ No memory? → "Mujhe nahi pata"
```

---

## ⚡ Supported Assistant Commands

JARVIS parses natural language requests and converts them into intent payloads executed natively on Android or via web fallbacks:

*   **Android Operations**: Set Alarms, Open Apps, play YouTube Videos.
*   **Device Management**: Flashlight toggles, WiFi, Battery state, Volume control, Camera access.
*   **Cognitive Pipelines**: Goal tracking, Scheduled Events/Reminders, Session Reflection digests, Web search.
*   **File Operations**: Read/write storage (requires user confirmation on Android).

For exact API payloads, JSON structures, and natural language command examples, refer to the **[Commands Reference & Intent Guide](COMMANDS_REFERENCE.md)**.

---

## 🚀 Backend Quick Start

Ensure Python 3.11+ is installed. Follow these steps to spin up the Neural Engine orchestrator:

```bash
# 1. Install required dependencies
pip install -r requirements.txt

# 2. Configure environment variables (Supabase, LLM providers, keys)
cp .env.example .env
# Edit .env and enter your key credentials

# 3. Apply database schema in Supabase SQL Editor
#    Open app/core/supabase_schema.sql and run in Supabase dashboard

# 4. Spin up the orchestrator server
gunicorn app.main:app
```

---

## 📱 Android Client — Build & Setup

The Android interface is in the `android/` directory.

### Native Source Build
1. Locate or create `android/local.properties`.
2. Configure your server endpoints:
   ```properties
   JARVIS_BASE_URL=https://your-backend-app.onrender.com/api
   ```
3. Compile the debug APK:
   ```bash
   cd android
   ./gradlew assembleDebug
   # Build output: android/app/build/outputs/apk/debug/app-debug.apk
   ```

> **Important**: Android app no longer calls LLMs directly. `chatGroq()` and `chatOpenAI()` have been removed. All AI processing now routes through the server-side orchestration pipeline for truth-verified responses. Direct Groq/OpenAI API keys in the Android app are no longer supported.

### 📦 Custom User APK Rebuilding (Automation)
If you have an existing signed `jarvis.apk` at `/storage/emulated/0/jarvis.apk` and need to safely strip unwanted digital assistant overrides and inject system permissions, run:

```bash
python3 scripts/rebuild_user_apk.py
```

**What this automation script does:**
1. **Decompiles / Extracts** the raw apk assets.
2. **Removes the Digital Assistant service** structure from the Manifest.
3. **Injects high-access permissions** (`MANAGE_EXTERNAL_STORAGE`, `CALL_PHONE`, `READ_CONTACTS`).
4. **Repackages, aligns, and signs** with a generated cryptographic key.
5. **Replaces the file** at `/storage/emulated/0/jarvis.apk` with the final, optimized build.

---

## 🏗 System Architecture

```
and9/
  ├── android/               (Native Android client — no direct LLM calls)
  ├── app/
  │    ├── and9/             ← AND9 — Modular Reflex Intent Engine
  │    │    ├── __init__.py              (Public API — AND9 class, BrainType, IntentType)
  │    │    ├── and9.py                  (Thin orchestrator wrapper)
  │    │    ├── brain_types.py           (BrainType/IntentType enums, BrainResult)
  │    │    ├── conscious_brain.py       (LLM reasoning via JARVIS Orchestrator)
  │    │    ├── subconscious_brain.py    (Pattern learning & habit detection)
  │    │    ├── normalizer.py            (Redirect → router/normalizer.py)
  │    │    │
  │    │    ├── router/                  ← Intent routing pipeline
  │    │    │    ├── normalizer.py       (Hindi → English regex normalization)
  │    │    │    └── intent_router.py    (13-category priority-ordered detection)
  │    │    │
  │    │    ├── dialogue_manager/        ← Multi-turn dialogue engine
  │    │    │    ├── __init__.py         (Public API — DialogueManager, config)
  │    │    │    ├── dialogue_manager.py (Orchestrator — 11-step pipeline)
  │    │    │    ├── intent_definitions.py (Slot definitions per intent)
  │    │    │    ├── slot_filler.py      (Slot filling engine with classifiers)
  │    │    │    ├── state_manager.py    (Dialogue State Tracker — DST)
  │    │    │    ├── task_manager.py     (Multi-task lifecycle orchestration)
  │    │    │    ├── working_memory.py   (Short-term, active, and working memory)
  │    │    │    ├── context_manager.py  (Interruption & context tracking)
  │    │    │    ├── reference_resolver.py (Pronoun & anaphora resolution)
  │    │    │    ├── action_planner.py   (Execution validation & planning)
  │    │    │    └── routes.py           (API endpoints for dialogue)
  │    │    │
  │    │    ├── dependency_graph/        ← Code Dependency Analysis MCP
  │    │    │    ├── graph.py            (Pure-Python directed graph with PageRank)
  │    │    │    ├── analyzer.py         (AST-based Python code parser)
  │    │    │    ├── mcp_server.py       (MCP JSON-RPC 2.0 server over stdio)
  │    │    │    └── routes.py           (FastAPI/Flask-compatible API routes)
  │    │    │
  │    │    ├── intents/                 ← Intent parsers (delegate to router)
  │    │    │    ├── call_intents.py     (Call/SMS parameter extraction)
  │    │    │    ├── alarm_intents.py
  │    │    │    ├── timer_intents.py
  │    │    │    ├── reminder_intents.py
  │    │    │    ├── media_intents.py
  │    │    │    ├── app_intents.py
  │    │    │    └── search_intents.py
  │    │    │
  │    │    ├── actions/                 ← Action executors
  │    │    │    ├── call_actions.py     (Call/SMS with Android contact resolution)
  │    │    │    ├── alarm_actions.py
  │    │    │    ├── timer_actions.py
  │    │    │    ├── reminder_actions.py
  │    │    │    ├── app_actions.py
  │    │    │    ├── youtube_actions.py
  │    │    │    └── device_actions.py   (Flashlight, volume, WiFi, BT, etc.)
  │    │    │
  │    │    ├── android/                 ← Android execution layer
  │    │    │    ├── action_registry.py  (20 actions with Android intent mapping)
  │    │    │    └── android_executor.py (Single entry point for all actions)
  │    │    │
  │    │    ├── contacts/
  │    │    │    └── resolver.py         (Contact name → Android ContactsContract lookup)
  │    │    ├── apps/
  │    │    │    └── package_resolver.py (40+ apps, 50+ aliases)
  │    │    ├── media/
  │    │    │    └── youtube_handler.py  (YouTube app routing only)
  │    │    ├── alarms/
  │    │    │    └── alarm_manager.py
  │    │    ├── timers/
  │    │    │    └── timer_manager.py
  │    │    ├── reminders/
  │    │    │    └── scheduler.py
  │    │    ├── brain/
  │    │    │    └── orchestrator.py     (Full pipeline orchestrator)
  │    │    └── core/
  │    │         ├── logger.py           (Per-request debug logging)
  │    │         ├── constants.py
  │    │         └── config.py
  │    │
  │    │    ├── orchestrator/           ← Agent Orchestrator (Phase 4)
  │    │    │    ├── __init__.py         (Public API — TaskQueue, AgentOrchestrator)
  │    │    │    ├── task_queue.py       (Priority-ordered thread-safe task queue)
  │    │    │    └── orchestrator.py     (Full pipeline: analyze→decompose→execute→validate→retry→merge)
  │    │    │
  │    │    ├── agents/                 ← Multi-Agent System (Phase 3)
  │    │    │    ├── __init__.py         (Public API, factory, 20 agent classes)
  │    │    │    ├── base.py             (AgentBase abstract class, AgentMemory, AgentMetrics)
  │    │    │    ├── registry.py         (AgentRegistry — service locator, routing, delegation)
  │    │    │    ├── core_agents.py      (Executive, Conversation, Planning)
  │    │    │    ├── knowledge_agents.py (Research, Coding, Debug)
  │    │    │    ├── memory_agents.py    (Memory, Learning, Reflection)
  │    │    │    ├── device_agents.py    (Android, Voice, Browser)
  │    │    │    ├── system_agents.py    (Scheduler, Automation, Security, Health)
  │    │    │    └── integration_agents.py (Tool, Integration, Notification, Workflow)
  │    │
  │    ├── agents/           (LLM orchestrators & coding/research agents)
  │    ├── api/              (REST endpoints & socket routers)
  │    ├── core/
  │    │    ├── truth_engine.py      ← Truth-First validation gate
  │    │    ├── memory.py            (Supabase memory with source tracking)
  │    │    ├── personality.py       (Truth-First system prompt)
  │    │    ├── orchestrator.py      (Cognitive pipeline with Truth Engine)
  │    │    ├── context_builder.py   (Truth-first context assembly)
  │    │    ├── understanding.py     (Regex-only entity extraction)
  │    │    ├── reflection.py        (No LLM fact extraction)
  │    │    ├── brain.py             (LLM provider abstraction)
  │    │    ├── goal_tracker.py      (Goal management)
  │    │    ├── events.py            (Event/reminder system)
  │    │    └── supabase_schema.sql  (DB schema with source/confidence/verified)
  │    ├── skills/           (command actions — no LLM command parsing)
  │    └── templates/        (control dashboard frontend)
  ├── scripts/               (automated APK patching utilities)
  ├── tests/                 (264 tests — core, dialogue, dep graph, multi-agent, orchestrator)
  ├── COMMANDS_REFERENCE.md  (extensive usage command catalog)
  ├── AUDIT.md               (system design audit & structural findings)
  └── ROADMAP.md             (15-phase JARVIS AI OS roadmap)
```

### Core Module Roles

| Module | Responsibility |
|--------|---------------|
| `truth_engine.py` | Gatekeeper: validates confidence, checks memory before LLM, generates "I don't know" responses |
| `memory.py` | Supabase-backed storage with source/confidence/verified on every write |
| `understanding.py` | Keyword + regex analysis only — zero LLM calls |
| `orchestrator.py` | Pipeline: Understand → Truth Engine → Context → Route → Post-Process |
| `brain.py` | LLM provider abstraction (Groq primary, Opencode fallback) |
| `reflection.py` | Session summaries + daily reviews — regex-only fact extraction |

---

## 🧠 AND9 — Modular Reflex Intent Engine

**AND9** (`app/and9/`) is a modular, stateless intent processing engine for Android voice commands. It is organized into three layers:

### Architecture Layers

| Layer | Directory | Responsibility |
|-------|-----------|---------------|
| 🧭 **Router** | `router/` | Normalize query → Detect intent + extract params |
| ⚡ **Actions** | `actions/` | Execute action (call, alarm, app launch, device control) |
| 📱 **Android** | `android/` | Action registry with Android intent mapping + executor |

Support modules handle contacts resolution, package lookup, media routing, alarm/timer/reminder management, and debug logging.

### Processing Pipeline

```
User Query → Normalize (Hindi→English) → Detect Intent (13 categories) → Execute Action → Log → Response
```

### Intent Categories (Priority Order)

| Priority | Intent | Examples |
|----------|--------|---------|
| 1 | EMERGENCY | `emergency`, `help`, `bachao` |
| 2 | CALL | `call mummy`, `dial 98765...` |
| 3 | SEND_SMS | `message mummy mein ghar aa raha hoon` |
| 4 | OPEN_APP | `open whatsapp`, `youtube kholo` |
| 5 | OPEN_CAMERA | `camera kholo`, `selfie lo` |
| 6 | FLASHLIGHT | `torch on karo`, `flashlight off` |
| 7 | YOUTUBE | `youtube search sad songs`, `gaana chalao` |
| 8 | SET_ALARM | `alarm 7 am`, `alarm lagao 7 baje` |
| 9 | SET_REMINDER | `remind me after 10 minutes...` |
| 10 | SET_TIMER | `timer 5 minutes`, `timer lagao` |
| 11 | DEVICE_CONTROL | `volume badhao`, `wifi on`, `home jao` |
| 12 | SEARCH | `search python tutorial`, `who is...` |
| 13 | CHAT | `hello kaise ho` (→ conscious brain / LLM) |

### Key Design Decisions

1. **Priority-Ordered Intent Detection**: 13 categories checked in strict priority order. SEARCH is always last — device commands (call, camera, flashlight, alarm, timer, YouTube) are all detected before generic search.

2. **Single-Pass Hindi Normalization**: Uses regex alternation (longest-match-first) instead of sequential `str.replace()` to prevent double-replacement (e.g., "home jao" → "go home", not "go go home").

3. **Fully Stateless Action Layer**: All action handlers are pure functions — parse params, return intent payloads. No LLM calls, no state mutations, zero side effects.

4. **Chrome Fallback Eliminated**: Only SEARCH intent opens a browser URL. All device commands (alarm, timer, call, camera, flashlight, WiFi, Bluetooth, volume, home, app launch, YouTube) route through the Android Action Registry and Executor — never to Chrome.

5. **Contact Resolution Before Dialing**: `execute_call()` always resolves contact names to phone numbers via `ContactsResolver` before dialing. Never dials string names directly.

6. **YouTube Always Routes to YouTube App**: YouTube commands always target `com.google.android.youtube` package — never Chrome. Music fallback (`gaana chalao`) attempts JARVIS music handler then falls back to YouTube search URL.

7. **Smart Brain Delegation**: Emergency/call/sms intents bypass LLM entirely — only CHAT and SEARCH intents reach the conscious brain. This keeps response times under 5ms for reflex actions vs 1-5s for LLM responses.

---

## 📞 Making Calls — Multi-Turn Phone Call System

The system supports making phone calls through a multi-turn dialogue flow that collects required information before executing.

### Call Intent (`app/and9/dialogue_manager/intent_definitions.py`)

Defined in the dialogue manager with proper slot definitions:

- **Required Slots**: `contact_name` — who to call
- **Optional Slots**: `number` — phone number (if contact name not found in address book)
- **Validation**: `_validate_not_empty` ensures a name/number is provided
- **Action Mapping**: Maps to `execute_call()` in `app/and9/actions/call_actions.py`

### Call Processing Flow

```
User: "Call someone"
  → Dialogue Manager detects "call" intent
  → Asks: "Kise call karna chahte ho?" (Who do you want to call?)

User: "Mummy"
  → Slot filler fills "contact_name" = "Mummy"
  → Action Planner validates all slots filled
  → execute_call(contact_name="Mummy")
    → ContactsResolver.resolve("Mummy")
      → Returns lookup_required=True → Android ContactsContract query
    → Android dials the number
  → Response: "Call kar raha hoon Mummy ko... 📞"
```

### Direct Number Dialing

If the user provides a phone number instead of a name, `ContactsResolver.is_number()` detects it and routes directly:

```
User: "Call 9876543210"
  → Intent: call, params: {contact_name: "9876543210"}
  → ContactsResolver detects it's a number
  → Direct dial via android.intent.action.CALL with tel:9876543210
```

### Contact Resolution Architecture

`app/and9/contacts/resolver.py` uses a privacy-first approach:
- The Python backend does **NOT** store any phone numbers or contact data
- Contact names are validated and passed to Android
- Android resolves via `ContactsContract.CommonDataKinds.Phone` API
- Direct numbers are dialed immediately without contact lookup

### SMS Messaging

The same system supports sending SMS messages:
- Required slots: `contact_name`, `message_text`
- Maps to `execute_message()` → `android.intent.action.SENDTO` with `sms:` URI
- Also supports ContactsContract lookup for named recipients

---

## 🗣️ AND9 Dialogue Manager — Multi-Turn Conversation Engine

The **Dialogue Manager** (`app/and9/dialogue_manager/`) is a production-quality, stateful multi-turn dialogue engine that gives JARVIS human-like conversation memory. It sits on top of the AND9 intent router and adds slot filling, interruption handling, reference resolution, and multi-task management.

### Architecture — 10 Core Modules

| # | Module | Responsibility |
|---|--------|---------------|
| 1 | `intent_definitions.py` | Declares required/optional slots, questions, and success messages per intent |
| 2 | `slot_filler.py` | Fills one slot at a time with typed classifiers (time, contact, app name, content type) |
| 3 | `state_manager.py` | Dialogue State Tracker — task lifecycle (pending -> waiting -> ready -> executing -> completed) |
| 4 | `task_manager.py` | Multi-task orchestration — create, pause, resume, cancel; priority ordering |
| 5 | `working_memory.py` | Three memory layers: WorkingMemory (turn buffer), ShortTermMemory (TTL entities), ActiveTaskMemory |
| 6 | `context_manager.py` | Interruption detection, context summary, conversation history |
| 7 | `reference_resolver.py` | Resolves "it", "that", "this", "them", "continue", "cancel" from context |
| 8 | `action_planner.py` | Validates filled slots, builds execution plans with success/failure messages |
| 9 | `dialogue_manager.py` | Main orchestrator — 11-step pipeline tying all modules together |
| 10 | `routes.py` | FastAPI/Flask endpoints exposing the dialogue engine |

### Processing Pipeline

```
User Message
  |
  +-- 1. Reference Resolution — Resolve "it", "that", "continue", "cancel"
  +-- 2. Cancel Detection — Handle "stop", "cancel", "don't" requests
  +-- 3. Resume Detection — Detect "continue", "resume" for paused tasks
  +-- 4. Intent Detection — AND9 router (with fallback for reconstructed refs)
  +-- 5. Slot Definitions — Load required/optional slots for detected intent
  +-- 6. Active Task Check — Continue existing task or create new one
  +-- 7. Interruption Check — Detect topic switches, pause current task
  +-- 8. Task Management — Create/reuse tasks, track state
  +-- 9. Slot Filling — Fill slots from message + detected params
  +-- 10. Action Planning — Validate slots, build execution plan
  +-- 11. Execute or Ask — Run action or generate next question
  |
  v
Response + State Update
```

### Key Capabilities

**Slot Filling** — Each intent defines required and optional slots. The assistant asks for exactly one missing slot at a time with natural, context-aware questions:

```
User:  Play a song
Agent: Which song would you like to hear?

User:  Tum Hi Ho
Agent: Playing "Tum Hi Ho" on YouTube.
```

**Interruption Handling** — If the user switches topics mid-task, the original task is paused and automatically resumed when they return:

```
User:  Play a song
Agent: Which song?

User:  What's the weather today?
Agent: (Answers weather.)

User:  Now continue
Agent: Continuing youtube! Which song would you like to hear?
```

**Reference Resolution** — Pronouns and deictic references are resolved using ShortTermMemory:

- "Play it" -> resolves *it* to the last mentioned song/video
- "Play that again" -> resolves *that* and reuses slots from the completed task
- "Call them" -> resolves *them* to the last mentioned contact
- "Continue" / "Resume" -> reactivates the most recently paused task

**Multi-Task Management** — Multiple active tasks are tracked independently with their own state, slots, and lifecycle:

```
Task 1: youtube (WAITING_FOR_INFO - waiting for search_query)
Task 2: alarm (PAUSED - was setting alarm for 7 AM)
Task 3: call (COMPLETED - called Mummy)
```

**Cancellation** — "Cancel the music", "Stop", "Don't play music" cleanly cancels the active task and offers the next pending task.

**Never Asks Twice** — If a slot value was already provided, it is never asked for again. The system remembers across interruptions.

### Example Usage

```bash
# Multi-turn dialogue
curl -X POST http://localhost:8000/api/dialogue \
  -H "Content-Type: application/json" \
  -d '{"message":"Play a song"}'
# -> {"response":"Which song?","intent":"youtube","status":"waiting_for_info",...}

curl -X POST http://localhost:8000/api/dialogue \
  -H "Content-Type: application/json" \
  -d '{"message":"Tum Hi Ho"}'
# -> {"response":"Playing Tum Hi Ho on YouTube","intent":"youtube","status":"completed",...}

# Making a call
curl -X POST http://localhost:8000/api/dialogue \
  -H "Content-Type: application/json" \
  -d '{"message":"Call someone"}'
# -> {"response":"Kise call karna chahte ho?","intent":"call","status":"waiting_for_info",...}

curl -X POST http://localhost:8000/api/dialogue \
  -H "Content-Type: application/json" \
  -d '{"message":"Mummy"}'
# -> {"response":"Call kar raha hoon Mummy ko...","intent":"call","status":"completed",...}

# Interruption + resume
curl -X POST http://localhost:8000/api/dialogue \
  -H "Content-Type: application/json" \
  -d '{"message":"Now continue that"}'
# -> {"response":"Chaliye, youtube jaari rakhte hain! ...","status":"waiting_for_info",...}

# Reference resolution
curl -X POST http://localhost:8000/api/dialogue \
  -H "Content-Type: application/json" \
  -d '{"message":"Play that again"}'
# -> {"response":"Playing Tum Hi Ho on YouTube","intent":"youtube","status":"completed",...}

# Cancel a task
curl -X POST http://localhost:8000/api/dialogue \
  -H "Content-Type: application/json" \
  -d '{"message":"Cancel the music"}'
# -> {"response":"OK, music cancel kar diya!","status":"cancelled",...}
```

---

## 🤖 AND9 Multi-Agent System — Phase 3

The **Multi-Agent System** (`app/and9/agents/`) is a coordinated team of 20+ specialized AI agents that work together to handle any user request. Built on the `AgentBase` abstract class with a central `AgentRegistry` for discovery and routing.

### Architecture — 20 Agents in 6 Groups

```
AgentRegistry (service locator)
  ├── Core Agents
  │   ├── Executive      (CEO — orchestrates the swarm)
  │   ├── Conversation   (natural dialogue)
  │   └── Planning       (task decomposition)
  ├── Knowledge Agents
  │   ├── Research       (web research)
  │   ├── Coding         (code generation)
  │   └── Debug          (bug analysis)
  ├── Memory Agents
  │   ├── Memory         (information storage)
  │   ├── Learning       (pattern learning)
  │   └── Reflection     (self-improvement)
  ├── Device Agents
  │   ├── Android        (device control)
  │   ├── Voice          (speech I/O)
  │   └── Browser        (browser automation)
  ├── System Agents
  │   ├── Scheduler      (time-based tasks)
  │   ├── Automation     (rule automation)
  │   ├── Security       (security enforcement)
  │   └── Health         (system monitoring)
  └── Integration Agents
      ├── Tool           (tool registry)
      ├── Integration    (external services)
      ├── Notification   (alerting)
      └── Workflow       (multi-step execution)
```

### Core Components

| Component | File | Responsibility |
|-----------|------|---------------|
| `AgentBase` | `base.py` | Abstract class with memory, metrics, tools, logging, lifecycle |
| `AgentRegistry` | `registry.py` | Service locator — registration, routing, delegation, health |
| `AgentMemory` | `base.py` | Per-agent short-term, working, and persistent memory with TTL |
| `AgentMetrics` | `base.py` | Success/failure tracking, latency, tool usage |
| `AgentResult` | `base.py` | Standard result type with confidence, follow-up support |

### Each Agent Has

| Property | Description |
|----------|-------------|
| `name` | Unique identifier (e.g., `"coding"`, `"research"`) |
| `role` | Short description of purpose |
| `goal` | What the agent aims to achieve |
| `backstory` | Extended persona context |
| `memory` | `AgentMemory` — short-term (TTL), working, persistent |
| `tools` | Dict of callable tools bound to the agent |
| `status` | `AgentStatus` — healthy / degraded / error / disabled |
| `metrics` | `AgentMetrics` — invocations, latency, success rate |
| `confidence` | Confidence in responses (0.0 to 1.0) |
| `logs` | Action history (max 100 entries) |

### Agent Lifecycle

```
Agent Created → initialize() → HEALTHY
  → process(input) → returns AgentResult
  → health_check() → status report
  → shutdown() → DISABLED
```

### Executive Agent — CEO of the Swarm

The `ExecutiveAgent` acts as the orchestrator:

1. Receives user requests
2. Analyzes complexity — simple tasks route directly, complex tasks decompose
3. Delegates subtasks to specialist agents via the registry
4. Supports parallel execution for compound tasks (e.g., "Research and write code")
5. Merges results from multiple agents into coherent responses

### Agent Routing

The registry routes tasks by keyword matching:

```python
registry = create_agent_system()

# Direct routing to specific agents
result = registry.delegate("coding", "Write a Python script")
result = registry.delegate("research", "Latest AI news")

# Automatic routing based on task content
# "debug this error" → DebugAgent
# "plan a project" → PlanningAgent
# "remember my birthday" → MemoryAgent

# Route to all agents (broadcast)
all_results = registry.route_to_all("System check")
```

### Usage Examples

```python
from app.agents import create_agent_system

# Create the full system
registry = create_agent_system()

# Route tasks
result = registry.route("Research quantum computing")
print(result.response)
# → "**Research Plan for: Research quantum computing**..."

# Get a specific agent
coding = registry.get("coding")
result = coding("Write a function to sort files by date")

# Check system health
health = registry.health_report()
print(f"Status: {health['overall_status']}")
print(f"Healthy agents: {health['healthy']}/{health['total_agents']}")

# List all agents
for agent_info in registry.list_agents():
    print(f"{agent_info['name']}: {agent_info['status']}")
```

### Test Coverage

72 tests across 4 test classes:
- `TestAgentBase` (16 tests) — base class, memory, tools, metrics, lifecycle
- `TestAgentRegistry` (17 tests) — registration, routing, delegation, broadcasting
- `TestAgentSystem` (29 tests) — all 20 agents, full system integration
- `TestEdgeCases` (10 tests) — empty input, special chars, error recovery

---

## 🏗️ AND9 Agent Orchestrator — Phase 4

The **Agent Orchestrator** (`app/and9/orchestrator/`) is the central coordination engine for the multi-agent system. It receives user goals, analyzes them, decomposes complex tasks, executes them in parallel, validates results, retries failures, and merges outputs into a coherent final response. This is the "CEO" of the agent system.

### Architecture — 3 Components

| # | Module | Responsibility |
|---|--------|---------------|
| 1 | `task_queue.py` | Priority-ordered thread-safe task queue with dependency tracking |
| 2 | `orchestrator.py` | Full execution pipeline: analyze → decompose → plan → execute → validate → retry → merge |

### Execution Pipeline

```
User Request
  |
  +-- 1. analyze(request) → TaskGraph        — Detect intents, estimate complexity
  +-- 2. decompose(request) → list[SubTask]  — Break into single-domain units
  +-- 3. plan(subtasks) → task_ids           — Enqueue with dependency ordering
  +-- 4. execute(tasks) → dict[Result]       — ThreadPoolExecutor for parallelism
  +-- 5. validate(results) → (passed, failed) — Separate successes from failures
  +-- 6. retry(failed) → dict[Result]        — Re-execute up to max_retries
  +-- 7. merge(results) → AgentResult        — Combine into coherent response
  |
  v
Final Response
```

### Key Capabilities

**Priority-Ordered Queue** — Tasks are ordered by priority (HIGH, MEDIUM, LOW) within a thread-safe queue. Higher-priority tasks always execute first.

**Dependency Tracking** — Tasks can declare dependencies on other tasks. The orchestrator automatically defers execution until dependencies are met, preventing deadlocks.

**Parallel Execution** — Independent tasks execute concurrently via `ThreadPoolExecutor`, maximizing throughput for multi-domain requests.

**Automatic Retry** — Failed tasks are retried up to `max_retries` times with configurable timeout per task.

**Result Validation** — Results are classified as passed or failed. Only failed tasks are retried; successful results are preserved.

**Coherent Merging** — Results from multiple agents are merged into a single, well-structured response with task counts and failure summaries.

### Complexity Detection

The orchestrator automatically determines task complexity:

| Complexity | Criteria | Execution Strategy |
|-----------|----------|-------------------|
| `SIMPLE` | Single domain intent | Fast path — direct agent delegation |
| `MODERATE` | 2-3 domains | Full pipeline with parallel execution |
| `COMPLEX` | 4+ domains | Full pipeline with retry and validation |

### Integration with Executive Agent

The Executive Agent delegates complex tasks to the orchestrator:

```python
from app.agents import create_agent_system

# create_agent_system() automatically creates and links the orchestrator
registry = create_agent_system()

# Simple tasks route directly to specialist agents (fast path)
result = registry.route("Write a Python function")
# → routes directly to CodingAgent

# Complex tasks go through the orchestrator pipeline
result = registry.route("Research machine learning and write implementation")
# → analyze → decompose → execute_parallel → validate → retry → merge
```

### Usage Examples

```python
from app.orchestrator import AgentOrchestrator
from app.agents import create_agent_system

# Create system and orchestrator
registry = create_agent_system()
orchestrator = AgentOrchestrator(registry)

# Run a simple request (fast path)
result = orchestrator.run("Write a hello world function")
print(result.response)

# Run a complex multi-domain request
result = orchestrator.run(
    "Research quantum computing, write a simulator, and document the code"
)
print(f"Success: {result.success}")
print(f"Tasks: {result.data['task_count']}")
print(f"Completed: {result.data['success_count']}/{result.data['task_count']}")

# Check orchestrator status
status = orchestrator.get_status()
print(f"Queue: {status['queue']}")
print(f"History: {status['history_count']} executions")

# View execution history
for entry in orchestrator.get_history(5):
    print(f"{entry['timestamp']}: {entry['request'][:50]}... "
          f"success={entry['success']} ({entry['latency_ms']}ms)")
```

### Test Coverage

41 tests across 4 test classes:
- `TestTaskQueue` (14 tests) — enqueue, dequeue, priority, cancel, dependencies
- `TestAgentOrchestrator` (20 tests) — analyze, decompose, plan, execute, validate, retry, merge, full pipeline
- `TestExecutiveOrchestratorIntegration` (3 tests) — executive→orchestrator wiring
- `TestOrchestratorEdgeCases` (4 tests) — empty registry, deadlock handling, unknown agents

---

## 🔍 Dependency Graph MCP Server — Code Analysis Engine

The **Dependency Graph** (`app/and9/dependency_graph/`) is a pure-Python code analysis engine that parses Python source code using the built-in `ast` module and builds a directed dependency graph. It exposes analysis capabilities via an MCP (Model Context Protocol) server over stdio and REST API endpoints.

### Architecture — 4 Modules

| # | Module | Responsibility |
|---|--------|---------------|
| 1 | `graph.py` | Pure-Python directed graph with PageRank, BFS shortest path, transitive closure, Mermaid/D3 export. Zero dependencies. |
| 2 | `analyzer.py` | AST-based Python file parser. `FileVisitor` extracts imports, functions, classes, calls, inheritance. `DependencyAnalyzer` walks projects with `ThreadPoolExecutor`. |
| 3 | `mcp_server.py` | JSON-RPC 2.0 MCP server over stdio. 10 tools for dependency analysis. Caches analyzed graph. |
| 4 | `routes.py` | FastAPI router + Flask Blueprint-compatible endpoints for HTTP access. |

### Key Features

- **Zero External Dependencies** — Pure Python 3.11+ using only built-in modules (`ast`, `concurrent.futures`, `pathlib`, `collections`)
- **Termux Compatible** — Works on Android Termux with no additional packages
- **Parallel Analysis** — Uses `ThreadPoolExecutor` for fast project-wide parsing
- **Caching** — Analyzed graph is cached; `reanalyze=True` forces refresh

### MCP Server Tools

| Tool | Description |
|------|-------------|
| `get_dependency_graph` | Full project dependency graph as JSON |
| `get_callers` | Which files import/call a given file |
| `get_callees` | What a given file imports/calls |
| `impact_analysis` | Transitive dependents (change impact) |
| `find_orphans` | Files with no dependents |
| `find_leaves` | Files with no dependencies |
| `pagerank` | PageRank centrality scores |
| `export_mermaid` | Mermaid.js flowchart syntax |
| `export_d3` | D3.js force-directed graph JSON |
| `module_info` | Detailed module information |

### REST API Endpoints

All endpoints are available under `GET /api/depgraph/`:

```bash
# Analyze the project
curl http://localhost:8000/api/depgraph/analyze

# Get the full graph
curl http://localhost:8000/api/depgraph/graph

# Find callers of a file
curl -X POST http://localhost:8000/api/depgraph/callers \
  -H "Content-Type: application/json" \
  -d '{"filepath": "app/and9/dialogue_manager/dialogue_manager.py"}'

# Impact analysis (who breaks if this file changes)
curl -X POST http://localhost:8000/api/depgraph/impact \
  -H "Content-Type: application/json" \
  -d '{"filepath": "app/and9/state_manager.py", "max_depth": 5}'

# Find orphan files (no dependents)
curl http://localhost:8000/api/depgraph/orphans

# PageRank scores
curl http://localhost:8000/api/depgraph/pagerank?top_n=10

# Export as Mermaid.js flowchart
curl http://localhost:8000/api/depgraph/mermaid

# Module info
curl -X POST http://localhost:8000/api/depgraph/module \
  -H "Content-Type: application/json" \
  -d '{"filepath": "app/and9/dialogue_manager/intent_definitions.py"}'
```

### Running as MCP Server (CLI)

```bash
# Start the MCP server over stdio
python3 -c "
from app.dependency_graph.mcp_server import DependencyGraphMCPServer
server = DependencyGraphMCPServer('.')
server.run()
"
```

Then send JSON-RPC requests on stdin:
```json
{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"find_orphans","arguments":{}}}
```

---

## 🌐 API Endpoints — Complete Reference

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/and9` | `{"query": "..."}` → Full AND9 processing result |
| `GET` | `/api/and9/stats` | Pattern learning statistics and history |
| `POST` | `/api/and9/apps` | Sync installed apps from Android |
| `POST` | `/api/dialogue` | `{"message": "..."}` → Multi-turn dialogue processing |
| `GET` | `/api/dialogue/state` | Current dialogue state (active/paused tasks, memory) |
| `GET` | `/api/dialogue/tasks` | List active tasks |
| `GET` | `/api/dialogue/tasks/<id>` | Get specific task state |
| `DELETE` | `/api/dialogue/tasks/<id>` | Cancel a specific task |
| `GET` | `/api/dialogue/history` | Recent conversation history |
| `POST` | `/api/dialogue/reset` | Reset all dialogue state |
| `GET` | `/api/depgraph/analyze` | Build/rebuild dependency graph |
| `GET` | `/api/depgraph/graph` | Get full dependency graph |
| `POST` | `/api/depgraph/callers` | Get callers of a file |
| `POST` | `/api/depgraph/callees` | Get callees of a file |
| `POST` | `/api/depgraph/impact` | Impact analysis |
| `GET` | `/api/depgraph/orphans` | Find orphan files |
| `GET` | `/api/depgraph/leaves` | Find leaf files |
| `GET` | `/api/depgraph/pagerank` | PageRank scores |
| `GET` | `/api/depgraph/mermaid` | Export as Mermaid.js |
| `GET` | `/api/depgraph/d3` | Export as D3.js JSON |
| `POST` | `/api/depgraph/module` | Module detail info |
| `POST` | `/api/chat` | Send message to conscious brain |
| `GET` | `/api/history` | Recent chat history |
| `GET` | `/api/memory/facts` | Get stored facts |
| `POST` | `/api/memory/learn` | Learn a new fact |
| `GET` | `/api/memory/recall` | Fast cross-session recall |
| `GET` | `/api/goals` | List goals |
| `POST` | `/api/goals` | Create a new goal |
| `GET` | `/api/events` | List upcoming events |
| `POST` | `/api/events` | Create an event/reminder |
| `GET` | `/api/reflect` | Session or daily reflection |
| `GET` | `/api/proactive/briefing` | Time-aware greeting + suggestions |
| `POST` | `/api/tts` | Text-to-Speech via Edge TTS |
| `GET` | `/api/health` | Health check |

---

## 🧪 Running Tests

```bash
# Run all tests (264 tests: core + dialogue + dep graph + multi-agent + orchestrator)
pytest tests/ -v

# Run dialogue manager tests only (58 tests)
pytest tests/test_dialogue_manager.py -v

# Run dependency graph tests only (25 tests)
pytest tests/test_dependency_graph.py -v

# Run multi-agent system tests only (72 tests)
pytest tests/test_multi_agent_system.py -v

# Run agent orchestrator tests only (41 tests)
pytest tests/test_orchestrator.py -v

# Run multi-agent system sub-groups
pytest tests/test_multi_agent_system.py::TestAgentBase -v
pytest tests/test_multi_agent_system.py::TestAgentRegistry -v
pytest tests/test_multi_agent_system.py::TestAgentSystem -v
pytest tests/test_multi_agent_system.py::TestEdgeCases -v

# Run orchestrator sub-groups
pytest tests/test_orchestrator.py::TestTaskQueue -v          (14 tests)
pytest tests/test_orchestrator.py::TestAgentOrchestrator -v  (20 tests)

# Run specific test categories
pytest tests/test_dialogue_manager.py -k "TestSlotFilling" -v
pytest tests/test_dialogue_manager.py -k "TestInterruptionHandling" -v
pytest tests/test_dialogue_manager.py -k "TestReferenceResolution" -v
pytest tests/test_dialogue_manager.py -k "TestCancellation" -v
pytest tests/test_dialogue_manager.py -k "TestFullConversations" -v
```

---

## 🧭 JARVIS AI OS Roadmap

See [`ROADMAP.md`](ROADMAP.md) for the complete 15-phase vision:

| Phase | Focus | Status |
|-------|-------|--------|
| 0 | Foundation | ✅ **Done** — Modular architecture, event bus, config, logging |
| 1 | Human Brain Architecture | ✅ **Done** — Reflex, Subconscious, Conscious, Reflection brains |
| 2 | Memory System | ✅ **Done** — Working, Short-Term, Long-Term, Episodic memory |
| 3 | Multi-Agent System | ✅ **Done** — 20 agents, registry, routing, delegation |
| 4 | Agent Orchestrator | ✅ **Done** — Priority task queue, parallel execution, retry, merge pipeline |
| 5 | Workflow Engine | 🔜 Planned |
| 6 | Background Task Engine | ✅ **Done** — Timers, reminders, async workers |
| 7 | Long-Term Planning | 🔜 Planned |
| 8 | Learning Engine | 🔜 Planned |
| 9 | Tool System | ✅ **Done** — Dependency Graph MCP, action registry |
| 10 | Android Controller | ✅ **Done** — Full Android intent execution |
| 11 | Voice System | ✅ **Done** — Edge TTS, Hindi/English voice |
| 12 | Automation Engine | 🔜 Planned |
| 13 | Dashboard | 🔜 Planned |
| 14 | Coding Intelligence | ✅ **Done** — Dependency analysis, code parsing |
| 15 | Security & Production | 🔜 Planned |

---

## 📄 License
Licensed under the MIT License. Built with love by **Minaty001**.
