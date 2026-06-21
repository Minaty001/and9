# JARVIS PCOS (Personal Cognitive Operating System) — Complete Understanding Guide

## Overview

**JARVIS** is a full-stack AI personal assistant with an **Flask backend orchestrator** and a **native Android client**. It follows a **"Truth-First Architecture"** defined by **JARVIS Constitution V3** — a set of rules ensuring the AI never hallucinates, never stores LLM-inferred facts, and always tracks the source and confidence of every piece of information.

---

## 1. Repository Structure

```
/root/and9/
├── app/                           # Flask backend (Python)
│   ├── main.py                    # Flask app factory, rate limiter, blueprints
│   ├── core/                      # Core cognitive modules (19 files)
│   ├── api/                       # REST API endpoints
│   ├── agents/                    # LLM agent classes
│   ├── skills/                    # Executable tool functions
│   ├── templates/                 # HTML templates (index.html, admin.html)
│   └── static/                    # Frontend JS/CSS (7 files)
├── android/                       # Native Android app (Kotlin)
│   └── app/src/main/
│       ├── AndroidManifest.xml
│       └── java/com/jarvis/assistant/
│           ├── SetupActivity.kt           # Setup wizard
│           ├── overlay/OverlayViewController.kt  # Core UI controller (785 lines)
│           ├── services/                   # Android services (3 files)
│           └── voice/                      # TTS, STT, backend client (4 files)
├── scripts/                       # APK rebuild utilities (3 scripts)
├── tests/                         # 50+ pytest tests
├── docker-compose.yml             # Container deployment
├── Dockerfile                     # Multi-stage production build
├── render.yaml                    # Render.com deployment config
├── requirements.txt               # Python dependencies
├── .env.example                   # Environment variable template
└── README.md                      # Project documentation
```

---

## 2. Backend Architecture

### 2.1 Flask App (`app/main.py`)

The Flask application is created via a factory pattern (`create_app()`). Key features:
- **Rate Limiter**: In-memory sliding-window (30 req/min per IP)
- **Request ID tracking** via `X-Request-ID` header
- **Structured logging** with timestamps
- **Error handlers** for 404, 405, 429, 500
- **Blueprints**: `web_bp` (`/`), `api_bp` (`/api`), `admin_bp` (`/api/admin`)

Running via **Gunicorn** with 2 workers, 4 threads.

### 2.2 Core Modules (`app/core/`)

#### 2.2.1 Configuration (`config.py`)
Centralized environment-based config. Reads from `.env` or environment variables:
- **Supabase**: Primary database (PostgreSQL)
- **Groq**: Primary LLM provider (llama-3.3-70b-versatile)
- **Opencode Zen**: Fallback LLM provider (deepseek-v4-flash-free)
- **External APIs**: SerpAPI (search), NewsAPI, WeatherAPI
- **Deployment detection**: Render, Termux, Windows

#### 2.2.2 JARVIS Constitution V3 — Truth-First Architecture

The constitution has 6 active rules:

| Rule | Principle | Implementation |
|------|-----------|---------------|
| **Rule 1** | Never hallucinate — if info not in context, say "Mujhe nahi pata" | Truth Engine pre-LLM gate, personality prompt |
| **Rule 4** | Never claim memory you don't have | `verify_before_llm()` checks memory before any recall |
| **Rule 5** | Confidence map enforced on all writes | `cap_confidence()` caps by source type |
| **Rule 6** | No LLM inference stored as fact | `extract_facts_from_text()` removed everywhere |
| **Rule 7** | Whitelist-based action execution | Android `ACTION_WHITELIST` + parameter validation |
| **Rule 8** | Source tracking for all memory writes | `source`/`confidence`/`verified` on every record |

#### 2.2.3 Truth Engine (`truth_engine.py`)
Gatekeeper that validates all memory operations before they reach the LLM:
- **Confidence map**: `user_input` → 1.0, `observed` → 0.7, `regex_extraction` → 0.3, `llm_inference` → 0.0
- `validate_memory()`: Rejects LLM-inferred facts, unverified low-confidence facts, empty values
- `verify_before_llm()`: Pre-LLM gate — returns `(has_truth, guidance)`. If no verified memory exists, returns an honest "Mujhe nahi pata" response in Hinglish
- `generate_dont_know_response()`: Produces varied "I don't know" responses

#### 2.2.4 Memory System (`memory.py`)
Supabase-backed cognitive memory with in-memory fallback:
- **Chat History**: `add()` / `get_recent_chat()` — with source/confidence/verified
- **User Facts**: `learn_fact()` / `get_facts()` / `delete_fact()` / `search_facts()`
- **Session Management**: `get_or_create_session()` with 30-min timeout, `end_session()`
- **Episodic Memory**: `add_episode()` / `get_recent_episodes()` / `get_relevant_episodes()` — topic-based conversation history
- **Semantic Memory**: `store_fact()` / `get_user_profile()` / `get_facts_by_category()` / `forget_fact()` — structured knowledge
- **Emotional Memory**: `record_emotion()` / `get_emotional_context()` / `get_dominant_emotion_for_topic()`
- **Context Builder**: `build_memory_context()` — parallel Supabase queries for performance

When Supabase is unavailable, falls back to in-memory dict store (used in tests).

#### 2.2.5 Understanding Engine (`understanding.py`)
Regex and keyword-based NLU — **zero LLM calls**:
- **Intent Detection**: `memory_store`, `memory_recall`, `emotional`, `greeting`, `farewell`, `creative`, `command`, `question`, `casual`
- **Emotion Detection**: happy, sad, angry, confused, excited, anxious, neutral — with intensity scoring (1-5) using amplifiers, exclamation marks, ALL CAPS
- **Entity Extraction**: name, age, location, profession, project, preference — via regex patterns (English + Hinglish)
- **Topic Detection**: coding/programming, project, personal, work, health, education, entertainment, food, travel, technology, general
- **Expertise Estimation**: beginner / intermediate / expert (based on jargon detection)
- Returns: `MessageAnalysis` dataclass

#### 2.2.6 Personality Engine (`personality.py`)
The JARVIS system prompt — Hinglish-speaking, warm, concise (brevity enforced):
- System prompt: "Tu JARVIS hai — AI assistant, dost, aur technical partner"
- **Rule enforcement**: Never hallucinate, never claim memory you don't have, never invent information
- **Expertise levels**: beginner (simple Hinglish), intermediate (normal), expert (technical depth)
- `build_personality_prompt()`: Dynamically injects user profile, emotional context, expertise level

#### 2.2.7 Context Builder (`context_builder.py`)
Assembles the full LLM system prompt from all memory layers:
- Personality prompt → Recent conversation → Relevant past → Current analysis → Goals/Events context
- Truncates long messages to stay within token limits
- Adds a truth-first closing instruction

#### 2.2.8 Orchestrator (`orchestrator.py`)
The **central processing pipeline** — routes queries through 6 steps:
1. **Understand**: Analyze intent, emotion, entities via `UnderstandingEngine`
2. **Handle Memory Requests**: Explicit memory store/recall (bypasses LLM)
3. **Build Context + Truth Check**: Parallel Supabase fetches (memory, goals, events)
4. **Truth Engine**: Verify before LLM — if no verified memory, return "I don't know"
5. **Route & Execute**: Dispatch to appropriate agent:
   - `chat` → `ask_llm()` with full context
   - `music` → YouTube search (with preference memory)
   - `goal` → GoalTracker (add/list/complete)
   - `reminder` → EventSystem (create/list)
   - `reflection` → ReflectionEngine (daily review / session summary)
   - `search`, `coding`, `image`, `research`, `device` → respective agents
6. **Post-process**: Save episodes, tag emotions (async background thread)

Also includes `IntentRouter` — a keyword-based router for 12 intent categories.

#### 2.2.9 Brain (`brain.py`)
Central LLM interface:
- **Provider priority**: Groq → Opencode Zen
- Calls `_groq_call()` first, falls back to `_opencode_call()`
- `ask_llm()`: Public interface — builds payload, tries providers, returns response
- `ask_llm_json()`: For structured JSON responses
- Groq timeout: 12s (fast fail → fallback); Opencode timeout: 20s
- **No fact extraction** — the old `extract_facts_from_text()` was removed per Constitution V3

#### 2.2.10 Other Core Modules
- **`intent_router.py`**: LLM-powered intent classifier with TTL cache and keyword fallback — 15 intent categories
- **`goal_tracker.py`**: CRUD for goals and projects via Supabase
- **`events.py`**: Reminder/event system with Hinglish time parsing
- **`reflection.py`**: Session summaries and daily reviews via LLM
- **`knowledge_graph.py`**: Entity-relationship graph (source → relationship → target triples)
- **`proactive.py`**: Time-aware suggestions, morning/evening tips, productivity streak
- **`timer.py`**: In-memory countdown timers with background worker thread
- **`working_memory.py`**: Current session state (focus, task, state)
- **`activity_logger.py`**: Daily conversation logging to text files

### 2.3 API Endpoints (`app/api/`)

#### Chat & Agents
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat` | Main chat endpoint — processes message through orchestrator |
| GET | `/api/agents` | List available agents |
| GET | `/api/history` | Recent chat history (20 turns) |
| GET | `/health` | Health check |

#### Memory
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/memory/facts` | Get all user facts |
| POST | `/api/memory/learn` | Store a fact |
| DELETE | `/api/memory/fact` | Delete a fact |
| GET | `/api/memory/search` | Search facts by keyword |
| GET | `/api/memory/recall` | Fast cross-session memory recall |
| GET | `/api/memory/cache/stats` | Memory cache statistics |
| GET | `/api/memory/episodes/search` | Search episodic memory |
| GET | `/api/memory/sessions` | Session summaries |

#### Brain
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/brain/profile` | Full user profile |
| GET | `/api/brain/emotions` | Emotional context |
| GET | `/api/brain/sessions` | Current session info |

#### Goals
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/goals` | List goals (filter by status) |
| POST | `/api/goals` | Add a goal |
| PATCH | `/api/goals/<id>` | Update goal status |
| DELETE | `/api/goals/<id>` | Delete a goal |

#### Events / Reminders
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/events` | Upcoming events (+ due) |
| POST | `/api/events` | Add an event |
| PATCH | `/api/events/<id>/done` | Mark event done |

#### Reflection
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/reflect?type=daily\|session` | Daily review or session summary |

#### Proactive Intelligence
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/proactive/briefing` | Greeting, time, tip, quick actions, streak |
| GET | `/api/proactive/suggestion` | Contextual suggestion |

#### TTS (Text-to-Speech)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/tts` | Microsoft Edge TTS — returns MP3 audio |
| GET | `/api/tts/voices` | List available Indian voices |

#### Timer
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/timer` | Create countdown timer |
| GET | `/api/timer/alerts` | Poll for expired timers |
| GET | `/api/timer/<id>` | Timer status |
| DELETE | `/api/timer/<id>` | Cancel timer |

#### Admin (`/api/admin`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/admin/auth` | Authenticate (password: "code10" or "codeten") |
| POST | `/api/admin/logout` | Revoke session |
| GET | `/api/admin/check` | Check authentication |
| GET | `/api/admin/files` | File browser |
| GET | `/api/admin/file` | Read file content |
| PUT | `/api/admin/file` | Write/edit file |
| GET | `/api/admin/data` | View stored data |
| POST | `/api/admin/data/clear` | Clear data |
| GET | `/api/admin/images` | List generated images |
| GET | `/api/admin/activities` | List activity files |
| GET | `/api/admin/activity` | Read activity file |
| PUT | `/api/admin/activity` | Edit activity file |

### 2.4 Agents (`app/agents/`)

| Agent | File | Description |
|-------|------|-------------|
| **CodingAgent** | `coding_agent.py` | Write/debug/explain/refactor code. Extracts and executes Python locally (disabled on Render) |
| **ResearchAgent** | `research_agent.py` | Multi-source research: SerpAPI search → fetch pages → LLM summarize → synthesize with citations |
| **AssistantAgent** | `assistant_agent.py` | General-purpose agent that dispatches to tools (search, image, research, reasoning, chat, device) based on pre-classified intent |

**Agent Registry** (`agents/__init__.py`): Maps agent names to classes — `coding`, `research`, `search`, `image`, `chat`, `device`

### 2.5 Skills (`app/skills/`)

| Skill | File | Description |
|-------|------|-------------|
| **Intent Executor** | `intent_executor.py` | Generates Android Intent URIs. Maps 80+ app names to packages. Methods: `open_app()`, `play_youtube()`, `set_alarm()`, `create_reminder()`, `make_call()` |
| **YouTube** | `youtube.py` | Search YouTube without API key. Detects music requests, mood/genre mapping, extracts search queries from Hinglish |
| **Image Generation** | `img.py` | SeaArt API integration. Auth → submit → poll progress → download. Supports realistic/anime/fantasy/cyberpunk/watercolor/oil styles |
| **Research** | `research.py` | SerpAPI search, web page fetching (BeautifulSoup), LLM summarization |
| **Tasks** | `tasks.py` | Web search, real-time data, news, time/date, system info. Device commands: torch, WiFi, battery, volume, brightness, camera, app opening, alarm, call — all keyword-based (no LLM) |

### 2.6 Frontend (`app/templates/` + `app/static/`)

#### Templates
- **`index.html`**: Main UI — orb section, chat bubbles, side panel (goals/reminders), memory drawer, YouTube mini-player, timer overlay, image display, bottom input bar with quick chips
- **`admin.html`**: Full admin panel — file browser/editor, data viewer, image gallery, activity viewer

#### JavaScript
- **`script.js`**: Core UI — voice recognition (en-IN for Hinglish), Canvas animation (particle system + solar system), TTS via `/api/tts`, send/receive messages, wake lock, keyboard handling
- **`jarvis_v2.js`**: Modern chat bubble UI, memory recall drawer, proactive engine integration, YouTube mini-player, toast notifications
- **`panel.js`**: Side panel — load/save goals and events, mark complete/done, quick action chips, agent badge
- **`device.js`**: Client-side device control — 150+ app URL schemes, flashlight (camera torch API), battery API, search, call, SMS, navigation, fullscreen, share, copy
- **`timer.js`**: Timer manager — countdown display, alert polling, Web Audio API beep, vibration pattern

#### CSS
- **`jarvis_v2.css`**: Modern Android-first dark theme — Outfit/JetBrains Mono fonts, glassmorphism, bubble animations, responsive
- **`style.css`**: Legacy styling for orb section, transcript/response areas

---

## 3. Android Client (`android/`)

### Architecture
A native Android app built with Kotlin that acts as the **voice interaction frontend** for JARVIS. All AI processing goes through the server-side orchestrator — **no direct LLM calls from the app**.

### Components

#### Services (3)
| Service | File | Purpose |
|---------|------|---------|
| `JarvisVoiceInteractionService` | `services/JarvisVoiceInteractionService.kt` | Entry point — system digital assistant app service |
| `JarvisSessionService` | `services/JarvisSessionService.kt` | Manages assistant UI session lifecycle, inflates overlay |
| `JarvisAccessibilityService` | `services/JarvisAccessibilityService.kt` | System-level actions: home, back, recents, close_app, clickText |

#### Setup Activity
`SetupActivity.kt`: Launcher for first-run configuration — permission grants (mic, camera, contacts, storage), default assistant setup (RoleManager), accessibility service toggle, backend URL/API key configuration

#### Overlay Controller
`OverlayViewController.kt` (785 lines): The **core controller** — state machine (IDLE → LISTENING → PROCESSING → SPEAKING), speech recognition, backend communication, action execution with whitelist:
- **Safe actions**: torch, volume, alarm, open/close app, home, back, browser, search, camera, settings panels, screenshot, notifications, vibrate
- **Dangerous actions** (blocked unless confirmed): call, create_file, read_file, delete_file
- **App launching**: package name → app label → Play Store fallback
- TTS integration with auto-restart listening

#### Voice Modules
| Module | File | Purpose |
|--------|------|---------|
| `JarvisBackendClient` | `voice/JarvisBackendClient.kt` | OkHttp client to Flask backend (`/api/chat`) |
| `JarvisTts` | `voice/JarvisTts.kt` | Android TTS with hi-IN/en-IN locale |
| `WaveformView` | `voice/WaveformView.kt` | Custom animated audio amplitude visualization |
| `DebugLogger` | `voice/DebugLogger.kt` | In-memory ring buffer (100 entries) |

### Permissions (in Manifest)
17 permissions: RECORD_AUDIO, CAMERA, CALL_PHONE, READ/WRITE_CONTACTS, MANAGE/READ/WRITE_EXTERNAL_STORAGE, SYSTEM_ALERT_WINDOW, FOREGROUND_SERVICE*, SET_ALARM, POST_NOTIFICATIONS, BIND_VOICE_INTERACTION, BIND_ACCESSIBILITY_SERVICE, QUERY_ALL_PACKAGES, WAKE_LOCK, MODIFY_AUDIO_SETTINGS, VIBRATE, EXPAND_STATUS_BAR

---

## 4. APK Rebuild Scripts (`scripts/`)

| Script | Purpose |
|--------|---------|
| `rebuild_apk.py` | Rebuild `jarvis.apk` with updated permissions — removes camera/location/storage, adds SYSTEM_ALERT_WINDOW/FOREGROUND_SERVICE_MICROPHONE |
| `rebuild_user_apk.py` | Rebuild user's existing APK from `/storage/emulated/0/jarvis.apk` — strips digital assistant service, injects MANAGE_EXTERNAL_STORAGE/CALL_PHONE/READ_CONTACTS |
| `rebuild_apk_assistant.py` | Rebuild APK with full VoiceInteractionService + AccessibilityService support for digital assistant functionality |

All use: `aapt` / `aapt2` → `zipalign` → `apksigner`

---

## 5. Database Schema

**Supabase** (PostgreSQL) with 9 tables (see `app/core/supabase_schema.sql`):

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `chat_history` | Message log | role, content, source, confidence, verified |
| `user_facts` | User facts | fact_key, fact_value, fact_type, source, confidence |
| `conversation_sessions` | Session tracking | started_at, ended_at, summary, dominant_emotion |
| `episodic_memory` | Topic-based episodes | session_id, role, content, topic, emotion, importance |
| `semantic_memory` | Structured knowledge | category, fact_key, fact_value, confidence, source, verified |
| `emotional_memory` | Emotion tracking | topic, emotion, intensity, context, source |
| `goals` | Goal management | title, priority, status, deadline, project_id |
| `projects` | Project tracking | name, description, status |
| `events` | Reminders/events | title, event_time, notes, repeat, done |

---

## 6. Processing Pipeline

```
User Input
    │
    ▼
[1] Understanding Engine (regex/keyword)
    │  intent, emotion, entities, topic, expertise
    ▼
[2] Memory Request? → Yes → Store/Recall → Return response
    │                          (no LLM involved)
    No
    ▼
[3] Parallel Fetch
    │  ├─ Memory Context (Supabase)
    │  ├─ Goals Context
    │  └─ Events Context
    ▼
[4] Truth Engine (verify_before_llm)
    │  Has verified memory? → No → "Mujhe nahi pata"
    │
    Yes
    ▼
[5] Context Builder → Rich system prompt
    │
    ▼
[6] Route & Execute
    │  ├─ music → YouTube search
    │  ├─ goal → GoalTracker
    │  ├─ reminder → EventSystem
    │  ├─ reflection → ReflectionEngine
    │  ├─ coding → CodingAgent (LLM)
    │  ├─ research → ResearchAgent (LLM)
    │  ├─ search/image → AssistantAgent
    │  └─ chat → ask_llm()
    │
    ▼
[7] Post-Process (async)
    │  Save episodes, record emotions
    ▼
Response → Client
```

---

## 7. Deployment

### Docker
- Multi-stage Dockerfile: builder (install deps) → runtime (non-root user)
- `docker-compose.yml`: Flask service on port 8000, health check, persistent data volume

### Render.com
- `render.yaml`: Web service with Python 3.11, gunicorn, health check path `/health`
- Secrets: GROQ_API_KEY, SERP_API_KEY, NEWS_API_KEY, SECRET_KEY
- Free plan, Oregon region

### Environment Configuration
Required: `GROQ_API_KEY`
Optional: `SERP_API_KEY`, `NEWS_API_KEY`, `WEATHER_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`
Flask: `SECRET_KEY`, `FLASK_ENV`, `FLASK_DEBUG`

---

## 8. Tests (`tests/`)

50+ pytest tests covering:
- **Core config**: API base URLs and model defaults
- **Memory**: Chat history, facts (CRUD, search, delete), sessions, episodic memory (recent, relevant), semantic memory (store, upsert, categories, forget), emotional memory (record, context, dominant emotion), context builder
- **Understanding Engine**: Intent detection (9 intents), emotion detection (5 emotions + intensity), entity extraction (name, location, age, multiple), topic detection (3 topics), full analysis
- **Personality**: System prompt verification, dynamic prompt building with profile/emotion/expertise
- **Context Builder**: Full and minimal context assembly
- **Orchestrator**: Intent routing (7 routes)
- **Agents**: Registry imports, AssistantAgent run, CodingAgent code extraction
- **Skills**: Time/date utilities
- **API endpoints**: Health check, agents, fact CRUD, search, brain profile/emotions/sessions

---

## 9. Key Design Principles

1. **Truth-First**: Never hallucinate. If no verified memory exists, say "Mujhe nahi pata"
2. **Confidence Map**: Every stored fact has a source and confidence score. LLM-inferred facts (0.0 confidence) are never stored
3. **No LLM Command Parsing**: All Android device commands parsed via keyword/regex — zero LLM calls for actions
4. **Supabase First**: All persistent storage through Supabase (PostgreSQL), with in-memory fallback for testing
5. **Provider Redundancy**: Groq primary → Opencode Zen fallback for LLM
6. **Android as Frontend**: Native Android app handles voice I/O and device control; all AI processing is server-side
7. **Hinglish Support**: Natural language understanding for Hindi-English mixed input
8. **Server-side TTS**: Microsoft Edge TTS neural voices via Flask API — no browser Speech Synthesis dependency
