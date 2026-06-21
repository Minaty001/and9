# JARVIS PCOS (Personal Cognitive Operating System) — Complete Understanding Guide

---

## Table of Contents
1. [Overview](#overview)
2. [Commands & Deployment](#commands--deployment)
3. [Repository Structure](#repository-structure)
4. [Backend Architecture](#backend-architecture)
5. [All Functions Reference](#all-functions-reference)
6. [Features — What It Can Do](#features--what-it-can-do)
7. [What It CANNOT Do](#what-it-cannot-do)
8. [How It Works — Processing Pipeline](#how-it-works--processing-pipeline)
9. [Algorithms & Methods Used](#algorithms--methods-used)
10. [Android Client](#android-client)
11. [Database Schema](#database-schema)
12. [Dependencies](#dependencies)
13. [Key Design Principles](#key-design-principles)

---

## Overview

**JARVIS** is a full-stack AI personal assistant with a **Flask backend orchestrator** and a **native Android client**. It follows a **"Truth-First Architecture"** defined by **JARVIS Constitution V3** — a set of rules ensuring the AI never hallucinates, never stores LLM-inferred facts, and always tracks the source and confidence of every piece of information.

**Tech Stack**: Python (Flask) → Supabase (PostgreSQL) → Groq LLM (primary) / Opencode Zen (fallback) → Android (Kotlin)

---

## Commands & Deployment

### Run / Dev Commands

| Command | Purpose |
|---------|---------|
| `python app/main.py` | Run Flask dev server (port 8000, 0.0.0.0) |
| `gunicorn app.main:app --workers 2 --threads 4 --timeout 120` | Production server |
| `pip install -r requirements.txt` | Install Python deps |
| `pytest tests/` | Run test suite |
| `cd android && ./gradlew assembleDebug` | Build Android APK |
| `python scripts/rebuild_apk.py` | Rebuild APK with modded permissions |
| `python scripts/rebuild_user_apk.py` | Rebuild user's existing APK |
| `python scripts/rebuild_apk_assistant.py` | Rebuild APK with Digital Assistant service |

### Docker Commands

| Command | Purpose |
|---------|---------|
| `docker-compose up --build` | Build and start Flask service |
| `docker-compose down` | Stop service |
| `docker build -t jarvis .` | Build image manually |

### Env Variables

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `GROQ_API_KEY` | ✅ | — | Primary LLM (llama-3.3-70b-versatile) |
| `SERP_API_KEY` | ❌ | — | Web search via SerpAPI |
| `NEWS_API_KEY` | ❌ | — | NewsAPI for headlines |
| `WEATHER_API_KEY` | ❌ | — | Weather data |
| `SUPABASE_URL` | ❌ | `ipvdftzjyxwjhahfkwbq.supabase.co` | PostgreSQL endpoint |
| `SUPABASE_KEY` | ❌ | — | Supabase anon/service_role key |
| `SECRET_KEY` | ✅ | Random UUID | Flask session signing |
| `FLASK_ENV` | ❌ | `production` | Environment toggle |
| `FLASK_DEBUG` | ❌ | — | Debug mode (set to `1`) |
| `RENDER` | ❌ | — | Render.com deployment flag |
| `OPENCODE_API_KEY` | ❌ | — | Fallback LLM provider |
| `ENABLE_VECTOR_SEARCH` | ❌ | `false` | Embedding search toggle |
| `EMBEDDING_MODEL` | ❌ | `text-embedding-3-small` | Embedding model name |
| `EMBEDDING_DIMENSIONS` | ❌ | `384` | Vector dimensions |
| `GROQ_CHAT_MODEL` | ❌ | `llama-3.3-70b-versatile` | Chat model override |
| `GROQ_CODING_MODEL` | ❌ | `llama-3.3-70b-versatile` | Coding model override |
| `OPENCODE_CHAT_MODEL` | ❌ | `deepseek-v4-flash-free` | Fallback chat model |
| `OPENCODE_CODING_MODEL` | ❌ | `deepseek-v4-flash-free` | Fallback coding model |

### Render.com Deploy

```
service: jarvis-neural
region: oregon (free)
command: gunicorn app.main:app --workers 2 --threads 4 --timeout 120
health: /health
```

---

## Repository Structure

```
/root/and9/
├── app/                           # Flask backend (Python)
│   ├── main.py                    # Flask app factory (142 lines)
│   ├── __init__.py                # Package marker
│   ├── core/                      # Core cognitive modules (19 files, ~5K lines)
│   │   ├── config.py              # Centralized env config (50 lines)
│   │   ├── memory.py              # Supabase cognitive memory (654 lines)
│   │   ├── brain.py               # LLM interface (Groq → Opencode) (241 lines)
│   │   ├── truth_engine.py        # Constitution V3 gatekeeper (241 lines)
│   │   ├── orchestrator.py        # Cognitive pipeline (629 lines)
│   │   ├── understanding.py       # Regex/keyword NLU engine (481 lines)
│   │   ├── intent_router.py       # LLM-powered intent classifier (262 lines)
│   │   ├── personality.py         # System prompt engine (103 lines)
│   │   ├── context_builder.py     # LLM context assembler (225 lines)
│   │   ├── goal_tracker.py        # Goal/project CRUD (175 lines)
│   │   ├── events.py              # Event/reminder system (209 lines)
│   │   ├── reflection.py          # Session/daily reflection (242 lines)
│   │   ├── knowledge_graph.py     # Entity-relationship graph (268 lines)
│   │   ├── proactive.py           # Context-aware suggestions (206 lines)
│   │   ├── timer.py               # In-memory countdown (154 lines)
│   │   ├── working_memory.py      # Session state manager (152 lines)
│   │   ├── activity_logger.py     # Daily file logging
│   │   └── supabase_schema.sql    # Full DB schema
│   ├── api/                       # REST API endpoints
│   │   ├── routes.py              # Main JSON API (583 lines)
│   │   ├── web_routes.py          # HTML page routes (11 lines)
│   │   └── admin_routes.py        # Admin panel API (359 lines)
│   ├── agents/                    # LLM agent classes
│   │   ├── __init__.py            # Agent registry (20 lines)
│   │   ├── coding_agent.py        # Code generation/debug/explain (111 lines)
│   │   ├── research_agent.py      # Multi-source research (48 lines)
│   │   └── assistant_agent.py     # Unified dispatch agent (81 lines)
│   ├── skills/                    # Executable tool functions
│   │   ├── tasks.py               # Web search, time, news, device control (308 lines)
│   │   ├── intent_executor.py     # Android Intent URI generation (235 lines)
│   │   ├── youtube.py             # YouTube search (141 lines)
│   │   ├── img.py                 # SeaArt image generation (263 lines)
│   │   └── research.py            # SerpAPI + page fetch + summarize (102 lines)
│   ├── templates/                 # HTML templates
│   │   ├── index.html             # Main chat UI
│   │   └── admin.html             # Admin panel
│   └── static/                    # Frontend assets (7 files)
│       ├── style.css              # Base styles
│       ├── jarvis_v2.css          # Android-first premium UI
│       ├── script.js              # Voice, canvas, core UI
│       ├── jarvis_v2.js           # Chat bubbles, memory drawer, YouTube
│       ├── device.js              # 150+ Android app URL schemes
│       ├── panel.js               # Goals & reminders sidebar
│       └── timer.js               # Timer countdown alerts
├── android/                       # Native Android app (Kotlin)
│   ├── app/src/main/
│   │   ├── AndroidManifest.xml    # 17 permissions
│   │   ├── res/                   # Layouts, drawables, animations
│   │   └── java/com/jarvis/assistant/
│   │       ├── SetupActivity.kt           # Permission wizard
│   │       ├── overlay/OverlayViewController.kt  # Core overlay (785 lines)
│   │       ├── services/JarvisAccessibilityService.kt
│   │       ├── services/JarvisSessionService.kt
│   │       ├── services/JarvisVoiceInteractionService.kt
│   │       └── voice/
│   │           ├── JarvisBackendClient.kt
│   │           ├── JarvisTts.kt
│   │           ├── WaveformView.kt
│   │           └── DebugLogger.kt
│   └── build.gradle               # AGP 8.2.2, Kotlin 1.9.22
├── scripts/                       # APK rebuild utilities
│   ├── rebuild_apk.py             # Rebuild with minimal permissions
│   ├── rebuild_user_apk.py        # Custom user APK rebuild
│   └── rebuild_apk_assistant.py   # Rebuild with Digital Assistant
├── tests/                         # pytest suite
│   ├── __init__.py
│   └── test_imports.py            # 50+ tests
├── Dockerfile                     # Multi-stage production build
├── docker-compose.yml             # Flask + healthcheck
├── render.yaml                    # Render.com config
├── build.sh                       # pip install + verify
├── requirements.txt               # 12 production deps
├── .env.example                   # Template
└── .gitignore
```

---

## Backend Architecture

### Flask App (`app/main.py`)

**Factory function**: `create_app() → Flask`

**Components**:
- **RateLimiter**: In-memory sliding-window per IP (30 req / 60s). Methods: `check(key) → (allowed, retry_after)`
- **Request ID**: Every request gets `X-Request-ID` via `g.request_id`
- **Structured logging**: Timestamps, module names, log levels
- **Error handlers**: 404, 405, 429, 500 — all return JSON
- **Blueprints**: `web_bp` (`/`), `api_bp` (`/api`), `admin_bp` (`/api/admin`)

**Rate Limiter Algorithm**:
- Maintains a `dict[str, list[float]]` mapping IP → timestamps
- On each request: prune timestamps older than 60s, check count < 30
- If exceeded: return 429 with `Retry-After` header
- O(1) amortized per request

### Core Modules (`app/core/`)

#### config.py — Configuration
- **Method**: `_str_env(key, default) → str` (cached via `@lru_cache`)
- Reads all secrets from environment, never hardcoded
- Auto-detects deployment: `IS_RENDER`, `IS_TERMUX`, `IS_WINDOWS`
- Configurable model overrides for both providers

#### memory.py — Cognitive Memory (Supabase-backed)
**Singleton pattern**: Lazy Supabase client via `_get_client()` → `supabase.create_client()`

**Functions**:
| Function | Returns | Purpose |
|----------|---------|---------|
| `Memory.__init__(db_path)` | — | Init Supabase client or in-memory fallback |
| `Memory.add(role, content, source, confidence, verified)` | — | Store chat message with source tracking |
| `Memory.get_recent_chat(limit) → list` | `[{role, content}]` | Get last N messages |
| `Memory.get_chat_count() → int` | Count | Total chat messages |
| `Memory.clear_chat_history()` | — | Delete all messages |
| `Memory.learn_fact(key, value, fact_type, priority, source, confidence, verified)` | — | Store user fact |
| `Memory.get_facts(fact_type, min_confidence) → dict` | `{key: value}` | Get facts filtered by type/confidence |
| `Memory.delete_fact(key) → bool` | Success | Remove a fact |
| `Memory.search_facts(keyword) → dict` | `{key: value}` | ILIKE search across fact values |
| `Memory.get_or_create_session(timeout_minutes) → int` | Session ID | Find open session or create new one (30-min timeout) |
| `Memory.end_session(session_id, summary)` | — | Close session with summary |
| `Memory.get_session_history(session_id) → list` | Episodes | All episodes for a session |
| `Memory.add_episode(role, content, topic, emotion, importance, source, confidence, verified) → int` | Episode ID | Store conversation turn |
| `Memory.get_recent_episodes(limit) → list` | Episodes | Last N episodes |
| `Memory.get_relevant_episodes(topic, limit) → list` | Episodes | ILIKE topic match |
| `Memory.get_episode_count() → int` | Count | Total episodes |
| `Memory.store_fact(category, key, value, confidence, source, verified)` | — | Semantic fact storage (Constitution V3) |
| `Memory.get_user_profile() → dict` | `{category: {key: value}}` | All semantic facts grouped |
| `Memory.get_verified_facts(min_confidence) → dict` | Facts | Only verified facts above threshold |
| `Memory.get_facts_by_category(category) → dict` | `{key: value}` | Facts for one category |
| `Memory.confirm_fact(category, key)` | — | Mark fact as verified |
| `Memory.forget_fact(category, key) → bool` | Success | Delete semantic fact |
| `Memory.record_emotion(topic, emotion, intensity, episode_id, context, source, confidence)` | — | Store emotional state |
| `Memory.get_emotional_history(topic) → list` | Entries | All emotions for a topic |
| `Memory.get_emotional_context() → dict` | `{topic: {emotion, intensity}}` | Latest emotion per unique topic |
| `Memory.get_dominant_emotion_for_topic(topic) → str` | Emotion | Most frequent emotion |
| `Memory.build_memory_context(current_topic, limit) → dict` | Context | Parallel Supabase fetch (4 threads) |

**Fallback**: When no `SUPABASE_KEY`, uses in-memory dict (`self._mem`).

#### truth_engine.py — Constitution V3 Gatekeeper

**Confidence Map**:
| Source | Max Confidence |
|--------|---------------|
| `user_input`, `direct_statement`, `user_stated`, `system` | 1.0 |
| `observed`, `observed_pattern`, `cross_session` | 0.7 |
| `regex_extraction`, `keyword_detection` | 0.3 |
| `llm_inference`, `llm_extraction`, `ai_inferred` | 0.0 ❌ |

**Functions**:
| Function | Returns | Algorithm |
|----------|---------|-----------|
| `validate_memory(value, source, confidence, verified) → bool` | Valid? | Rejects empty, LLM-inferred, unverified low-confidence |
| `cap_confidence(source) → float` | Capped score | Lookup in CONFIDENCE_MAP |
| `get_source_type(source) → str` | Normalized source | Fuzzy matching against known sources |
| `has_relevant_memory(memory_ctx, query) → bool` | Has data? | Checks user_profile + recent_episodes + relevant_past |
| `generate_dont_know_response(topic) → str` | Hinglish response | Random selection from multi-response pool |
| `verify_before_llm(memory_ctx, query) → (bool, str)` | (has_truth, guidance) | Full pre-LLM gate: has_relevant_memory → generate_dont_know |
| `annotate_facts_with_confidence(facts) → list` | Annotated | Maps each fact to confidence + valid flag |

#### brain.py — Central LLM Interface

**Provider chain**: Groq → Opencode Zen

**Functions**:
| Function | Returns | Detail |
|----------|---------|--------|
| `ask_llm(messages, model, system, context, temperature, max_tokens) → str` | Response | Tries Groq first (12s timeout), falls back to Opencode (20s) |
| `ask_llm_json(messages, model, system) → dict` | Parsed JSON | Calls ask_llm, extracts `{...}` via regex, json.loads |
| `get_available_models() → list` | Model names | Combined list from both providers |
| `_groq_call(payload, model, temperature, max_tokens) → Optional[str]` | Response/None | POST to Groq API, 12s timeout |
| `_opencode_call(payload, model, temperature, max_tokens) → Optional[str]` | Response/None | POST to Opencode API, 20s timeout |
| `_resolve_opencode_model(requested) → str` | Best model | Fetches model list, prefers free models |
| `_get_opencode_models() → list` | Models | Cached fetch of available Opencode models |

**API endpoints used**:
- Groq: `POST {GROQ_API_BASE}/chat/completions`
- Opencode: `GET {OPENCODE_API_BASE}/models` + `POST {OPENCODE_API_BASE}/chat/completions`

#### orchestrator.py — Central Processing Pipeline

**Classes**:
1. **IntentRouter** — Keyword-based router (zero LLM):
   - `PATTERNS` dict: 10 intent categories with Hinglish keyword lists
   - `route(query) → str`: Returns intent name (search, coding, image, music, goal, reminder, reflection, device, research, chat)

2. **Orchestrator** — Cognitive pipeline:
   - `run(query) → dict`: Full 6-step pipeline
   - `_handle_memory_store()`, `_handle_memory_recall()`: Memory CRUD (bypass LLM)
   - `_handle_music()`: YouTube search with favorite-song memory
   - `_handle_goal()`: Add/list/complete goals
   - `_handle_reminder()`: Create/list reminders
   - `_handle_reflection()`: Daily review or session summary
   - `_post_process()`: Async background save + emotion tagging
   - `_store_entities()`: Store regex-extracted entities (confidence 0.3)
   - `_get_agent(name)`: Lazy-load agents from AGENT_REGISTRY

**TTL Cache**: 60-second cache for goals/events context (`_cached()`)

#### understanding.py — Regex/Keyword NLU Engine

**Class**: `UnderstandingEngine`

**Functions**:
| Function | Returns | Algorithm |
|----------|---------|-----------|
| `detect_intent(message) → str` | Intent label | Priority-ordered regex matching (9 intents) |
| `detect_emotion(message) → (str, int)` | (emotion, intensity 1-5) | Keyword match + intensity (amplifiers, diminishers, exclamation count, ALL CAPS ratio) |
| `extract_entities(message) → dict` | `{type: value}` | Regex group extraction (7 entity types) |
| `detect_topic(message) → str` | Topic | Keyword matching across 11 topic categories |
| `detect_expertise(message, user_profile) → str` | beginner/intermediate/expert | Profile check → jargon detection → beginner patterns |
| `analyze(message, user_profile) → MessageAnalysis` | Full analysis | Runs all above, returns dataclass |

**Data Class**: `MessageAnalysis` — intent, emotion, emotion_intensity, entities, is_memory_store, is_memory_recall, topic, expertise_level

#### intent_router.py — LLM-Powered Intent Classifier

**Class**: `LLMIntentRouter`

**Functions**:
| Function | Returns | Detail |
|----------|---------|--------|
| `classify(query) → dict` | `{intent, parameters, confidence}` | Cache-check → LLM → fallback |
| `_classify_via_llm(query) → dict` | Classified | Calls `ask_llm` with CLASSIFY_PROMPT, parses JSON |
| `_fallback_classify(query) → dict` | Fallback result | Keyword matching for 13 intents + parameter extraction |
| `_extract_fallback_params(intent, q) → dict` | Parameters | Intent-specific regex extraction |

**15 intents**: music, device_app, device_call, device_control, timer, reminder, goal, search, research, image, coding, reflection, memory, chat

**Cache**: MD5 hash of query → 60s TTL

#### personality.py — System Prompt Engine

**Constants**:
- `SYSTEM_PROMPT`: Base prompt — Hinglish, warm, concise, truth-first (Rule 1/4/6 enforcement)

**Functions**:
| Function | Returns | Detail |
|----------|---------|--------|
| `build_personality_prompt(user_profile, emotional_context, expertise_level) → str` | Full system prompt | Injects profile, emotional context, expertise instructions |

**Expertise levels**:
- `beginner`: Simple Hinglish, avoid jargon, real-life analogies
- `intermediate`: Normal Hinglish, moderate technical detail
- `expert`: Full technical depth, advanced concepts

#### context_builder.py — LLM Context Assembler

**Class**: `ContextBuilder`

**Functions**:
| Function | Returns | Detail |
|----------|---------|--------|
| `build(user_profile, emotional_context, recent_episodes, relevant_past, current_analysis, extra_context) → str` | Full prompt | Personality → Recent → Relevant → Analysis → Goals/Events → Truth-footer |
| `build_minimal(user_profile, expertise_level) → str` | Minimal prompt | For non-chat agents |
| `_format_recent_episodes(episodes, max_count) → str` | Formatted | Limits to 8 episodes, truncates 500 chars |
| `_format_relevant_past(episodes) → str` | Formatted | With timestamps, 400-char truncation |
| `_format_current_analysis(analysis) → str` | Formatted | Emotion, intent, topic, expertise, memory flags |

#### goal_tracker.py — Goal/Project CRUD

**Class**: `GoalTracker`
**Constants**: STATUS_ACTIVE, STATUS_DONE, STATUS_PAUSED, STATUS_CANCELLED, PRIORITY_*

**Functions**: `add_goal()` / `get_active_goals()` / `complete_goal()` / `update_goal_status()` / `get_all_goals()` / `delete_goal()`
**Projects**: `add_project()` / `get_active_projects()`
**Context**: `build_goal_context() → str` — compact string for LLM prompt injection

#### events.py — Event/Reminder System

**Class**: `EventSystem`

**Functions**: `add_event()` / `get_upcoming_events(hours_ahead)` / `get_due_events()` / `mark_done()` / `get_all_events()`
**NLP**: `parse_event_from_text(text) → dict` — Extracts time (relative: "30 min mein", absolute: "kal 5 baje") + title
**Context**: `build_event_context() → str` — "DUE NOW" + upcoming events

#### reflection.py — Session/Daily Summarizer

**Class**: `ReflectionEngine`

**Functions**:
| Function | Returns | Detail |
|----------|---------|--------|
| `reflect_on_session(session_id, ask_llm_fn) → str` | Summary | Builds transcript from episodes → LLM summarizes in Hinglish |
| `daily_review(ask_llm_fn) → str` | Review | Last 24h episodes → LLM summaries (discussed, decisions, pending, suggestions) |
| `extract_key_facts(session_id) → list` | Facts | Regex-only extraction (Constitution V3 — no LLM) |

#### knowledge_graph.py — Entity-Relationship Graph

**Class**: `KnowledgeGraph`
**Data model**: `source → relationship → target` triples with weight, access_count, last_seen

**Functions**:
| Function | Returns | Detail |
|----------|---------|--------|
| `add_triple(source, relationship, target, weight, source_type, target_type, metadata) → bool` | Success | Upsert: find → bump weight OR insert new |
| `get_related(entity, max_depth, limit) → list` | Triples | Outgoing + incoming edges (weight DESC) |
| `get_by_relationship(relationship, limit) → list` | Triples | Filter by relationship type |
| `search(keyword, limit) → list` | Triples | ILIKE on source/relationship/target |
| `get_all_entities(entity_type) → list` | Entities | Distinct entity names |
| `build_graph_context(topic, max_relations) → str` | Context string | For LLM prompt injection |
| `extract_and_store(entities) → int` | Count | Converts flat dict to triples (User → has_X → value) |
| `delete_triple(triple_id) → bool` | Success | Remove by ID |

#### proactive.py — Proactive Suggestion Engine

**Class**: `ProactiveEngine`

**Functions**:
| Function | Returns | Detail |
|----------|---------|--------|
| `get_time_context() → dict` | Time info | hour, period (morning/afternoon/evening/night), is_weekend |
| `get_smart_greeting(user_profile) → str` | Personalized | Time-aware + user name |
| `get_proactive_suggestion(emotion, topic) → str` | Suggestion | 30-min cooldown, mood-based/focus/morning/evening tips |
| `get_daily_briefing() → dict` | Briefing | time, date, weekday, tip, greeting |
| `analyze_productivity_streak(episodes) → dict` | Streak stats | Date extraction from timestamps, unique day count |
| `get_android_quick_actions(user_profile) → list` | Action chips | Time-aware + always-present (max 6) |

**Tip pools**: Morning (4), Evening (4), Focus (3), Motivation (4), Health (4)

#### timer.py — In-Memory Countdown Service

**Class**: `TimerService`
**Data model**: `Timer(id, label, end_time, duration_secs, alerted, created_at)`

**Functions**:
| Function | Returns | Detail |
|----------|---------|--------|
| `create_timer(duration_secs, label) → dict` | Timer info | Creates Timer, returns id/remaining/end |
| `get(timer_id) → dict` | Status | remaining seconds, expired flag |
| `get_alerts() → list` | Expired | Claim-based — each timer returned exactly once |
| `cancel(timer_id) → bool` | Success | Removes from dict |
| `active_count() → int` | Count | Total active timers |

**Background worker**: Daemon thread, wakes every 1s, prunes stale timers (>1h)

#### working_memory.py — Session State

**Class**: `WorkingMemory`
**Storage**: Supabase `working_memory` table + in-memory cache

**Functions**: `set_focus()` / `get_focus()` / `set_current_task()` / `get_current_task()` / `set_state()` / `get_state()` / `set_metadata()` / `get_metadata()` / `clear()`

### Agents (`app/agents/`)

#### Agent Registry

```python
AGENT_REGISTRY = {
    "coding": CodingAgent,
    "research": ResearchAgent,
    "search": AssistantAgent,
    "image": AssistantAgent,
    "chat": AssistantAgent,
    "device": AssistantAgent,
}
```

#### CodingAgent

**Methods**: `run(query)`, `_write(query)`, `_explain(query)`, `_debug(query)`, `_improve(query)`, `_extract_code(text) → (code, lang)`, `_execute_python(code, timeout) → str`

**Flow**: LLM generates code → extracts ``` blocks → optionally executes Python via `subprocess` with `tempfile` (disabled on Render)

#### ResearchAgent

**Flow**: `search_sources(SerpAPI)` → `fetch_page(BeautifulSoup)` per source → `summarize_source(LLM)` per source → `ask_llm(synthesis)` → return with citations

**Methods**: `run(query)`

#### AssistantAgent

**Methods**: `run(query, intent_name, intent_params)`, `_handle_search()`, `_handle_research()`, `_handle_reasoning()`, `_handle_image()`, `_handle_chat()`, `_handle_device()`

### Skills (`app/skills/`)

#### tasks.py — Task Functions

**Functions**:
| Function | Returns | Detail |
|----------|---------|--------|
| `search_web(query) → str` | Answer | SerpAPI → answer_box → organic_results |
| `get_realtime_data(query) → str` | Data | SerpAPI with knowledge_graph fallback |
| `get_time() → str` | Formatted | `datetime.now().strftime(...)` |
| `get_time_date() → str` | Formatted | Alias for get_time |
| `get_system_info() → str` | OS/Python info | platform module |
| `get_news(topic) → str` | Headlines | NewsAPI (top-headlines or everything) |
| `generate_image_task(prompt) → dict` | `{result, image_url}` | Delegates to img.py |
| `handle_device_command(query) → dict` | `{reply, action, payload}` | Keyword-based: torch, wifi, battery, volume, brightness, camera, open_app, alarm, call |

**Device Command Parsing Algorithm**:
1. Check Hinglish keywords in priority order
2. Extract parameters via regex (on/off, app name, time, number)
3. Execute locally via Termux if available
4. Return `{reply, action, payload}` for Android client to execute

#### intent_executor.py — Android Intent Generator

**Class**: `IntentExecutor`

**Data**: `APP_MAP` — 80+ app name → package mappings (Google, comms, media, tools, browsers, productivity, shopping, payments, travel, food)

**Functions**:
| Function | Returns | Detail |
|----------|---------|--------|
| `resolve_app_name(name) → str` | Normalized | Hinglish alias check (yt→youtube, wa→whatsapp, etc.) |
| `_match_app(name) → str` | Package | Exact match → longest substring match |
| `open_app(app_name) → dict` | Intent | `{action: LAUNCH_APP, package, category}` |
| `play_youtube(query, video_id) → dict` | Intent | VIEW with youtube.com URL |
| `set_alarm(hour, minute, label) → dict` | Intent | `{action: SET_ALARM, package, extras}` |
| `create_reminder(title, time_str) → dict` | Intent | Calendar event intent |
| `make_call(number) → dict` | Intent | `{action: CALL, data: tel:}` |

#### youtube.py — No-API-Key YouTube Search

**Functions**:
| Function | Returns | Algorithm |
|----------|---------|-----------|
| `is_music_request(text) → bool` | Boolean | Keyword match (25 keywords) |
| `extract_search_query(text) → str` | Search query | Mood→query map → filler removal → append "song" |
| `search_youtube(query, max_results) → dict` | `{title, url, channel, duration, thumbnail}` | `youtube-search-python` library |
| `handle_music_request(text) → dict` | Full result | Pipeline: detect → extract → search → format reply |

**Mood mapping**: 12 moods (soft→"soft hindi songs", sad→"sad hindi songs", romantic, party, ghazal, punjabi, lo-fi, etc.)

#### img.py — SeaArt Image Generation

**Functions**: `generate_image(prompt, style) → (filepath, url)`, `list_generated_images() → list`

**Pipeline**: Authenticate → Submit text-to-img → Poll progress (2s interval, 60s max) → Download → Save to `static/generated_images/`

**Styles**: realistic, anime, fantasy, cyberpunk, watercolor, oil_painting

#### research.py — Web Research Tools

**Functions**: `search_sources(query, num) → list` (SerpAPI), `fetch_page(url, max_chars) → str` (BeautifulSoup), `summarize_source(content, query, source_num) → str` (LLM), `synthesize_answer(query, sources_data) → str` (LLM)

---

## All Functions Reference

### Core Functions (app/core/)

| Function | File | Returns |
|----------|------|---------|
| `RateLimiter.check(key)` | `main.py` | `(bool, int)` |
| `Memory.add()` | `memory.py` | `None` |
| `Memory.get_recent_chat()` | `memory.py` | `list` |
| `Memory.learn_fact()` | `memory.py` | `None` |
| `Memory.get_facts()` | `memory.py` | `dict` |
| `Memory.delete_fact()` | `memory.py` | `bool` |
| `Memory.search_facts()` | `memory.py` | `dict` |
| `Memory.get_or_create_session()` | `memory.py` | `int` |
| `Memory.end_session()` | `memory.py` | `None` |
| `Memory.get_session_history()` | `memory.py` | `list` |
| `Memory.add_episode()` | `memory.py` | `int` |
| `Memory.get_recent_episodes()` | `memory.py` | `list` |
| `Memory.get_relevant_episodes()` | `memory.py` | `list` |
| `Memory.store_fact()` | `memory.py` | `None` |
| `Memory.get_user_profile()` | `memory.py` | `dict` |
| `Memory.get_verified_facts()` | `memory.py` | `dict` |
| `Memory.confirm_fact()` | `memory.py` | `None` |
| `Memory.forget_fact()` | `memory.py` | `bool` |
| `Memory.record_emotion()` | `memory.py` | `None` |
| `Memory.get_emotional_history()` | `memory.py` | `list` |
| `Memory.get_emotional_context()` | `memory.py` | `dict` |
| `Memory.get_dominant_emotion_for_topic()` | `memory.py` | `str` |
| `Memory.build_memory_context()` | `memory.py` | `dict` |
| `validate_memory()` | `truth_engine.py` | `bool` |
| `cap_confidence()` | `truth_engine.py` | `float` |
| `verify_before_llm()` | `truth_engine.py` | `(bool, str)` |
| `has_relevant_memory()` | `truth_engine.py` | `bool` |
| `generate_dont_know_response()` | `truth_engine.py` | `str` |
| `ask_llm()` | `brain.py` | `str` |
| `ask_llm_json()` | `brain.py` | `dict` |
| `UnderstandingEngine.analyze()` | `understanding.py` | `MessageAnalysis` |
| `UnderstandingEngine.detect_intent()` | `understanding.py` | `str` |
| `UnderstandingEngine.detect_emotion()` | `understanding.py` | `(str, int)` |
| `UnderstandingEngine.extract_entities()` | `understanding.py` | `dict` |
| `UnderstandingEngine.detect_topic()` | `understanding.py` | `str` |
| `UnderstandingEngine.detect_expertise()` | `understanding.py` | `str` |
| `LLMIntentRouter.classify()` | `intent_router.py` | `dict` |
| `build_personality_prompt()` | `personality.py` | `str` |
| `ContextBuilder.build()` | `context_builder.py` | `str` |
| `ContextBuilder.build_minimal()` | `context_builder.py` | `str` |
| `Orchestrator.run()` | `orchestrator.py` | `dict` |
| `GoalTracker.add_goal()` | `goal_tracker.py` | `dict` |
| `GoalTracker.get_active_goals()` | `goal_tracker.py` | `list` |
| `GoalTracker.complete_goal()` | `goal_tracker.py` | `bool` |
| `GoalTracker.build_goal_context()` | `goal_tracker.py` | `str` |
| `EventSystem.add_event()` | `events.py` | `dict` |
| `EventSystem.get_upcoming_events()` | `events.py` | `list` |
| `EventSystem.parse_event_from_text()` | `events.py` | `dict` |
| `EventSystem.build_event_context()` | `events.py` | `str` |
| `ReflectionEngine.reflect_on_session()` | `reflection.py` | `str` |
| `ReflectionEngine.daily_review()` | `reflection.py` | `str` |
| `ReflectionEngine.extract_key_facts()` | `reflection.py` | `list` |
| `KnowledgeGraph.add_triple()` | `knowledge_graph.py` | `bool` |
| `KnowledgeGraph.get_related()` | `knowledge_graph.py` | `list` |
| `KnowledgeGraph.search()` | `knowledge_graph.py` | `list` |
| `KnowledgeGraph.build_graph_context()` | `knowledge_graph.py` | `str` |
| `ProactiveEngine.get_smart_greeting()` | `proactive.py` | `str` |
| `ProactiveEngine.get_proactive_suggestion()` | `proactive.py` | `str` |
| `ProactiveEngine.get_daily_briefing()` | `proactive.py` | `dict` |
| `ProactiveEngine.get_android_quick_actions()` | `proactive.py` | `list` |
| `TimerService.create_timer()` | `timer.py` | `dict` |
| `TimerService.get_alerts()` | `timer.py` | `list` |
| `WorkingMemory.set_focus()` | `working_memory.py` | `bool` |
| `WorkingMemory.get_focus()` | `working_memory.py` | `str` |
| `ActivityLogger.log()` | `activity_logger.py` | `None` |

### API Endpoint Functions (app/api/)

| Endpoint | Method | Function | Returns |
|----------|--------|----------|---------|
| `/api/chat` | POST | `chat()` | `{reply, agent, time_ms, image_url, youtube_url, brain}` |
| `/api/agents` | GET | `list_agents()` | List of agent objects |
| `/api/history` | GET | `get_history()` | 20 recent messages |
| `/api/memory/facts` | GET | `get_facts()` | All facts dict |
| `/api/memory/learn` | POST | `learn_fact()` | `{status, key}` |
| `/api/memory/fact` | DELETE | `delete_fact()` | `{status, key}` |
| `/api/memory/search` | GET | `search_facts()` | Matching facts |
| `/api/memory/recall` | GET | `fast_recall()` | `{matched_episodes, user_profile, recent_chat, sessions_summary}` |
| `/api/memory/cache/stats` | GET | `recall_cache_stats()` | Cache metrics |
| `/api/memory/episodes/search` | GET | `search_episodes()` | `{keyword, results, count}` |
| `/api/memory/sessions` | GET | `sessions_summary()` | Recent session summaries |
| `/api/brain/profile` | GET | `brain_profile()` | Full user profile |
| `/api/brain/emotions` | GET | `brain_emotions()` | Emotional context |
| `/api/brain/sessions` | GET | `brain_sessions()` | Current session info |
| `/api/goals` | GET/POST | `list_goals()`/`add_goal()` | Goals array or created goal |
| `/api/goals/<id>` | PATCH/DELETE | `update_goal()`/`delete_goal()` | Status |
| `/api/events` | GET/POST | `list_events()`/`add_event()` | Events array or created event |
| `/api/events/<id>/done` | PATCH | `mark_event_done()` | Status |
| `/api/reflect` | GET | `reflect()` | Daily review or session summary |
| `/api/health` | GET | `health()` | `{status: ok}` |
| `/api/proactive/briefing` | GET | `proactive_briefing()` | `{greeting, time, date, suggestion, streak, quick_actions}` |
| `/api/proactive/suggestion` | GET | `proactive_suggestion()` | Single suggestion |
| `/api/tts` | POST | `tts()` | `audio/mpeg` stream |
| `/api/tts/voices` | GET | `tts_voices()` | Available Indian voices |
| `/api/timer` | POST | `create_timer()` | `{id, remaining, end_time, label}` |
| `/api/timer/alerts` | GET | `timer_alerts()` | `{alerts: [...]}` |
| `/api/timer/<id>` | GET/DELETE | `timer_status()`/`cancel_timer()` | Status or cancelled |

---

## Features — What It Can Do

### General
- ✅ Conversational AI in Hinglish (Hindi-English mix)
- ✅ Follow Constitution V3: never hallucinate, never invent information
- ✅ Truth-First: says "Mujhe nahi pata" when no verified memory exists
- ✅ User expertise adaptation (beginner/intermediate/expert)
- ✅ Emotion detection and empathetic responses

### Memory
- ✅ Store facts about user (name, age, location, profession, preferences)
- ✅ Recall stored facts on demand
- ✅ Cross-session conversation memory (episodic)
- ✅ Semantic memory (categorized, verified knowledge)
- ✅ Emotional memory (track moods per topic)
- ✅ Session management (30-min timeout, summaries)
- ✅ Search across all memory types

### Goals & Tasks
- ✅ Add/list/complete goals with priorities (high/medium/low)
- ✅ Manage projects with grouped goals
- ✅ Query: "Mera goal kya hai?", "Goal complete karo"

### Events & Reminders
- ✅ Create events with time parsing (Hinglish: "kal 5 baje", "30 min mein")
- ✅ List upcoming events
- ✅ Get due event alerts
- ✅ Mark events done

### Music & YouTube
- ✅ Search YouTube by song/artist name (no API key)
- ✅ Mood-based music: "soft song", "sad song", "ghazal", "bhajan"
- ✅ Favorite song memory: "koi bhi" → plays user's favorite
- ✅ Returns YouTube URL for frontend playback

### Web Search
- ✅ Real-time search via SerpAPI
- ✅ News headlines via NewsAPI
- ✅ Knowledge graph answers
- ✅ Weather (when configured)

### Research
- ✅ Multi-source deep research: search → fetch pages → LLM summarize → synthesize with citations
- ✅ Sources returned with numbered citations

### Image Generation
- ✅ Text-to-image via SeaArt API
- ✅ Multiple styles: realistic, anime, fantasy, cyberpunk, watercolor, oil painting
- ✅ Progress polling with real-time feedback
- ✅ Images saved locally and displayed in frontend

### Coding
- ✅ Code writing in any language
- ✅ Bug fixing and debugging
- ✅ Code explanation
- ✅ Code optimization/refactoring
- ✅ Python code execution (local only, disabled on Render)

### Android Device Control
- ✅ Open 80+ apps by name (YouTube, WhatsApp, Chrome, etc.)
- ✅ Flashlight on/off
- ✅ WiFi toggle
- ✅ Volume up/down
- ✅ Battery status check
- ✅ Camera open
- ✅ Alarm setting
- ✅ Phone calls
- ✅ App launching via package names
- ✅ Settings panels

### Reflection
- ✅ Session summaries (LLM-generated from transcript)
- ✅ Daily reviews (LLM-generated from 24h activity)
- ✅ Regex-based fact extraction from sessions (no LLM hallucination)

### Proactive Intelligence
- ✅ Time-aware greetings (morning/afternoon/evening/night)
- ✅ Contextual suggestions (mood-based, focus tips, health tips, motivation)
- ✅ Productivity streak tracking
- ✅ Quick action chips for Android UI
- ✅ 30-min cooldown between auto-suggestions

### Timer
- ✅ Server-side countdown timers
- ✅ Alert polling (frontend polls every 1s)
- ✅ Multiple concurrent timers
- ✅ Auto-cleanup after 1h
- ✅ Cancel any timer

### TTS (Text-to-Speech)
- ✅ Server-side Microsoft Edge TTS (neural voices)
- ✅ Indian English (en-IN-NeerjaNeural) and Hindi (hi-IN-SwaraNeural)
- ✅ Auto-language detection (Devanagari → Hindi)
- ✅ Configurable rate and pitch
- ✅ Returns MP3 audio stream

### Admin Panel
- ✅ Password-protected admin (code10 / codeten)
- ✅ File browser (read/edit any file in project)
- ✅ Data viewer (chat history, user facts)
- ✅ Image gallery (generated images)
- ✅ Activity log viewer
- ✅ Data clearing

### Android Client
- ✅ Native Android app with floating overlay
- ✅ Speech recognition (Hinglish)
- ✅ TTS with Hindi/English support
- ✅ Accessibility service for system actions
- ✅ Digital Assistant integration (long-press Power → JARVIS)
- ✅ Permission wizard on first run
- ✅ Waveform audio visualization

---

## What It CANNOT Do

- ❌ No LLM-inferred facts stored as memory (Constitution V3, Rule 6)
- ❌ No code execution on Render (cloud security restriction)
- ❌ No persistent timers (in-memory only, lost on restart)
- ❌ No direct hardware access from cloud (battery, torch, volume via Termux only)
- ❌ No vector/embedding search (disabled by default, requires config)
- ❌ No email sending (no SMTP config)
- ❌ No file downloads/uploads (admin read/write only with auth)
- ❌ No multi-user support (single user, no auth/login system)
- ❌ No streaming response (request-response only; streaming endpoint defined but separate)
- ❌ No push notifications (poll-based timer alerts only)
- ❌ No file attachments in chat
- ❌ No webhook integration
- ❌ No offline mode (requires internet for LLM + Supabase)
- ❌ No model fine-tuning (uses fixed Groq/Opencode models)
- ❌ No end-to-end encryption
- ❌ No speech-to-text on server (all STT on Android/browser side)

---

## How It Works — Processing Pipeline

### Full Request Flow

```
User: "Hey JARVIS, kal 5 baje meeting yaad dilana"
                                    │
┌───────────────────────────────────▼──────────────────────────────┐
│  1. Flask receives POST /api/chat  {message: "..."}             │
│     RateLimiter checks IP (30/60s)                               │
│     X-Request-ID generated                                        │
└───────────────────────────────────┬──────────────────────────────┘
                                    │
┌───────────────────────────────────▼──────────────────────────────┐
│  2. Orchestrator.run(query)                                      │
│     │                                                            │
│     ├── 2a. UnderstandingEngine.analyze()                         │
│     │     ├── detect_intent: "reminder" (by regex)               │
│     │     ├── detect_emotion: "neutral", intensity: 3            │
│     │     ├── extract_entities: {}                               │
│     │     ├── detect_topic: "general"                            │
│     │     └── detect_expertise: "intermediate"                   │
│     │                                                            │
│     ├── 2b. Check is_memory_store/recall (no → continue)         │
│     │                                                            │
│     ├── 2c. Parallel Supabase fetch (ThreadPoolExecutor x3)      │
│     │     ├── build_memory_context() (4 sub-threads)              │
│     │     │   ├── get_user_profile()                             │
│     │     │   ├── get_emotional_context()                        │
│     │     │   ├── get_recent_episodes(5)                         │
│     │     │   └── get_relevant_episodes(topic, 3)                │
│     │     ├── GoalTracker.build_goal_context() (cached 60s)      │
│     │     └── EventSystem.build_event_context() (cached 60s)     │
│     │                                                            │
│     ├── 2d. Truth Engine: verify_before_llm()                    │
│     │     └── Check has_relevant_memory()                        │
│     │         ├── user_profile has data?                         │
│     │         ├── recent_episodes have user content?             │
│     │         └── relevant_past has user content?                │
│     │         → has_truth=True (user just spoke)                  │
│     │                                                            │
│     ├── 2e. ContextBuilder.build()                               │
│     │     ├── Personality prompt (Hinglish, truth-first)          │
│     │     ├── User profile sections                              │
│     │     ├── Emotional context                                  │
│     │     ├── Recent conversation (last 5 episodes)              │
│     │     ├── Relevant past context                              │
│     │     ├── Current analysis (emotion, intent, topic)          │
│     │     ├── Extra context (goals + events brief)               │
│     │     └── Truth-footer: "Sirf context use karo"              │
│     │                                                            │
│     └── 2f. IntentRouter.route(query)                            │
│           └── Keyword match: "remind" → "reminder"               │
│                                │                                 │
┌───────────────────────────────▼──────────────────────────────────┐
│  3. _handle_reminder()                                           │
│     ├── events_sys.parse_event_from_text(query)                  │
│     │     ├── Regex: "kal" → tomorrow + "5" + "baje" → 5:00     │
│     │     ├── Title extraction: strip keywords                   │
│     │     └── Returns {title: "meeting", event_time: ISO}        │
│     ├── events_sys.add_event(title, event_time)                  │
│     │     └── INSERT INTO events (Supabase)                      │
│     └── Returns response string                                  │
│                                 │                                │
┌───────────────────────────────▼──────────────────────────────────┐
│  4. Post-Process (background thread, daemon)                     │
│     ├── add_episode(user, query, topic, emotion)                 │
│     └── record_emotion(topic, emotion, intensity)                │
│                                 │                                │
┌───────────────────────────────▼──────────────────────────────────┐
│  5. Flask returns JSON:                                          │
│     {                                                            │
│       "reply": "🔔 Reminder set! meeting - tomorrow 5:00",       │
│       "agent": "reminder",                                       │
│       "brain": {intent, emotion, topic, session_id},             │
│       "time_ms": 847                                             │
│     }                                                            │
└──────────────────────────────────────────────────────────────────┘
```

### LLM Call Flow

```
ask_llm(messages, model, system, context)
    │
    ├── Build payload_messages: [system/context, ...messages]
    │
    ├── ✅ Step 1: Try Groq
    │     POST https://api.groq.com/openai/v1/chat/completions
    │     Model: llama-3.3-70b-versatile
    │     Timeout: 12s
    │     Success? → return response
    │
    └── ❌ Step 2: Fallback to Opencode Zen
          GET https://opencode.ai/zen/v1/models (list available)
          POST https://opencode.ai/zen/v1/chat/completions
          Model: deepseek-v4-flash-free (or best available)
          Timeout: 20s
          Success? → return response
    
    └── ❌ Both failed → return error string
```

---

## Algorithms & Methods Used

### 1. Rate Limiting — Sliding Window
**File**: `app/main.py:26-49`
- Per-IP bucket of timestamps
- Prune entries older than window (60s)
- Count remaining: if ≥ limit (30), deny
- O(1) amortized cleanup

### 2. Intent Detection — Regex Priority Matching
**File**: `app/understanding.py:244-267`
- 9 intent categories, each with 3-8 regex patterns
- Priority order: memory_store → memory_recall → emotional → greeting → farewell → creative → command → question → casual
- First match wins

### 3. Emotion Detection — Keyword + Intensity Scoring
**File**: `app/understanding.py:269-326`
- 6 emotion categories (happy/sad/angry/confused/excited/anxious) + neutral
- Each category has 6-10 keywords/emoji patterns
- Intensity (1-5):
  - Default: 3
  - Amplifiers ("bahut", "very", "extremely"): → 5
  - Diminishers ("thoda", "little", "slightly"): → 2
  - Exclamation marks (≥3): +1
  - ALL CAPS ratio (>60%): +1

### 4. Entity Extraction — Regex Named Groups
**File**: `app/understanding.py:328-376`
- 7 entity types: name, age, location, profession, project, preference
- Each type has 4-7 regex patterns (English + Hinglish)
- First match per entity type wins
- Special handling: "favorite X is Y" (two groups), hate/dislike prefixing

### 5. Expertise Estimation — Jargon Detection
**File**: `app/understanding.py:400-439`
1. Check stored profile → return if exists
2. Check for expert jargon (17 terms: docker, kubernetes, graphql, etc.) → "expert"
3. Check for beginner patterns ("kya hota hai", "what is", "explain basics") → "beginner"
4. Check for basic terms (website, app, code) → "intermediate"
5. Default: "intermediate"

### 6. LLM Intent Classification — Prompt Engineering
**File**: `app/intent_router.py:87-145`
- Sends structured prompt to LLM with 14 intent descriptions and JSON format examples
- Temperature: 0.1 (low randomness)
- Falls back to keyword matching if LLM fails/parses invalid JSON
- Result cached by MD5 hash for 60s

### 7. Truth-First Verification — Pre-LLM Gate
**File**: `app/truth_engine.py:106-199`
1. Check if memory context has any user content in:
   - user_profile (any non-empty value)
   - recent_episodes (role=user, non-empty content)
   - relevant_past (role=user, non-empty content)
2. If no content found: return variant Hinglish "Mujhe nahi pata" response
3. If content exists: allow LLM call

### 8. Memory Context — Parallel Supabase Queries
**File**: `app/memory.py:623-654`
- Uses `ThreadPoolExecutor(max_workers=4)` to fire:
  1. `get_user_profile()` — all semantic memory
  2. `get_emotional_context()` — latest 20 unique topic emotions
  3. `get_recent_episodes(limit)` — last N episodes
  4. `get_relevant_episodes(topic, 3)` — topic-matched past episodes
- All queries run concurrently, results collected via `.result()`

### 9. Session Management — Timeout + Lazy Creation
**File**: `app/memory.py:262-314`
- Find most recent open session (ended_at IS NULL)
- Check last activity timestamp
- If > 30 min since last episode → close session, create new one
- If session has no episodes yet → check started_at instead

### 10. Goal Router — Hinglish Keyword Parsing
**File**: `app/orchestrator.py:333-375`
- "complete/done/khatam/finish" → `complete_goal(goal_id)`
- "list/show/kya hain/batao/dikhaao" → `get_active_goals()` + format
- Default → regex-strip action words, extract title, set priority (urgent→high)

### 11. Event Time Parsing — Natural Language
**File**: `app/events.py:145-186`
- "30 min mein" / "2 ghante baad" → relative timedelta
- "kal 5 baje" → tomorrow + hour
- "aaj 3 pm" → today + hour
- Title = strip all time/reminder keywords from original text

### 12. YouTube Search — No API Key
**File**: `app/skills/youtube.py:77-100`
- Uses `youtube-search-python` library (scrapes YouTube HTML)
- `VideosSearch(query, limit)` → `result()` → first result
- Returns title, URL, channel, duration, thumbnail

### 13. Image Generation — SeaArt API Polling
**File**: `app/skills/img.py:39-228`
1. Auth: POST to SeaArt login → get token
2. Submit: POST text-to-img with enhanced prompt + style
3. Poll: GET progress every 2s (max 60s), update progress bar
4. Download: GET image URL → save to `static/generated_images/`
5. Return: filepath + image URL

### 14. Knowledge Graph — Weighted Triples
**File**: `app/knowledge_graph.py:27-106`
- Entity → relationship → target triples with weight
- Upsert: find → bump weight + access_count + last_seen OR insert new
- Query: outgoing + incoming edges, weight DESC
- Search: ILIKE on all three columns

### 15. Proactive Suggestion — Time + Mood + Cooldown
**File**: `app/proactive.py:108-131`
- Cooldown: 1800s (30 min) between auto-suggestions
- Mood routing: sad/anxious/angry → motivation + health tips
- Topic routing: coding/work → focus tips
- Time routing: morning → morning tips, evening → evening tips
- Default: health + motivation mix

### 16. Rate Limiter — Sliding Window
**File**: `app/main.py:26-49`
- `dict[str, list[float]]` per IP timestamp bucket
- Prune entries older than `window_sec` (60s)
- Count ≤ `limit` (30) → allow, else → 429

### 17. TTS — Async Edge TTS Wrapper
**File**: `app/api/routes.py:419-498`
- Runs `edge_tts.Communicate` asynchronously
- Collects all audio chunks in `io.BytesIO`
- Auto-detects Hindi (Devanagari Unicode range) vs English
- Returns complete MP3 as Response
- Falls back to synchronous executor if no event loop

### 18. Android Command Parser — Keyword Regex
**File**: `app/skills/tasks.py:154-308`
- Priority-ordered keyword checks: torch → wifi → battery → volume → brightness → bluetooth → camera → open_app → alarm → call
- Each has regex parameter extraction
- Termux direct execution if available
- Returns `{reply, action, payload}` for frontend

---

## API Endpoints Complete Reference

| Method | Endpoint | Body/Params | Returns |
|--------|----------|------------|---------|
| POST | `/api/chat` | `{message: str}` | `{reply, agent, time_ms, image_url, youtube_url, brain, intent}` |
| GET | `/api/agents` | — | Agent list with descriptions |
| GET | `/api/history` | — | 20 recent `{role, content}` |
| GET | `/api/memory/facts` | — | `{key: value}` dict |
| POST | `/api/memory/learn` | `{key, value, fact_type?}` | `{status, key}` |
| DELETE | `/api/memory/fact` | `{key}` | `{status, key}` |
| GET | `/api/memory/search` | `?q=keyword` | `{key: value}` matches |
| GET | `/api/memory/recall` | `?q=query&limit=8` | Full recall response |
| GET | `/api/memory/cache/stats` | — | Cache metrics |
| GET | `/api/memory/episodes/search` | `?q=keyword&limit=10` | Matching episodes |
| GET | `/api/memory/sessions` | `?limit=5` | Session summaries |
| GET | `/api/brain/profile` | — | User profile from semantic memory |
| GET | `/api/brain/emotions` | — | Emotional context |
| GET | `/api/brain/sessions` | — | Current session info |
| GET | `/api/goals` | `?status=active` | Goals array |
| POST | `/api/goals` | `{title, description?, priority?, deadline?}` | Created goal |
| PATCH | `/api/goals/<id>` | `{status: done\|active\|paused}` | Status |
| DELETE | `/api/goals/<id>` | — | Status |
| GET | `/api/events` | `?hours=48` | Events + due array |
| POST | `/api/events` | `{title, event_time?, notes?, repeat?}` | Created event |
| PATCH | `/api/events/<id>/done` | — | Status |
| GET | `/api/reflect` | `?type=daily\|session` | Summary text |
| GET | `/api/proactive/briefing` | — | Greeting, time, suggestion, streak, actions |
| GET | `/api/proactive/suggestion` | `?emotion=&topic=` | Single suggestion |
| POST | `/api/tts` | `{text, voice?, rate?, pitch?}` | `audio/mpeg` binary |
| GET | `/api/tts/voices` | — | Available Indian voices |
| POST | `/api/timer` | `{duration: int, label?}` | Timer info |
| GET | `/api/timer/alerts` | — | Expired timers |
| GET | `/api/timer/<id>` | — | Timer status |
| DELETE | `/api/timer/<id>` | — | Cancelled status |
| GET | `/health` | — | `{status: ok}` |
| GET | `/api/admin/panel` | — | Admin HTML page |
| POST | `/api/admin/auth` | `{password}` | Auth status |
| POST | `/api/admin/logout` | — | Logout status |
| GET | `/api/admin/check` | — | `{authenticated: bool}` |
| GET | `/api/admin/files` | `?path=.` | File listing |
| GET | `/api/admin/file` | `?path=` | File content |
| PUT | `/api/admin/file` | `{path, content}` | Save status |
| GET | `/api/admin/data` | — | Chat + facts + system info |
| POST | `/api/admin/data/clear` | `{target: chat\|facts\|all}` | Clear status |
| GET | `/api/admin/images` | — | Generated images list |
| GET | `/api/admin/activities` | — | Activity log files |
| GET | `/api/admin/activity` | `?date=YYYY-MM-DD` | Activity content |
| PUT | `/api/admin/activity` | `{date, content}` | Save status |

---

## Database Schema

**Supabase (PostgreSQL)** — 9 tables (see `app/core/supabase_schema.sql`):

### `chat_history`
| Column | Type | Description |
|--------|------|-------------|
| id | BIGSERIAL PK | Auto-increment |
| created_at | TIMESTAMPTZ | Default now() |
| role | TEXT | 'user' or 'assistant' |
| content | TEXT | Message body |
| source | TEXT | user_input, llm_response, system |
| confidence | FLOAT | Per Rule 5 map |
| verified | BOOLEAN | Passed truth gate |

### `user_facts`
| Column | Type | Description |
|--------|------|-------------|
| fact_key | TEXT PK | Unique key |
| fact_value | TEXT | Value |
| fact_type | TEXT | personal, preference, etc. |
| priority | INT | Display order |
| created_at | TIMESTAMPTZ | |
| last_updated | TIMESTAMPTZ | |
| source | TEXT | Origin tracking |
| confidence | FLOAT | Per Rule 5 |
| verified | BOOLEAN | |

### `conversation_sessions`
| Column | Type | Description |
|--------|------|-------------|
| id | BIGSERIAL PK | |
| started_at | TIMESTAMPTZ | |
| ended_at | TIMESTAMPTZ | Null if active |
| summary | TEXT | Session summary from reflection |
| dominant_emotion | TEXT | |

### `episodic_memory`
| Column | Type | Description |
|--------|------|-------------|
| id | BIGSERIAL PK | |
| session_id | BIGINT FK → sessions | |
| created_at | TIMESTAMPTZ | |
| role | TEXT | |
| content | TEXT | |
| topic | TEXT | Detected topic |
| emotion | TEXT | Detected emotion |
| importance | INT | 1-5 |
| source | TEXT | |
| confidence | FLOAT | |
| verified | BOOLEAN | |

### `semantic_memory`
| Column | Type | Description |
|--------|------|-------------|
| category | TEXT | identity, location, preference, etc. |
| fact_key | TEXT | |
| fact_value | TEXT | |
| created_at | TIMESTAMPTZ | |
| last_confirmed | TIMESTAMPTZ | User confirmation timestamp |
| confidence | FLOAT | |
| source | TEXT | |
| verified | BOOLEAN | |
| PK | (category, fact_key) | Composite |

### `emotional_memory`
| Column | Type |
|--------|------|
| id | BIGSERIAL PK |
| topic | TEXT |
| emotion | TEXT |
| intensity | INT (1-5) |
| episode_id | BIGINT (nullable) |
| context | TEXT (nullable) |
| created_at | TIMESTAMPTZ |
| source | TEXT |
| confidence | FLOAT |

### `goals`
| Column | Type |
|--------|------|
| id | BIGSERIAL PK |
| title | TEXT |
| description | TEXT |
| priority | TEXT (high/medium/low) |
| status | TEXT (active/done/paused/cancelled) |
| deadline | TIMESTAMPTZ (nullable) |
| project_id | BIGINT FK → projects |
| created_at | TIMESTAMPTZ |
| completed_at | TIMESTAMPTZ (nullable) |

### `projects`
| Column | Type |
|--------|------|
| id | BIGSERIAL PK |
| name | TEXT |
| description | TEXT |
| status | TEXT |
| created_at | TIMESTAMPTZ |

### `events`
| Column | Type |
|--------|------|
| id | BIGSERIAL PK |
| title | TEXT |
| event_time | TIMESTAMPTZ (nullable) |
| notes | TEXT |
| repeat | TEXT (none/daily/weekly) |
| done | BOOLEAN |
| created_at | TIMESTAMPTZ |

### `knowledge_graph`
| Column | Type |
|--------|------|
| id | BIGSERIAL PK |
| source_entity | TEXT |
| relationship | TEXT |
| target_entity | TEXT |
| weight | FLOAT |
| source_type | TEXT |
| target_type | TEXT |
| metadata | JSONB |
| access_count | INT |
| last_seen | TIMESTAMPTZ |
| created_at | TIMESTAMPTZ |

### `working_memory`
| Column | Type |
|--------|------|
| id | BIGSERIAL PK |
| session_id | BIGINT |
| focus | TEXT |
| current_task | TEXT |
| state | TEXT |
| metadata | JSONB |
| created_at | TIMESTAMPTZ |
| updated_at | TIMESTAMPTZ |

---

## Dependencies

### Python (requirements.txt — 12 packages)
```
flask~=3.1.0           # Web framework
gunicorn~=23.0.0       # Production WSGI server
requests~=2.32.0       # HTTP client
openai~=1.82.0         # OpenAI-compatible API (Groq client)
edge-tts~=7.0          # Microsoft Edge TTS (neural voices)
supabase~=2.0          # Supabase PostgreSQL client
youtube-search-python~=1.6.6  # YouTube search (no API key)
beautifulsoup4~=4.13.0 # HTML parsing
lxml~=5.3.0            # XML/HTML parser (for BeautifulSoup)
Pillow~=11.2.0         # Image handling
numpy~=2.2.0           # Numerical ops
python-dotenv~=1.0.0   # .env file loading
pytest~=9.1.0          # Testing
```

### Android (Kotlin/Gradle)
- AGP 8.2.2, Kotlin 1.9.22
- compileSdk 35, minSdk 26, targetSdk 35
- OkHttp (HTTP client — bundled via JarvisBackendClient)

### System
- Python 3.11+
- Docker / Docker Compose (for container deployment)
- Render.com (free tier, Oregon)
- Gradle 8.x (for Android builds)

---

## Android Client Architecture

### Service Architecture

```
System Digital Assistant Trigger
    │ (long-press Power / gesture)
    ▼
JarvisVoiceInteractionService
    │  onCreate()
    ▼
JarvisSessionService (Foreground Service)
    │  Inflates overlay UI
    ▼
OverlayViewController (State Machine)
    │  IDLE → LISTENING → PROCESSING → SPEAKING
    │
    ├── SpeechRecognizer (Hinglish STT)
    ├── JarvisBackendClient (OkHttp → Flask /api/chat)
    ├── JarvisTts (Android TTS hi-IN/en-IN)
    └── JarvisAccessibilityService (system actions)
```

### Action Whitelist (Safety)
**Safe (always allowed)**: torch, volume, alarm, open/close app, home, back, browser, search, camera, settings panels, screenshot, notifications, vibrate

**Dangerous (blocked unless confirmed)**: call, create_file, read_file, delete_file

### App Launching Flow
1. Receive app name from backend
2. Search installed packages via `PackageManager`
3. If not installed: search in `APP_MAP` → Play Store fallback
4. Launch via `startActivity(intent)`

---

## Key Design Principles

1. **Truth-First (Constitution V3)**: Never hallucinate. If no verified memory exists, say "Mujhe nahi pata". Every stored fact has source + confidence, never from LLM inference.

2. **Confidence Map**: Fact trustworthiness is determined by source type, not content. `user_input` (1.0) > `observed` (0.7) > `regex_extraction` (0.3) > `llm_inference` (0.0 → never stored).

3. **No LLM Command Parsing**: All Android device commands parsed via keyword/regex — zero LLM calls for actions. This prevents the AI from inventing commands.

4. **Supabase First**: All persistent storage through Supabase (PostgreSQL). In-memory dict fallback for testing only.

5. **Provider Redundancy**: Groq llama-3.3-70b (fast) → Opencode deepseek-v4-flash-free (fallback). 12s timeout on primary before fallback.

6. **Android as Frontend**: Native Android app handles voice I/O and device control; all AI processing is server-side. The Android app never calls an LLM directly.

7. **Hinglish Support**: Natural language understanding for Hindi-English mixed input across all modules (intent, emotion, entities, topics, time parsing).

8. **Server-side TTS**: Microsoft Edge TTS neural voices via Flask API — no browser Speech Synthesis dependency, works on all clients.

9. **Two-Layer Intent Routing**: LLM-powered classifier (detailed, 14 intents) with keyword fallback (fast, 10 intents). Cache for performance.

10. **Async Post-Processing**: Episodes and emotions saved in background thread — never blocks response delivery.
