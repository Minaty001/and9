# 🔄 AND9 (JARVIS PCOS) — Complete Reverse Engineering Document

> **Generated:** 2026-06-27
> **Purpose:** Comprehensive reverse-engineering documentation covering rules, architecture, methods, features, functions, workflows, API endpoints, configurations, and known issues of the AND9 Personal Cognitive Operating System.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Reverse-Engineered Architecture](#2-reverse-engineered-architecture)
3. [Brain System — Reverse Catalog](#3-brain-system--reverse-catalog)
4. [Intent Routing System](#4-intent-routing-system)
5. [Action System — Registered Actions](#5-action-system--registered-actions)
6. [Core Cognitive System — Methods & Functions](#6-core-cognitive-system--methods--functions)
7. [API Endpoints — Complete Reverse Catalog](#7-api-endpoints--complete-reverse-catalog)
8. [Data Flow Workflows](#8-data-flow-workflows)
9. [Rules & Constitutions](#9-rules--constitutions)
10. [Configuration & Dependencies](#10-configuration--dependencies)
11. [Known Bugs & Issues](#11-known-bugs--issues)
12. [Micro Neural Brain (Offline System)](#12-micro-neural-brain-offline-system)

---

## 1. Project Overview

### System Identity
- **Name:** JARVIS PCOS (Personal Cognitive Operating System) v4 / AND9
- **Type:** Flask-based AI Assistant Backend + Android Client + Micro Neural Brain
- **Primary Purpose:** On-device Android voice assistant with multi-brain cognitive architecture

### Architecture Type: Three-Brain Architecture + PersonalOS
```
┌──────────────────────────────────────────────────────────────────┐
│                      PERSONAL OS                                 │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                    COGNITIVE ENGINE                         │  │
│  │  ┌──────────┐   ┌──────────┐   ┌────────────────────┐    │  │
│  │  │  REFLEX  │→  │  HABIT   │→  │    REASONING       │    │  │
│  │  │  BRAIN   │   │  BRAIN   │   │     BRAIN          │    │  │
│  │  │ (<300ms) │   │ (~200ms) │   │    (1-5s)          │    │  │
│  │  └──────────┘   └──────────┘   └────────────────────┘    │  │
│  └────────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                   MEMORY SYSTEM                             │  │
│  │  ┌────────┐ → ┌──────────┐ → ┌───────────┐                │  │
│  │  │WORKING │   │ EPISODIC │   │  SEMANTIC │                │  │
│  │  │MEMORY  │   │  MEMORY  │   │  MEMORY   │                │  │
│  │  └────────┘   └──────────┘   └───────────┘                │  │
│  │  ┌──────────────────────┐  ┌──────────────────────┐       │  │
│  │  │  PROCEDURAL MEMORY   │  │   KNOWLEDGE GRAPH    │       │  │
│  │  └──────────────────────┘  └──────────────────────┘       │  │
│  └────────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                  LEARNING SYSTEM                            │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐  │  │
│  │  │    PATTERN   │  │    SKILL     │  │   PREFERENCE   │  │  │
│  │  │   LEARNING   │  │   LEARNING   │  │   LEARNING     │  │  │
│  │  └──────────────┘  └──────────────┘  └────────────────┘  │  │
│  └────────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                  AUTOMATION SYSTEM                          │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐  │  │
│  │  │    GOALS     │  │    HABITS    │  │   SCHEDULED    │  │  │
│  │  │   TRACKING   │  │   TRACKING   │  │   ACTIONS      │  │  │
│  │  └──────────────┘  └──────────────┘  └────────────────┘  │  │
│  └────────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                  ANDROID INTEGRATION                        │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────────┐  │  │
│  │  │ACCESSIBILITY│  │   OVERLAY  │  │   APP CONTROL     │  │  │
│  │  └────────────┘  └────────────┘  └────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                    AGENT LOOP                               │  │
│  │          Observe → Think → Act → Reflect → Learn           │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### Technology Stack
| Layer | Technology | Role |
|-------|-----------|------|
| **Web Framework** | Flask 3.1 | HTTP server, routing, middleware |
| **Production Server** | Gunicorn 23 | WSGI server |
| **Primary LLM** | Groq (via OpenAI-compatible client) | Language understanding |
| **Fallback LLM** | Opencode Zen | Backup when Groq is unavailable |
| **Database** | Supabase (PostgreSQL) | Primary persistent storage |
| **Local Storage** | SQLite | Timers, reminders, activity DB |
| **TTS** | Microsoft Edge TTS | Text-to-speech (Neural voices) |
| **NLP** | spaCy 3.8 + SciPy/NumPy | Deep linguistic analysis |
| **Android** | Kotlin/Java | Client-side execution |
| **Offline NN** | Micro Neural Brain (NumPy) | Lightweight intent classification |
| **Deployment** | Docker, Render.com | Containerization & hosting |

### Directory Structure (Reverse)
```
and9/
├── app/                          # Flask Backend (Python)
│   ├── main.py                   # Application factory, startup, middleware
│   ├── _flask_compat.py          # Flask compatibility shim
│   ├── agents/                   # Agent definitions (coding, research, assistant)
│   ├── and9/                     # AND9 Multi-brain AI OS
│   │   ├── and9.py               # Main AND9 entry point class
│   │   ├── brain_types.py        # BrainType, IntentType enums, BrainResult
│   │   ├── conscious_brain.py    # LLM reasoning wrapper
│   │   ├── subconscious_brain.py # Pattern learning, habit detection
│   │   ├── habit_brain.py        # Routine suggestion engine
│   │   ├── actions/              # Action handler definitions
│   │   ├── alarms/               # Alarm management
│   │   ├── android/              # Android action execution, registry, firewall
│   │   ├── apps/                 # Package resolver (dynamic app lookup)
│   │   ├── brain/                # Orchestrator pipeline, cognitive engine
│   │   ├── contacts/             # Contact resolution
│   │   ├── core/                 # Config, logger, activity DB, intent trace
│   │   ├── intents/              # Intent classification regex files
│   │   ├── media/                # YouTube handler
│   │   ├── reminders/            # Reminder system (DB, scheduler)
│   │   ├── router/               # Intent router, entity extractor, confidence scorer
│   │   ├── timers/               # Timer management
│   │   └── utils/                # Time parsing, timezone utilities
│   ├── api/                      # Flask API blueprints
│   │   ├── routes.py             # Main JSON API (~50 endpoints)
│   │   ├── web_routes.py         # HTML page routes
│   │   ├── admin_routes.py       # Admin panel routes
│   │   └── memory_api.py         # 4-layer memory API
│   ├── core/                     # Core cognitive system
│   │   ├── orchetrator.py       # Central orchestrator pipeline
│   │   ├── memory.py             # Supabase-backed memory (4-layer)
│   │   ├── personality_os.py     # PersonalOS master integration
│   │   ├── brain.py              # LLM interface (Groq + fallback)
│   │   ├── understanding.py      # NLP understanding engine
│   │   ├── truth_engine.py       # Constitution V3 truth validation
│   │   ├── context_builder.py    # LLM context assembly
│   │   ├── personality.py        # JARVIS system prompt
│   │   ├── nlp_pipeline.py       # 4-stage spaCy+SciPy NLP
│   │   ├── nlp_models.py         # NLP data models
│   │   ├── goal_tracker.py       # Goal management
│   │   ├── events.py             # Event system
│   │   ├── proactive.py          # Proactive intelligence engine
│   │   ├── reflection.py         # Daily/session reflection
│   │   ├── timer.py              # Server-side countdown timer
│   │   ├── learning_system.py    # Pattern/skill/preference learning
│   │   ├── procedural_memory.py  # Skill memory
│   │   ├── working_memory.py     # Session memory
│   │   ├── memory_consolidation.py # Working→Episodic→Semantic
│   │   ├── knowledge_graph.py    # Knowledge graph
│   │   ├── agent_loop.py         # Continuous cognitive loop
│   │   ├── automation_system.py  # Goals, habits, scheduled actions
│   │   ├── activity_logger.py    # Activity tracking
│   │   └── supabase_schema.sql   # Database schema DDL
│   ├── reminders/               # Background reminder worker
│   ├── skills/                  # Skills (img, youtube, research, tasks)
│   ├── static/                  # Frontend JS/CSS
│   └── templates/               # HTML templates
├── micro_brain/                 # Offline Micro Neural Brain
├── android/                     # Android client (Gradle project)
├── deploy/                      # Render.com deployment config
├── scripts/                     # Build and utility scripts
├── tests/                       # Pytest test suite
├── Dockerfile                   # Container definition
├── docker-compose.yml           # Multi-service orchestration
└── requirements.txt             # Python dependencies
```

---

## 2. Reverse-Engineered Architecture

### 2.1 Flask App Factory (`app/main.py`)

**Purpose:** Creates and configures the Flask application with all middleware, blueprints, and startup initialization.

**Startup Sequence:**
```
create_app()
  ├── Configure Flask (SECRET_KEY, JSON settings)
  ├── Configure logging
  ├── _init_and9(app)
  │     ├── Phase 12: Validate Action Registry
  │     ├── Validate Android Handler Coverage
  │     ├── Start Reminder Worker (background thread)
  │     ├── Phase 4: Preload PackageResolver (dynamic cache)
  │     ├── Validate Activity Database
  │     └── Phase 0: Ensure data directory
  ├── _init_personality(app)
  │     └── Initialize PersonalOS (cognitive architecture)
  ├── Register middleware
  │     ├── Request ID (X-Request-ID header)
  │     ├── Rate limiter (30 req/min per IP, sliding window)
  │     └── Response headers (X-Runtime-Ms)
  ├── Register blueprints
  │     ├── web_bp (/) — HTML pages
  │     ├── api_bp (/api) — JSON endpoints
  │     ├── admin_bp (/api/admin) — Admin panel
  │     └── memory_bp (/api/memory) — Memory API
  ├── Register /health endpoint
  └── Register error handlers (404, 405, 429, 500)
```

### 2.2 Rate Limiter (`app/main.py`)

- **Class:** `RateLimiter`
- **Algorithm:** Sliding window per IP
- **Default:** 30 requests per 60 seconds
- **Exempt paths:** `/health`, `/api/health`, `/static/*`
- **Response:** 429 with `Retry-After` header

### 2.3 AND9 Entry Point (`app/and9/and9.py`)

- **Class:** `AND9`
- **Constructor:** `AND9(events_sys=None, enable_patterns=True)`
- **Method:** `process(query: str) -> Dict` — delegates to `brain/orchestrator.py`
- **Method:** `get_stats() -> Dict` — returns subconscious, history, logs

### 2.4 PersonalOS (`app/core/personality_os.py`)

- **Class:** `PersonalOS`
- **Purpose:** Master integration point for the entire cognitive architecture
- **Subsystems initialized:** Cognitive Engine, Memory System, Learning System, Automation System, Agent Loop, Android Integration
- **Methods:** `initialize()`, `process(query, source, **context)`, `get_stats()`, `get_daily_reflection()`, `get_all_learnings()`

---

## 3. Brain System — Reverse Catalog

### 3.1 BrainType Enum (`app/and9/brain_types.py`)

| Value | Speed Target | Description |
|-------|-------------|-------------|
| `REFLEX` | < 100ms | Instant execution, zero LLM. App launches, device controls, calls, alarms |
| `SUBCONSCIOUS` | ~200ms | Pattern learning, habit detection, routine suggestions |
| `CONSCIOUS` | 1-5s | Full LLM reasoning, chat, web search, goal management |

### 3.2 IntentType Enum (Priority Order 1-21)

| Priority | Value | Description |
|----------|-------|-------------|
| 1 | `EMERGENCY` | SOS, danger, accident |
| 2 | `CALL` | Phone calls, dial |
| 3 | `MESSAGE` | SMS, WhatsApp message |
| 4 | `OPEN_APP` | Launch Android app |
| 5 | `CAMERA` | Open camera, take photo |
| 6 | `FLASHLIGHT` | Toggle flashlight |
| 7 | `BLUETOOTH` | Bluetooth on/off |
| 8 | `WIFI` | WiFi on/off |
| 9 | `AIRPLANE_MODE` | Flight mode toggle |
| 10 | `VOLUME` | Volume up/down/mute |
| 11 | `YOUTUBE` | YouTube search/play |
| 12 | `MUSIC` | Play music/songs |
| 13 | `SET_ALARM` | Set an alarm |
| 14 | `SET_REMINDER` | Set a reminder |
| 15 | `SET_TIMER` | Set countdown timer |
| 16 | `TIME` | Generic time query |
| 17 | `GOAL` | Goal/project management |
| 18 | `HOME` | Go to home screen |
| 19 | `AUTOMATION` | Automation/routines |
| 20 | `SEARCH` | Web search |
| 21 | `CHAT` | General conversation |

### 3.3 BrainResult Data Class

**Universal result object across all three brains:**

```python
@dataclass
class BrainResult:
    response: str = ""
    action: Optional[str] = None
    payload: Any = None
    brain: BrainType = BrainType.CONSCIOUS
    intent: Optional[IntentType] = None
    parameters: dict = field(default_factory=dict)
    execution_time_ms: float = 0.0
    success: bool = True
    metadata: dict = field(default_factory=dict)
```

**Serialization:** `to_dict()` → `{response, action, payload, brain, intent, parameters, time_ms, success, metadata}`

### 3.4 AND9 Brain Orchestrator (`app/and9/brain/orchestrator.py`)

- **Class:** `Orchestrator`
- **Pipeline:** `normalize → detect_intent → validate → execute → log → return`

**Full Pipeline Steps:**

1. **Normalize** — `QueryNormalizer.normalize()` (Hindi/English normalization)
2. **Detect Intent** — `detect_intent_with_confidence()` → `(intent_name, action_type, params, confidence)`
3. **Validate** — `validate_intent()` checks parameter completeness
4. **Habit Check** — `HabitBrain.get_routine_suggestion()` for greetings
5. **Verify Action** — `verify_action()` checks if confirmation needed
6. **Confidence Tiers:**
   - `< 0.70` → "Samajh nahi aaya" clarification
   - `0.70-0.95` + dangerous → confirmation required
   - `>= 0.95` → execute directly
7. **Execute** — `_execute()` routes to appropriate handler
8. **Background Hooks** — LearningSystem.observe(), MemoryConsolidation
9. **Log** — `_log_result()` → QueryLogger + activity.db
10. **Error Recovery** — `run_diagnostics()` on exceptions

**Execute Method Routing:**
```
_execute(intent_name, action_type, params, start)
  ├── "chat" → ConsciousBrain (LLM)
  ├── "search" → Chrome/web search
  ├── "city_time" → Timezone-aware response
  ├── "emergency" → Emergency response (112)
  ├── device actions → Android Executor (unified entry point)
  └── fallback → Generic response
```

### 3.5 Conscious Brain (`app/and9/conscious_brain.py`)

- **Class:** `ConsciousBrain`
- **Purpose:** Wraps JARVIS Orchestrator for LLM-powered chat, search, goals
- **Key:** Lazy-loads the Orchestrator on first `execute()` call
- **Fallback:** Returns friendly Hinglish error on LLM failure

### 3.6 Subconscious Brain (`app/and9/subconscious_brain.py`)

- **Class:** `SubconsciousBrain`
- **Purpose:** Background pattern learning and habit detection
- **Pattern Types:**
  1. **Time-based frequency** — actions repeated at same time/day (threshold: 3 occurrences)
  2. **Sequential patterns** — action A → action B sequences (threshold: 2 occurrences)
- **Limits:** Max 1000 action history entries (in-memory)
- **Methods:** `record_action()`, `detect_patterns()`, `get_stats()`

### 3.7 Habit Brain (`app/and9/habit_brain.py`)

- **Class:** `HabitBrain`
- **Purpose:** Generates routine suggestions from subconscious patterns
- **Trigger:** On greeting queries ("hello", "hey jarvis")
- **Output:** Suggests predicted next action (e.g., "You usually open WhatsApp at this time")

---

## 4. Intent Routing System

### 4.1 Intent Router (`app/and9/router/intent_router.py`)

**Purpose:** Classifies normalized queries into intents using regex patterns.

**Priority Order (19 levels):**
```
Priority 1:  EMERGENCY
Priority 2:  CALL
Priority 3:  MESSAGE
Priority 4:  OPEN_APP (with sub-routing for camera/youtube)
Priority 5:  CAMERA
Priority 6:  FLASHLIGHT
Priority 7:  BLUETOOTH
Priority 8:  WIFI
Priority 8b: AIRPLANE_MODE
Priority 9:  VOLUME
Priority 9b: GO_HOME
Priority 10: YOUTUBE
Priority 11: MUSIC
Priority 12: ALARM
Priority 13: REMINDER (management → creation)
Priority 14: TIMER
Priority 15: CITY_TIME / TIME
Priority 16: GOAL / AUTOMATION
Priority 17: SEARCH (LAST for device actions)
Priority 18: Micro Neural Brain fallback
Priority 19: CHAT (default)
```

**Key Functions:**

| Function | Returns | Purpose |
|----------|---------|---------|
| `detect_intent(query)` | `(intent_name, action_type, params)` | Primary classification |
| `detect_intent_with_confidence(query)` | `(..., confidence_score)` | Enhanced with confidence scoring |
| `_get_neural_brain()` | NeuralBrain instance | Lazy-loads offline NN fallback |

**Micro Neural Brain Integration:**
- Included after all regex checks fail
- Maps Micro Brain intents (OPEN_APP, PLAY_MUSIC, etc.) to AND9 action types
- Activation threshold: confidence >= 0.75

### 4.2 Entity Extractor (`app/and9/router/entity_extractor.py`)

- **Purpose:** Regex-based extraction of structured entities from queries
- **Entity types extracted:**
  - `app_name` — Android app names
  - `number` / `contact` — Phone numbers, contact names
  - `time` / `duration` — Time expressions (7am, 5 minutes, etc.)
  - `label` — Reminder/alarm labels
  - `city` — Indian city names for timezone queries
  - `query` — Search query text

### 4.3 Confidence Scorer (`app/and9/router/confidence_scorer.py`)

- **Function:** `score_intent(intent, query, params, action)`
- **Scoring factors:** Pattern match strength, parameter completeness, query length
- **Thresholds:**
  - `< 0.70`: Low — ask for clarification
  - `0.70 - 0.95`: Medium — confirm if dangerous
  - `>= 0.95`: High — execute directly

### 4.4 Intent Validator (`app/and9/router/intent_validator.py`)

- **Function:** `validate_intent(intent_name, params, action_type)`
- **Checks:** Required parameters presence, value validity
- **Returns:** `(is_valid, validation_message)`

### 4.5 Query Normalizer (`app/and9/router/normalizer.py`)

- **Class:** `QueryNormalizer`
- **Purpose:** Normalizes Hinglish/Hindi queries to standard form
- **Operations:** Lowercasing, common word replacements, whitespace normalization

### 4.6 Action Verifier (`app/and9/actions/action_verifier.py`)

- **Function:** `verify_action(action_type, params)`
- **Purpose:** Determines if action needs user confirmation
- **Triggers:** Dangerous actions (call, message, emergency), missing params

### 4.7 Command Dictionary (`app/and9/router/command_dictionary.py`)

**Regex pattern definitions for all intent types:**
- `EMERGENCY` — danger, sos, accident patterns
- `CALL_CONTACT` / `CALL_NUMBER` — calling patterns
- `OPEN_APP_TRIGGERS` — kholo, open, launch patterns
- `FLASHLIGHT_ON/OFF` — torch/flashlight patterns
- `VOLUME_UP/DOWN/MUTE/MAX` — volume control patterns
- `YOUTUBE_TRIGGER` / `YOUTUBE_PLAY_TRIGGER` — YouTube patterns
- `ALARM_TRIGGER` — alarm setting patterns
- `REMINDER_TRIGGER` — reminder patterns (including management commands)
- `TIMER_TRIGGER` — timer patterns
- `TIME_TRIGGER` — time query patterns
- `SEARCH_TRIGGER` — web search patterns
- `GO_HOME` — home screen patterns
- `AIRPLANE_MODE` — flight mode patterns

---

## 5. Action System — Registered Actions

### 5.1 ActionType Enum (`app/and9/core/constants.py`)

All 30+ device action constants:

**App Management:**
| Action | Value | Description |
|--------|-------|-------------|
| `LAUNCH_APP` | `open_app` | Open Android app by package name |
| `CLOSE_APP` | `close_app` | Close/go back from app |

**Communication:**
| Action | Value | Description |
|--------|-------|-------------|
| `CALL` | `call` | Initiate phone call |
| `SEND_SMS` | `send_sms` | Send SMS message |

**Device Control:**
| Action | Value | Description |
|--------|-------|-------------|
| `FLASHLIGHT` | `flashlight` | Toggle flashlight |
| `FLASHLIGHT_ON` | `flashlight_on` | Flashlight on |
| `FLASHLIGHT_OFF` | `flashlight_off` | Flashlight off |
| `VOLUME_UP` | `volume_up` | Increase volume |
| `VOLUME_DOWN` | `volume_down` | Decrease volume |
| `VOLUME_MUTE` | `volume_mute` | Mute volume |
| `VOLUME_MAX` | `volume_max` | Max volume |
| `WIFI` | `wifi` | Toggle WiFi |
| `BLUETOOTH` | `bluetooth` | Toggle Bluetooth |
| `AIRPLANE_MODE` | `airplane_mode` | Toggle airplane mode |
| `GO_HOME` | `go_home` | Go to home screen |
| `OPEN_CAMERA` | `open_camera` | Open camera |

**Media:**
| Action | Value | Description |
|--------|-------|-------------|
| `YOUTUBE_SEARCH` | `youtube_search` | Search YouTube |
| `YOUTUBE_PLAY` | `youtube_play` | Play video/song |
| `MUSIC_PLAY` | `music_play` | Play music |

**Time:**
| Action | Value | Description |
|--------|-------|-------------|
| `SET_ALARM` | `set_alarm` | Set alarm |
| `SET_TIMER` | `set_timer` | Set countdown timer |
| `SET_REMINDER` | `set_reminder` | Set reminder |
| `GET_TIME` | `get_time` | Tell current time |
| `CITY_TIME` | `city_time` | Time in specific city |

**Reminder Management (Phase G):**
| Action | Value |
|--------|-------|
| `LIST_REMINDERS` | `list_reminders` |
| `DELETE_REMINDER` | `delete_reminder` |
| `PAUSE_REMINDER` | `pause_reminder` |
| `RESUME_REMINDER` | `resume_reminder` |
| `SNOOZE_REMINDER` | `snooze_reminder` |
| `CLEAR_ALL_REMINDERS` | `clear_all_reminders` |
| `SHOW_COMPLETED_REMINDERS` | `show_completed_reminders` |
| `EDIT_REMINDER` | `edit_reminder` |

**Other:**
| Action | Value |
|--------|-------|
| `EMERGENCY` | `emergency` |
| `SEARCH` | `search` |
| `CHAT` | `chat` |
| `UNKNOWN_APP` | `unknown_app` |
| `ERROR` | `error` |

### 5.2 Action Registry (`app/and9/android/action_registry.py`)

**Required Actions (validated at startup):**
```python
_REQUIRED_ACTIONS = frozenset({
    "open_app", "close_app", "call", "send_sms", "open_camera",
    "set_alarm", "set_timer", "set_reminder",
    "list_reminders", "delete_reminder", "pause_reminder",
    "resume_reminder", "snooze_reminder", "clear_all_reminders",
    "show_completed_reminders", "edit_reminder",
    "youtube_search", "youtube_play",
    "flashlight", "flashlight_on", "flashlight_off",
    "go_home", "volume_up", "volume_down", "volume_mute", "volume_max",
    "wifi", "bluetooth", "airplane_mode", "emergency",
    "get_time", "search",
    "clipboard_read", "clipboard_write",
    "media_play_pause", "media_next", "media_prev",
    "screen_state", "read_notifications",
})
```

**Registry Entry Format:**
```python
REGISTRY = {
    "open_app": {
        "handler": "actions.app_actions.execute_open_app",
        "android_intent": "android.intent.action.MAIN",
        "description": "Open an Android app...",
        "params": ["app_name"],
        "whitelisted": True,
    },
    # ... 30+ entries
}
```

### 5.3 Android Executor (`app/and9/android/android_executor.py`)

- **Function:** `execute(action_type, params, events_sys)`
- **Purpose:** **Single entry point** for all Android actions
- **Pipeline:** lookup registry → validate params → Chrome Firewall check → call handler
- **Chrome Firewall:** Blocks any non-search action from opening Chrome

### 5.4 Chrome Firewall (`app/and9/android/chrome_firewall.py`)

- **Rule:** Only SEARCH/NEWS/WEB_LOOKUP may open Chrome
- **Enforcement:** Checked after every action execution, before response return
- **Blocked actions:** CALL, ALARM, TIMER, YOUTUBE, OPEN_APP (when targeting Chrome)

### 5.5 Action Handlers (`app/and9/actions/`)

| Module | Handlers |
|--------|----------|
| `app_actions.py` | `execute_open_app()`, `execute_close_app()` |
| `call_actions.py` | `execute_call()`, `execute_dial()` |
| `device_actions.py` | Flashlight, WiFi, Bluetooth, Volume, Airplane, Home |
| `alarm_actions.py` | `execute_set_alarm()` |
| `timer_actions.py` | `execute_set_timer()` |
| `reminder_actions.py` | Set, list, delete, pause, resume, snooze, clear reminders |
| `time_actions.py` | Get current time, city time |
| `youtube_actions.py` | YouTube search, play |

---

## 6. Core Cognitive System — Methods & Functions

### 6.1 Memory System (`app/core/memory.py`)

**Class:** `Memory`
**Backend:** Supabase (PostgreSQL) — primary; 4-layer cognitive memory

| Layer | Type | Purpose | Persistence |
|-------|------|---------|-------------|
| **Working Memory** | `working_memory.py` | Current session context | In-memory |
| **Episodic Memory** | Supabase `episodes` table | Past conversations and events | DB |
| **Semantic Memory** | Supabase `facts`, `user_facts` | Verified knowledge, user profile | DB |
| **Procedural Memory** | `procedural_memory.py` | Learned skills and procedures | DB |

**Key Methods:**

| Method | Purpose |
|--------|---------|
| `add_episode()` | Save a conversation turn to episodic memory |
| `store_fact()` | Store verified fact with source/confidence/verified |
| `learn_fact()` | Legacy fact storage with backward compatibility |
| `delete_fact()` | Remove a fact by key |
| `search_facts()` | Search facts by keyword |
| `get_facts()` | Retrieve all stored facts |
| `get_user_profile()` | Aggregate user profile from semantic memory |
| `get_recent_chat(n)` | Get N most recent chat turns |
| `get_recent_episodes(n)` | Get N most recent episodes |
| `fast_recall(query)` | Cross-session memory recall with LRU cache |
| `build_memory_context()` | Assemble context for LLM prompt |
| `get_or_create_session()` | Manage conversation sessions |
| `get_session_history()` | Get episodes for a session |
| `record_emotion()` | Tag emotional context to episodes |
| `get_emotional_context()` | Get emotional state summary |

### 6.2 Understanding Engine (`app/core/understanding.py`)

**Class:** `UnderstandingEngine`
**Method:** `analyze(query, user_profile) → MessageAnalysis`

**`MessageAnalysis` Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `intent` | str | Detected intent category |
| `emotion` | str | Detected emotion (neutral, happy, sad, angry, etc.) |
| `emotion_intensity` | int | 1-5 scale |
| `entities` | dict | Extracted entities |
| `is_memory_store` | bool | User wants to store info |
| `is_memory_recall` | bool | User wants to recall info |
| `topic` | str | Conversation topic |
| `expertise_level` | str | beginner/intermediate/expert |
| `nlp_result` | NLPResult | spaCy pipeline result (optional) |
| `nlp_confidence` | float | NLP confidence score |

**Intent Patterns (order matters):**
- `memory_store` — yaad rakh, remember, note kar, save kar, likh le
- `memory_recall` — kya hai, yaad hai, batao, what is my, who am i
- `personal_info` — mera naam, meri, my name, my age, my profession
- `preference` — mujhe pasand, favorite, I like, prefer
- `time_query` — time kya hai, what time, kitne baje
- `weather_query` — mausam, weather, temperature, kitna garmi
- `location_query` — kahan hai, location, where is
- `calculation` — add, subtract, multiply, calculate
- Also: `greeting`, `farewell`, `casual`, `question`, `command`, `opinion`, `confirmation`

**NLP Pipeline (`app/core/nlp_pipeline.py`):**
- **Stage 1:** Tokenization + POS tagging (spaCy)
- **Stage 2:** Dependency parsing, noun chunks
- **Stage 3:** TF-IDF intent scoring (SciPy cosine similarity)
- **Stage 4:** Sentiment analysis, complexity metrics
- **Override:** NLP intent overrides regex when confidence >= 0.35

### 6.3 Truth Engine (`app/core/truth_engine.py`)

**Confidence Map (Constitution V3 Rule 5):**

| Source | Max Confidence |
|--------|---------------|
| `user_input`, `direct_statement`, `user_stated` | 1.0 |
| `observed`, `observed_pattern`, `cross_session` | 0.7 |
| `regex_extraction`, `keyword_detection` | 0.3 |
| `llm_inference`, `llm_extraction`, `ai_inferred` | 0.0 ❌ Never stored |

**Key Functions:**

| Function | Purpose |
|----------|---------|
| `validate_memory(value, source, confidence, verified)` | Gate check for memory items |
| `verify_before_llm(memory_ctx, query)` | Check if verified memory exists before LLM call |
| `cap_confidence(source)` | Apply max confidence cap by source type |

**Rejection Rules:**
1. LLM-inferred facts (confidence 0.0) — always rejected
2. Unverified regex extractions (confidence < 0.5) — rejected unless verified
3. Empty/null values — rejected

### 6.4 Context Builder (`app/core/context_builder.py`)

**Class:** `ContextBuilder`
**Method:** `build(user_profile, emotional_context, recent_episodes, relevant_past, current_analysis, extra_context)`
**Purpose:** Assembles rich LLM prompt context from all memory layers
**Components:** Profile + emotions + recent chat + relevant episodes + extra context

### 6.5 Personality System (`app/core/personality.py`)

**Purpose:** JARVIS character system prompt
**Style:** Hinglish, respectful, helpful, action-oriented
**Rules embedded:** Constitution V3 rules, memory constraints, response format

### 6.6 Goal Tracker (`app/core/goal_tracker.py`)

**Class:** `GoalTracker`
**Key Methods:**

| Method | Purpose |
|--------|---------|
| `add_goal(title, description, priority, deadline)` | Create new goal |
| `get_active_goals()` | List active goals |
| `get_all_goals()` | List all goals |
| `complete_goal(goal_id)` | Mark goal as done |
| `update_goal_status(goal_id, status)` | Update goal state |
| `delete_goal(goal_id)` | Remove goal |
| `build_goal_context()` | Generate goal summary for LLM |

### 6.7 Event System (`app/core/events.py`)

**Class:** `EventSystem`
**Key Methods:**

| Method | Purpose |
|--------|---------|
| `add_event(title, event_time, notes, repeat)` | Create event |
| `get_upcoming_events(hours_ahead)` | List upcoming events |
| `get_due_events()` | Get events due now |
| `mark_done(event_id)` | Complete event |
| `parse_event_from_text(text)` | Extract event from natural language |
| `build_event_context()` | Generate event summary for LLM |

### 6.8 Reflection Engine (`app/core/reflection.py`)

**Class:** `ReflectionEngine`
**Key Methods:**

| Method | Purpose |
|--------|---------|
| `daily_review(ask_llm)` | Generate daily activity summary |
| `reflect_on_session(session_id, ask_llm)` | Reflect on specific session |

### 6.9 Proactive Engine (`app/core/proactive.py`)

**Class:** `ProactiveEngine`
**Key Methods:**

| Method | Purpose |
|--------|---------|
| `get_daily_briefing()` | Time-aware greeting, date, tip |
| `get_proactive_suggestion(emotion, topic)` | Contextual suggestion |
| `analyze_productivity_streak(episodes)` | Streak tracking |
| `get_android_quick_actions(profile)` | Dynamic quick action chips |

### 6.10 Learning System (`app/core/learning_system.py`)

**Class:** `LearningSystem`
**Subsystems:**
- **Pattern Learning** — detects user behavior patterns over time
- **Skill Learning** — tracks skill usage and improvement
- **Preference Learning** — learns user preferences

### 6.11 Agent Loop (`app/core/agent_loop.py`)

**Class:** AgentLoop
**Cycle:** Observe → Think → Act → Reflect → Learn → Improve

### 6.12 Memory Consolidation (`app/core/memory_consolidation.py`)

**Pipeline:** Working Memory → Episodic Memory → Semantic Memory
**Method:** `add_to_working(content, importance, topics, entities, source)`

### 6.13 LLM Interface (`app/core/brain.py`)

**Function:** `ask_llm(messages, context)`
**Fallback Chain:** Groq (primary) → Opencode Zen (fallback)
**Provider:** OpenAI-compatible API client

### 6.14 Timer Service (`app/core/timer.py`)

**Class:** TimerService (singleton via `get_timer_service()`)
**Backend:** SQLite persistence
**Key Methods:** `create_timer()`, `get_alerts()`, `get()`, `cancel()`, `pause()`, `resume()`, `get_all_active()`

### 6.15 Activity Logger (`app/core/activity_logger.py`)

**Purpose:** Daily activity logging and tracking

### 6.16 PersonalOS Central Processing

**`PersonalOS.process(query, source, **context)`** → Integrates all subsystems:
1. Route through Cognitive Engine
2. Log to Memory System
3. Trigger Learning System
4. Check Automation System
5. Run Agent Loop

### 6.17 Central Orchestrator (`app/core/orchestrator.py`)

**Class:** `Orchestrator` (different from AND9 brain/orchestrator)
**Pipeline:** Analyze → Truth Engine → Memory → Context → Route → Execute → Post-process

**Intent Router Patterns (10 categories):**
| Category | Keywords |
|----------|----------|
| `search` | find, look up, google, news, weather, who is, what is |
| `research` | in-depth, comprehensive, deep dive, history of |
| `coding` | code, python, javascript, bug, fix, debug, refactor |
| `image` | generate image, create image, draw, make a picture |
| `music` | song, gaana, music, play, bajao, laga do, sunao |
| `goal` | goal, target, aim, lakshya, project, todo, task |
| `reminder` | remind, yaad dilana, event, meeting, schedule |
| `reflection` | daily review, aaj kya kiya, session summary, reflect |
| `device` | turn on/off, wifi, bluetooth, torch, volume, alarm, call, open, kholo |
| `chat` | (default fallback) |

---

## 7. API Endpoints — Complete Reverse Catalog

### 7.1 Health & Status

| Endpoint | Method | Input | Output |
|----------|--------|-------|--------|
| `/health` | GET | None | `{"status": "ok", "request_id": "..."}` |
| `/api/health` | GET | None | `{"status": "ok"}` |

### 7.2 Chat & Agents

| Endpoint | Method | Input | Output |
|----------|--------|-------|--------|
| `/api/chat` | POST | `{"message": "..."}` | `{reply, agent, time_ms, image_url, youtube_url, sources, status, brain, metadata, intent}` |
| `/api/agents` | GET | None | `[{name, description}, ...]` — 10 agents |

### 7.3 History

| Endpoint | Method | Input | Output |
|----------|--------|-------|--------|
| `/api/history` | GET | None | `[{role, content, timestamp}, ...]` — last 20 turns |

### 7.4 Memory (Semantic Facts)

| Endpoint | Method | Input | Output |
|----------|--------|-------|--------|
| `/api/memory/facts` | GET | None | `[{key, value, category, confidence, ...}]` |
| `/api/memory/learn` | POST | `{"key": "...", "value": "..."}` | `{"status": "learned", "key": "..."}` |
| `/api/memory/fact` | DELETE | `{"key": "..."}` | `{"status": "deleted", "key": "..."}` |
| `/api/memory/search` | GET | `?q=keyword` | `{matching facts}` |
| `/api/memory/recall` | GET | `?q=...&limit=8` | `{matched_episodes, user_profile, recent_chat, sessions_summary}` |
| `/api/memory/cache/stats` | GET | None | `{hits, misses, size}` ⚠️ KNOWN BUG |
| `/api/memory/episodes/search` | GET | `?q=...&limit=10` | `{keyword, results, count}` ⚠️ KNOWN BUG |
| `/api/memory/sessions` | GET | `?limit=5` | `{sessions, count}` ⚠️ KNOWN BUG |

### 7.5 Brain

| Endpoint | Method | Output |
|----------|--------|--------|
| `/api/brain/profile` | GET | User profile from semantic memory |
| `/api/brain/emotions` | GET | Emotional context |
| `/api/brain/sessions` | GET | Session info + recent episodes |

### 7.6 Understanding

| Endpoint | Method | Input | Output |
|----------|--------|-------|--------|
| `/api/understanding/analyze` | POST | `{"query": "..."}` | `{intent, emotion, emotion_intensity, entities, topic, expertise_level, nlp_details}` |

### 7.7 Goals

| Endpoint | Method | Input | Output |
|----------|--------|-------|--------|
| `/api/goals` | GET | `?status=active` | `{goals, count}` |
| `/api/goals` | POST | `{"title", "description?", "priority?", "deadline?"}` | `{status: "created", goal}` |
| `/api/goals/<id>` | PATCH | `{"status": "done"/"active"/"paused"}` | `{status: "updated"}` |
| `/api/goals/<id>` | DELETE | None | `{status: "deleted"}` |

### 7.8 Events/Reminders

| Endpoint | Method | Input | Output |
|----------|--------|-------|--------|
| `/api/events` | GET | `?hours=48` | `{events, due, count}` |
| `/api/events` | POST | `{"title", "event_time?", "notes?", "repeat?"}` | `{status: "created", event}` |
| `/api/events/<id>/done` | PATCH | None | `{status: "done"}` |
| `/api/reminder/alerts` | GET | None | `{alerts}` — claim-based queue |

### 7.9 Reflection

| Endpoint | Method | Input | Output |
|----------|--------|-------|--------|
| `/api/reflect` | GET | `?type=daily\|session` | `{type, review}` or `{type, session_id, summary}` |

### 7.10 Proactive Intelligence

| Endpoint | Method | Input | Output |
|----------|--------|-------|--------|
| `/api/proactive/briefing` | GET | None | `{time, date, greeting, tip, suggestion, streak, quick_actions}` |
| `/api/proactive/suggestion` | GET | `?emotion=...&topic=...` | `{suggestion}` |

### 7.11 TTS (Text-to-Speech)

| Endpoint | Method | Input | Output |
|----------|--------|-------|--------|
| `/api/tts` | POST | `{"text", "voice?", "rate?", "pitch?"}` | `audio/mpeg` stream |
| `/api/tts/voices` | GET | None | `{voices, default_hinglish, default_hindi}` |

**Voice Auto-detection:** Devanagari script → `hi-IN-SwaraNeural` (Hindi), else `en-IN-NeerjaNeural` (Indian English)

### 7.12 Timer

| Endpoint | Method | Input | Output |
|----------|--------|-------|--------|
| `/api/timer` | POST | `{"duration"(secs), "label?"}` | `{id, remaining, end_time, label}` |
| `/api/timers` | GET | None | `{timers, count}` |
| `/api/timer/<id>` | GET | None | `{id, remaining, status, ...}` |
| `/api/timer/<id>` | DELETE | None | `{cancelled: true}` |
| `/api/timer/<id>/pause` | POST | None | `{remaining, status: paused}` |
| `/api/timer/<id>/resume` | POST | None | `{remaining, status: active}` |
| `/api/timer/alerts` | GET | None | `{alerts}` — polling endpoint |

### 7.13 AND9 Multi-brain

| Endpoint | Method | Input | Output |
|----------|--------|-------|--------|
| `/api/and9` | POST | `{"query": "..."}` | `{response, action, payload, brain, intent, time_ms, success}` |
| `/api/and9/apps` | POST | `{pkg: label, ...}` | `{status: "synced", count}` |
| `/api/and9/stats` | GET | None | `{subconscious, history, logs}` |

### 7.14 PersonalOS

| Endpoint | Method | Input | Output |
|----------|--------|-------|--------|
| `/api/personality/process` | POST | `{"query", "source?", ...}` | `{response, brain, time_ms, success, learning, metadata}` |
| `/api/personality/stats` | GET | None | Full system statistics |
| `/api/personality/reflection` | GET | None | Daily reflection summary |
| `/api/personality/learnings` | GET | None | Patterns, skills, preferences |
| `/api/personality/health` | GET | None | `{status, initialized, subsystems}` — 9 subsystem booleans |

### 7.15 4-Layer Memory API (`/api/memory`)

| Endpoint | Method | Output |
|----------|--------|--------|
| `/api/memory/working` | GET | Working memory state |
| `/api/memory/episodic` | GET | Recent episodic memories |
| `/api/memory/semantic` | GET | User profile and facts |
| `/api/memory/procedural` | GET | Learned skills |
| `/api/memory/consolidate` | POST | Trigger consolidation |

### 7.16 Web Routes

| Endpoint | Method | Output |
|----------|--------|--------|
| `/` | GET | `index.html` (main UI) |
| `/admin` | GET | `admin.html` (admin panel) |

### 7.17 Admin Routes (`/api/admin`)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/admin/auth` | POST | Admin authentication (⚠️ KNOWN BUG) |
| `/api/admin/files` | GET | File browser |
| `/api/admin/data` | GET | Database viewer |
| `/api/admin/logs` | GET | Activity logs viewer |

---

## 8. Data Flow Workflows (Reverse)

### 8.1 User Query → Response Pipeline (AND9 Flow)

```
User Input
  │
  ▼
[1. Query Normalizer]
  │  Normalize Hindi/English → lowercase, cleanup
  ▼
[2. Intent Router]
  │  Priority check: Emergency(1) → Call(2) → ... → Chat(21)
  │  Optional: Micro Neural Brain fallback
  ▼
[3. Entity Extractor]
  │  Extract parameters: app_name, number, time, duration, label, city
  ▼
[4. Intent Validator]
  │  Check required parameters
  ▼
[5. Confidence Scorer]
  │  Score: <0.70 → clarification | 0.70-0.95+dangerous → confirm | ≥0.95 → execute
  ▼
[6. Habit Check]
  │  Greeting? → Suggest routine from Subconscious patterns
  ▼
[7. Action Verifier]
  │  Dangerous action? → Request confirmation
  ▼
[8. Execute]
  ├── Chat → ConsciousBrain (LLM via Groq/Opencode)
  ├── Search → Chrome/Web
  ├── Device → Android Executor (unified entry)
  └── Emergency → Emergency response
  ▼
[9. Background Hooks]
  │  Subconscious.record_action()
  │  LearningSystem.observe()
  │  MemoryConsolidation.add_to_working()
  ▼
[10. Log]
  │  QueryLogger.log()
  │  Activity DB log_activity()
  ▼
[11. Return]
     BrainResult.to_dict() → API Response
```

### 8.2 User Query → Response Pipeline (Core Orchestrator Flow)

```
User Input
  │
  ▼
[1. Understanding Engine]
  │  Intent detection, emotion analysis, entity extraction
  │  NLP pipeline (spaCy+SciPy) optional enrichment
  ▼
[2. Memory Check]
  │  is_memory_store? → Store entities via Truth Engine → return
  │  is_memory_recall? → Recall via Truth Engine → return
  ▼
[3. Parallel Context Fetch]
  │  Memory context + Goals context + Events context
  │  (ThreadPoolExecutor, max 3 workers)
  ▼
[4. Truth Engine]
  │  Personal query? → verify_before_llm()
  │  No memory? → "Mujhe nahi pata"
  ▼
[5. Context Builder]
  │  Assemble: Profile + Emotions + Episodes + Context
  ▼
[6. Intent Router]
  │  Route to: music / goal / reminder / reflection / agent / chat
  ▼
[7. Execute Agent]
  │  CodingAgent / ResearchAgent / AssistantAgent / Agent
  │  Or: Music handler / Goal handler / Reminder handler / Reflection handler
  ▼
[8. Post-Process (background)]
  │  Save episodes to Episodic Memory
  │  Tag emotions (if not neutral)
  │  NO auto-entity storage (Constitution V3 Rule 5/6)
  ▼
[9. Return]
     JSON Response: {response, agent, success, metadata, brain, time_ms}
```

### 8.3 Android Action Execution Flow

```
Action Type + Parameters
  │
  ▼
[Action Registry Lookup]
  │  get_action(action_type)
  │  → handler path, description, required params
  ▼
[Handler Import & Call]
  │  _call_handler(handler_path, action_type, params, events_sys)
  ▼
[Chrome Firewall Check]
  │  Is the payload opening Chrome?
  │  Is the action type SEARCH/NEWS/WEB_LOOKUP?
  │  No → BLOCK (return CHROME_FIREWALL_BLOCKED)
  ▼
[Return]
  {response, action, payload, metadata}
```

### 8.4 Startup Initialization Sequence

```
create_app()
  │
  ├── Phase 12: Validate Action Registry
  │   → Assert all _REQUIRED_ACTIONS have handlers
  │   → FATAL on failure
  │
  ├── Phase 8: Validate Android Handler Coverage
  │   → Check every handler module is importable
  │   → Non-fatal in dev, fatal in production (AND9_STRICT_VALIDATION=1)
  │
  ├── Phase 4: Start Reminder Worker
  │   → Background thread polling for due reminders
  │
  ├── Phase 4: Preload PackageResolver
  │   → Dynamic installed_apps.json cache
  │
  ├── Self Diagnostics: Validate Activity Database
  │   → activities.db schema check
  │
  ├── Phase 0: Ensure Data Directory
  │   → Legacy notes directory
  │
  └── Phase 16: Initialize PersonalOS
      → Cognitive Engine, Memory, Learning, Automation, Agent Loop
```

### 8.5 LLM Fallback Chain

```
ask_llm(messages, context)
  │
  ├── Groq API (OPENAI_API_BASE = Groq endpoint)
  │   → Success? → Return response
  │
  └── Opencode Zen API (fallback)
      → Success? → Return response
      → Failure? → Return None → "AI service not configured"
```

### 8.6 Memory Storage Flow (Rule 5/6 Compliant)

```
User says "My name is Saif"
  │
  ├── Understanding Engine extracts: entities = {name: "Saif"}
  │
  ├── Truth Engine: source=regex_extraction → max_confidence=0.3
  │
  ├── _store_entities()
  │   ├── store_fact(category="identity", key="name", value="Saif",
  │   │               confidence=0.3, source="regex_extraction", verified=False)
  │   └── learn_fact(key="name", value="Saif", ...)
  │
  └── add_episode(role="user", content="My name is Saif", source="user_input")
      → No LLM inference involved → Rule 6 compliant
```

---

## 9. Rules & Constitutions

### 9.1 AGENTS.md — AND9 Workspace Rules & Constitution

**Primary Rule — Action First Policy:**
```
DO NOT explain. DO NOT teach.
DO NOT provide instructions. DO NOT answer like ChatGPT.
Instead:
1. Determine intent
2. Execute action
3. Verify result
4. Save activity
5. Return concise confirmation
```

**Execution Order:**
```
Intent → Entity Extraction → Validation → Action Registry → Android Executor → Result Verification → Memory Save → Confirmation
```

**Memory Requirement:**
- Every action must create an activity record
- Columns: id, timestamp, query, intent, action, result, details
- No action may execute without logging

**Action Verification:**
- After action execution: Verify success
- OPEN_APP → Verify app package moved foreground
- CALL → Verify dial intent launched
- ALARM → Verify alarm created
- REMINDER → Verify reminder inserted
- TIMER → Verify timer running
- If verification fails: Retry once, then return failure reason

**Forbidden Responses:**
"To open YouTube...", "You can open YouTube by...", "Here are the steps...", "I cannot directly..."

**Self Diagnostics (Every Startup):**
validate registry → validate handlers → validate database → validate permissions → validate accessibility service → validate notification service

### 9.2 Constitution V3 — Truth-First Architecture

| Rule | Principle | Implementation |
|------|-----------|---------------|
| **Rule 1** | Never hallucinate — if info not in context, say "Mujhe nahi pata" | Truth Engine pre-LLM gate, personality prompt |
| **Rule 4** | Never claim memory you don't have | `verify_before_llm()` checks memory before any recall |
| **Rule 5** | Confidence map enforced on all writes | `cap_confidence()` caps by source type |
| **Rule 6** | No LLM inference stored as fact | Entity storage only from regex, never from LLM |
| **Rule 7** | Whitelist-based action execution | Android ACTION_WHITELIST + parameter validation |
| **Rule 8** | Source tracking for all memory writes | source/confidence/verified on every record |

### 9.3 Chrome Firewall Rules (Phase 14/17)

1. Only SEARCH/NEWS/WEB_LOOKUP may open Chrome
2. All device actions (CALL, ALARM, TIMER, YOUTUBE, etc.) are blocked from opening Chrome
3. Chrome is NEVER used as fallback for device commands
4. Checked AFTER execution, before returning

### 9.4 AND9 Design Rules

1. Device actions ALWAYS beat search actions
2. SEARCH is the LAST intent checked (priority 17/20)
3. Chrome is NEVER opened except for SEARCH/NEWS/WEB_LOOKUP
4. All actions pass through Android Executor (single entry point)
5. Every request traced through intent_trace
6. All actions registered in Action Registry
7. Registry validated at every startup

### 9.5 PersonalOS Subsystems (Health Check)

9 subsystems tracked:
- `procedural_memory` — learned skills
- `memory_consolidation` — W→E→S pipeline
- `learning_system` — pattern/skill/preference learning
- `memory_system` — 4-layer cognitive memory
- `knowledge_graph` — entity relationships
- `reflection_engine` — daily/session reviews
- `automation_system` — goals, habits, scheduled actions
- `cognitive_engine` — Reflex + Habit + Reasoning brains
- `agent_loop` — Observe→Think→Act→Reflect→Learn

---

## 10. Configuration & Dependencies

### 10.1 Environment Variables

| Variable | Purpose | Required |
|----------|---------|----------|
| `GROQ_API_KEY` | Primary LLM provider (Groq) | For LLM features |
| `OPENCODE_API_KEY` | Fallback LLM (Opencode Zen) | Optional |
| `SUPABASE_URL` | Supabase project URL | For memory features |
| `SUPABASE_KEY` | Supabase anon/service_role key | For memory features |
| `SECRET_KEY` | Flask secret key | Auto-generated if absent |
| `FLASK_DEBUG` | Debug mode (1=on) | Optional |
| `HOST` | Bind address (default: 0.0.0.0) | Optional |
| `PORT` | Listen port (default: 8000) | Optional |
| `AND9_STRICT_VALIDATION` | Strict mode (1=on) | Optional |
| `SERP_API_KEY` | Web search | Optional |
| `NEWS_API_KEY` | News fetch | Optional |
| `WEATHER_API_KEY` | Weather | Optional |

### 10.2 Python Dependencies (`requirements.txt`)

```
flask~=3.1.0               # Web framework
gunicorn~=23.0.0           # Production WSGI server
requests~=2.32.0           # HTTP client
openai~=1.82.0             # OpenAI-compatible LLM client
edge-tts~=7.0              # Microsoft Edge TTS
supabase~=2.0              # Supabase PostgreSQL client
youtube-search-python~=1.6.6  # YouTube search
beautifulsoup4~=4.13.0     # HTML parsing
Pillow>=10.0.0             # Image handling
spacy~=3.8.0               # NLP
numpy>=2.0.0               # Numerical operations
python-dotenv~=1.0.0       # .env file support
pytest~=9.1.0              # Testing
```

### 10.3 Supabase Schema (Required Tables)

From `app/core/supabase_schema.sql`:
- `episodes` — Conversation turn storage
- `facts` / `user_facts` — Semantic memory
- `goals` — Goal tracking
- `events` — Event/reminder storage
- `sessions` — Conversation sessions
- `emotions` — Emotional context tracking
- `procedural_memory` — Learned skills
- `knowledge_graph` — Entity relationships

### 10.4 Docker Configuration

- **Dockerfile:** Multi-stage build, Python 3.11+
- **docker-compose.yml:** Single service with env vars
- **deploy/render.yaml:** Render.com deployment config

---

## 11. Known Bugs & Issues

### Bug 1: Missing `get_recall_cache_stats` import
- **File:** `app/api/routes.py` line 267
- **Error:** `ImportError: cannot import name 'get_recall_cache_stats' from 'app.core.memory'`
- **Impact:** `GET /api/memory/cache/stats` returns 500
- **Fix:** Implement `get_recall_cache_stats()` in memory.py, or remove the route

### Bug 2: Missing `get_sessions_summary` method
- **File:** `app/api/routes.py` line 289
- **Error:** `AttributeError: 'Memory' object has no attribute 'get_sessions_summary'`
- **Impact:** `GET /api/memory/sessions` returns 500
- **Fix:** Implement `get_sessions_summary()` in Memory class, or remove the route

### Bug 3: Admin auth fails with in-process Flask compat
- **File:** `app/api/admin_routes.py` line 56
- **Error:** `AttributeError: 'dict' object has no attribute 'permanent'`
- **Impact:** `POST /api/admin/auth` returns 500
- **Fix:** Guard `session.permanent` or wrap in try/except

### Bug 4: Missing `search_episodes` method
- **File:** `app/api/routes.py` line 281
- **Error:** `AttributeError: 'Memory' object has no attribute 'search_episodes'`
- **Impact:** `GET /api/memory/episodes/search?q=test` returns 500
- **Fix:** Implement `search_episodes()` in Memory, or remove the route

---

## 12. Micro Neural Brain (Offline System)

### 12.1 Overview

**Purpose:** Lightweight offline intent classifier for when internet/LLM unavailable
**RAM Budget:** 50MB (target for Android Termux)
**Model:** INT8 quantized neural network (NumPy, ~2MB)
**Entry Point:** `micro_brain/main.py`

### 12.2 Five-Brain Architecture

| Brain | Class | Purpose |
|-------|-------|---------|
| **Reflex Brain** | `ReflexBrain` | Fast pattern matching (word lists, regex) |
| **Neural Brain** | `NeuralBrain` | Neural network intent recognition |
| **Memory Brain** | `MemoryBrain` | SQLite memory (episodic, semantic, habits) |
| **Decision Brain** | `DecisionBrain` | Action planning from intent |
| **Learning Brain** | `LearningBrain` | Habit learning from observations |

### 12.3 Processing Pipeline

```
User Input
  │
  ├── Step 1: Reflex Brain → pattern match (fast)
  ├── Step 2: Neural Brain → NN intent recognition
  ├── Step 3: Combine → prefer neural if confident ≥ reflex
  ├── Step 4: Decision Brain → action plan
  ├── Step 5: Execute Action → reflex execute
  ├── Step 6: Memory Brain → save episodic memory + log activity
  ├── Step 7: Learning Brain → observe + habit prediction
  └── Return: {intent, confidence, action, pipeline, response}
```

### 12.4 Neural Network Config

| Parameter | Value |
|-----------|-------|
| Input dimension | 128 (embedding) |
| Hidden layer 1 | 64 neurons |
| Hidden layer 2 | 32 neurons |
| Learning rate | 0.01 |
| Epochs | 100 |
| Batch size | 32 |
| Max text length | 50 chars |
| Data type | INT8 (quantized) |
| Max model size | 2.0 MB |

### 12.5 Supported Intents (19)

`OPEN_APP`, `CLOSE_APP`, `PLAY_MUSIC`, `PAUSE_MUSIC`, `SEARCH_WEB`, `WEATHER`, `TIME`, `DATE`, `REMINDER`, `CALL`, `MESSAGE`, `CAMERA`, `FLASHLIGHT_ON`, `FLASHLIGHT_OFF`, `VOLUME_UP`, `VOLUME_DOWN`, `HOME`, `BACK`, `SETTING`, `UNKNOWN`

### 12.6 Operation Modes (CLI Arguments)

| Flag | Mode | Description |
|------|------|-------------|
| (none) | Console | Interactive REPL |
| `--gui` | GUI | Dashboard with customtkinter |
| `--cli "query"` | CLI | Single command, JSON output |
| `--train` | Training | Full neural network training |
| `--evaluate` | Evaluation | Model performance metrics |
| `--generate` | Dataset | Generate intent training data |

### 12.7 Resources

| Component | RAM Budget | Storage |
|-----------|-----------|---------|
| Python runtime | 20 MB | - |
| Neural model | 2 MB | ~2MB on disk (.npz) |
| SQLite | 5 MB | memory.db |
| Memory cache | 5 MB | In-memory |
| GUI | 10 MB | Optional |
| Buffers | 8 MB | Runtime |

---

## End of Reverse Engineering Document
