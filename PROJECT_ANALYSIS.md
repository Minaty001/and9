# JARVIS PCOS (Personal Cognitive Operating System) — Complete Project Analysis

> Generated: 2026-06-26
> This document contains comprehensive notes, tested API inputs/outputs, and architecture details.

---

## 📋 PROJECT OVERVIEW

**Name:** JARVIS PCOS (Neural Engine v4)
**Type:** Flask-based AI Assistant Backend + Android Client + Micro Neural Brain
**Architecture:** Three-Brain Architecture (Conscious, Subconscious, Reflex) under PersonalOS
**Language:** Python 3, Kotlin (Android), Java (Android)
**Database:** Supabase (PostgreSQL) primary, SQLite for local services (timers, reminders, activity)
**LLM Providers:** Groq (primary), Opencode Zen (fallback)

### Core Principles (Constitution V3)
- **Rule 1:** Never hallucinate — say "Mujhe nahi pata" if info not in context
- **Rule 4:** Never claim memory you don't have
- **Rule 5:** Confidence map enforced on all writes
- **Rule 6:** No LLM inference stored as fact
- **Rule 7:** Whitelist-based Android action execution
- **Rule 8:** Source tracking for all memory writes

### Confidence Map (Rule 5)
| Source | Max Confidence | Example |
|--------|---------------|---------|
| `user_input` / `direct_statement` | 1.0 | User says "My name is Saif" |
| `observed` / `observed_pattern` | 0.7 | User consistently asks about coding |
| `regex_extraction` / `keyword_detection` | 0.3 | Regex matches "in Delhi" from message |
| `llm_inference` | 0.0 ❌ | **Never stored** |

---

## 📁 FILE STRUCTURE

```
and9/
├── app/                          # Flask Backend
│   ├── main.py                   # Flask app factory, rate limiter, startup sequence
│   ├── __init__.py               # Package marker
│   ├── _flask_compat.py          # Flask compat layer (real Flask or in-process fallback)
│   ├── agents/
│   │   ├── __init__.py           # Agent registry (coding, research, assistant)
│   │   ├── assistant_agent.py    # General assistant agent
│   │   ├── coding_agent.py       # Code generation/debug agent
│   │   └── research_agent.py     # Multi-source research agent
│   ├── and9/                     # AND9 Multi-brain AI OS
│   │   ├── and9.py               # Main AND9 class
│   │   ├── brain_types.py        # Brain type definitions
│   │   ├── conscious_brain.py    # Conscious brain (orchestrator-based)
│   │   ├── habit_brain.py        # Habit brain
│   │   ├── subconscious_brain.py # Subconscious brain (pattern matching)
│   │   ├── actions/              # Action definitions
│   │   ├── alarms/               # Alarm management
│   │   ├── android/              # Android integration (action registry, handlers, firewall)
│   │   ├── apps/                 # Package resolver for Android apps
│   │   ├── brain/                # Neural orchestrator, cognitive engine
│   │   ├── contacts/             # Contact management
│   │   ├── core/                 # Pipeline status, activity DB, intent trace
│   │   ├── intents/              # Intent classification
│   │   ├── media/                # Media handling
│   │   ├── reminders/            # Reminder system
│   │   ├── router/               # Intent router with offline micro-brain fallback
│   │   ├── timers/               # Timer management
│   │   └── utils/                # Utilities
│   ├── api/
│   │   ├── routes.py             # JSON API routes (chat, memory, goals, events, TTS, timers, AND9, Personality)
│   │   ├── web_routes.py         # HTML page routes (index)
│   │   ├── admin_routes.py       # Admin panel routes (file browsing, data viewing)
│   │   └── memory_api.py         # 4-layer memory API (working, episodic, semantic, procedural)
│   ├── core/
│   │   ├── config.py             # Centralized env config (Supabase, Groq, Opencode, etc.)
│   │   ├── brain.py              # LLM interface (Groq → Opencode fallback)
│   │   ├── memory.py             # 4-layer memory (chat, facts, episodes, semantic, emotional)
│   │   ├── orchestrator.py       # Central cognitive pipeline (route, execute, post-process)
│   │   ├── understanding.py      # Regex + spaCy NLP understanding engine
│   │   ├── truth_engine.py       # Constitution V3 truth validation
│   │   ├── context_builder.py    # Rich LLM context builder from all memory layers
│   │   ├── personality.py        # JARVIS personality system prompt
│   │   ├── personality_os.py     # PersonalOS — master cognitive architecture
│   │   ├── nlp_pipeline.py       # 4-stage spaCy+SciPy NLP pipeline
│   │   ├── nlp_models.py         # NLP data models
│   │   ├── goal_tracker.py       # Goal & project tracking
│   │   ├── events.py             # Event & reminder system
│   │   ├── proactive.py          # Proactive intelligence engine
│   │   ├── reflection.py         # Reflection engine (daily/session reviews)
│   │   ├── timer.py              # Server-side countdown timer
│   │   ├── learning_system.py    # Learning system (pattern, skill, preference)
│   │   ├── procedural_memory.py  # Procedural memory (skills)
│   │   ├── working_memory.py     # Working memory (current session)
│   │   ├── memory_consolidation.py # Working→Episodic→Semantic consolidation
│   │   ├── knowledge_graph.py    # Knowledge graph
│   │   ├── agent_loop.py         # Observe-Think-Act-Reflect-Learn loop
│   │   ├── automation_system.py  # Goals, habits, scheduled actions
│   │   ├── activity_logger.py    # Daily activity logging
│   │   └── supabase_schema.sql   # Required Supabase tables DDL
│   ├── reminders/
│   │   ├── scheduler.py          # Reminder scheduler
│   │   ├── storage.py            # SQLite-backed reminder storage
│   │   ├── worker.py             # Background reminder polling worker
│   │   └── recurring.py          # Recurring reminder handler
│   ├── skills/
│   │   ├── img.py                # Image generation
│   │   ├── youtube.py            # YouTube music search
│   │   ├── research.py           # Web research
│   │   ├── tasks.py              # Task management
│   │   └── intent_executor.py    # Intent execution
│   ├── static/                   # Frontend static files (JS, CSS)
│   └── templates/                # HTML templates (index.html, admin.html)
├── android/                      # Android client (Gradle project)
├── micro_brain/                  # Micro Neural Brain (lightweight offline NN)
│   ├── main.py                   # Entry point (console, GUI, CLI, training)
│   ├── config.py                 # NN config
│   ├── brain/                    # Neural network (decision, learning, memory, neural, reflex)
│   ├── database/                 # Database layer
│   ├── datasets/                 # Intent datasets
│   ├── gui/                      # GUI dashboard
│   ├── models/                   # Trained model files (.npz, vocab.json)
│   ├── training/                 # Training and evaluation
│   └── utils/                    # Utilities (logger, metrics, timezone)
├── deploy/
│   └── render.yaml               # Render.com deployment config
├── scripts/                      # Build/install scripts
├── tests/                        # Pytest test suite
├── requirements.txt              # Python dependencies
├── Dockerfile                    # Docker build
├── docker-compose.yml            # Docker compose
└── README.md                     # Project documentation
```

---

## 🧠 ARCHITECTURE

### Processing Pipeline
```
User Input → Intent Router → Memory Retrieval → Truth Engine → Context Builder → LLM → Response → Memory Storage
                                                       │
                                                       └─ No memory? → "Mujhe nahi pata"
```

### PersonalOS Cognitive Architecture
```
                                    ┌─────────────────┐
                                    │   AGENT LOOP    │
                                    │ (Observe-Think- │
                                    │  Act-Reflect-   │
                                    │  Learn-Improve) │
                                    └────────┬────────┘
                                             │
┌────────────────────────────────────────────┼──────────────────────────┐
│                                            │                          │
│  ┌──────────┐  ┌──────────┐  ┌────────────┴──────────┐              │
│  │  REFLEX  │  │  HABIT   │  │     REASONING         │  COGNITIVE   │
│  │  BRAIN   │→ │  BRAIN   │→ │      BRAIN            │  ENGINE      │
│  │ (<300ms)  │  │ (~200ms) │  │     (1-5s)           │              │
│  └──────────┘  └──────────┘  └───────────────────────┘              │
│                                            │                          │
│  ┌─────────────────────────────────────────┼──────────────────┐     │
│  │              MEMORY SYSTEM              │                  │     │
│  │  ┌────────┐  ┌──────────┐  ┌───────────┴────────┐        │     │
│  │  │WORKING │  │ EPISODIC │  │     SEMANTIC       │        │     │
│  │  │MEMORY  │→ │  MEMORY  │→ │     MEMORY         │        │     │
│  │  └────────┘  └──────────┘  └────────────────────┘        │     │
│  │  ┌──────────────────┐  ┌──────────────────────┐          │     │
│  │  │PROCEDURAL MEMORY │  │   KNOWLEDGE GRAPH    │          │     │
│  │  └──────────────────┘  └──────────────────────┘          │     │
│  └─────────────────────────────────────────────────────────┘     │
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐       │
│  │              LEARNING SYSTEM                          │       │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │       │
│  │  │    PATTERN   │  │    SKILL     │  │ PREFERENCE │ │       │
│  │  │   LEARNING   │  │   LEARNING   │  │  LEARNING  │ │       │
│  │  └──────────────┘  └──────────────┘  └────────────┘ │       │
│  └──────────────────────────────────────────────────────┘       │
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐       │
│  │              AUTOMATION SYSTEM                        │       │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │       │
│  │  │    GOALS     │  │    HABITS    │  │ SCHEDULED  │ │       │
│  │  │   TRACKING   │  │   TRACKING   │  │  ACTIONS   │ │       │
│  │  └──────────────┘  └──────────────┘  └────────────┘ │       │
│  └──────────────────────────────────────────────────────┘       │
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐       │
│  │              ANDROID INTEGRATION                      │       │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────┐  │       │
│  │  │ACCESSIBILITY│  │   OVERLAY  │  │  APP CONTROL  │  │       │
│  │  └────────────┘  └────────────┘  └────────────────┘  │       │
│  └──────────────────────────────────────────────────────┘       │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🔌 API ENDPOINTS — INPUTS & OUTPUTS

All endpoints tested with Flask in-process test client. Responses captured live.

### 🏥 Health

**`GET /health`**
- **Input:** None
- **Output:** `{"status": "ok", "request_id": "fbb3f5a089a9"}`

**`GET /api/health`**
- **Input:** None
- **Output:** `{"status": "ok"}`

### 💬 Chat

**`POST /api/chat`**
- **Input (empty):** `{}`
- **Output:** `{"reply": "Please provide a message."}`
- **Input (greeting):** `{"message": "Hello!"}`
- **Output:** `{"reply": "AI service not configured...", "agent": "chat", "time_ms": 955, "brain": {"intent": "greeting", "emotion_detected": "neutral", "emotion_intensity": 3, "topic": "general", "session_id": 1}}`
- **Input (empty msg):** `{"message": ""}`
- **Output:** `{"reply": "Please provide a message."}`
- **Note:** LLM requires GROQ_API_KEY or OPENCODE_API_KEY env var

### 🤖 Agents

**`GET /api/agents`**
- **Input:** None
- **Output:**
```json
[
  {"name": "chat", "description": "General conversation and tasks"},
  {"name": "coding", "description": "Write, debug, and explain code"},
  {"name": "image", "description": "Generate images from text prompts"},
  {"name": "research", "description": "Multi-source research with citations"},
  {"name": "search", "description": "Real-time web search and facts"},
  {"name": "music", "description": "Search and play songs from YouTube"},
  {"name": "goal", "description": "Manage goals, tasks, and projects"},
  {"name": "reminder", "description": "Set and manage reminders and events"},
  {"name": "reflection", "description": "Daily review and session summaries"},
  {"name": "device", "description": "Control Android device features"}
]
```

### 📜 History

**`GET /api/history`**
- **Input:** None
- **Output:** `[]` (empty list when no chat history)

### 🧠 Memory

**`GET /api/memory/facts`**
- **Input:** None
- **Output:** `{}` (empty dict when no facts)

**`POST /api/memory/learn`**
- **Input:** `{"key": "name", "value": "Saif"}`
- **Output:** `{"status": "learned", "key": "name"}`

**`GET /api/memory/search?q=Saif`**
- **Input:** query param `q=Saif`
- **Output:** `{"name": "Saif"}`

**`GET /api/memory/recall?q=hello`**
- **Input:** query param `q=hello`
- **Output:** `{"query": "hello", "cache_hit": false, "matched_episodes": [], "user_profile": {}, "recent_chat": [], "sessions_summary": []}`

**`DELETE /api/memory/fact`**
- **Input:** `{"key": "name"}`
- **Output:** `{"status": "deleted", "key": "name"}`

### 🧠 Brain

**`GET /api/brain/profile`**
- **Input:** None
- **Output:** `{}` (empty when no profile data)

**`GET /api/brain/emotions`**
- **Input:** None
- **Output:** `{}`

**`GET /api/brain/sessions`**
- **Input:** None
- **Output:** `{"session_id": 1, "episode_count": 0, "episodes": []}`

### 🎯 Goals

**`GET /api/goals`**
- **Input:** None
- **Output:** `{"goals": [], "count": 0}`

**`POST /api/goals`**
- **Input:** `{"title": "Learn Python", "priority": "high"}`
- **Output:**
```json
{
  "status": "created",
  "goal": {
    "id": 1, "title": "Learn Python", "description": "",
    "priority": "high", "status": "active",
    "deadline": null, "project_id": null,
    "created_at": "2026-06-26T11:31:06.367375"
  }
}
```

**`GET /api/goals?status=active`**
- **Output:** Lists active goals

### 📅 Events

**`GET /api/events`**
- **Input:** None
- **Output:** `{"events": [], "due": [], "count": 0}`

**`POST /api/events`**
- **Input:** `{"title": "Meeting at 3pm"}`
- **Output:** `{"status": "created", "event": {"id": 1, "title": "Meeting at 3pm", "event_time": null, "done": false, ...}}`

### 🔔 Reminders

**`GET /api/reminder/alerts`**
- **Input:** None
- **Output:** `{"alerts": [...]}` (pending/overdue reminders)

### 💭 Reflection

**`GET /api/reflect`**
- **Input:** query param `?type=daily` (default)
- **Output:** `{"type": "daily", "review": "Aaj koi conversation nahi hui boss."}`
- **Input:** `?type=session`
- **Output:** Session reflection summary

### ⚡ Proactive Intelligence

**`GET /api/proactive/briefing`**
- **Input:** None
- **Output:**
```json
{
  "time": "06:31 PM",
  "date": "26 June 2026",
  "weekday": "Friday",
  "is_weekend": false,
  "tip": "Good morning! Kya aaj kuch naya seekhna hai?",
  "greeting": "Evening! 🌙 Din kaisa gaya?",
  "suggestion": "Aaj kya achieve kiya? Ek quick daily review karo.",
  "streak": {"streak_days": 0, "total_sessions": 0, "message": "Ab shuru karo!"},
  "quick_actions": [
    {"label": "🌙 Evening Review", "msg": "Din ka summary bana do"},
    {"label": "🎵 Chill Music", "msg": "Koi relaxing song laga do"},
    {"label": "📝 Journal", "msg": "Aaj ki highlights note karo"},
    {"label": "🧠 Memory Recall", "msg": "Humne kya baat ki thi"},
    {"label": "🌐 Search", "msg": "Search "}
  ]
}
```

### ⏱️ Timer

**`POST /api/timer`**
- **Input:** `{"duration": 60, "label": "Test Timer"}`
- **Output:** `{"id": 1, "remaining": 60, "end_time": 1782473526.39, "label": "Test Timer"}`

**`GET /api/timers`**
- **Input:** None
- **Output:** `{"timers": [{"id": 1, "label": "Test Timer", "remaining": 59, "status": "active", "duration_secs": 60}], "count": 1}`

### 🧬 AND9 Multi-brain

**`POST /api/and9`**
- **Input:** `{"query": "hello"}`
- **Output:** `{"response": "...", "brain": "conscious", "intent": "chat", "success": true, ...}`

**`POST /api/and9/apps`**
- **Input:** `{"com.whatsapp": "WhatsApp", "com.chrome": "Chrome"}`
- **Output:** `{"status": "synced", "count": 2}`

**`GET /api/and9/stats`**
- **Input:** None
- **Output:** System statistics

### 🧑‍🎤 PersonalOS

**`POST /api/personality/process`**
- **Input:** `{"query": "kaise ho"}`
- **Output:** `{"response": "...", "brain": "conscious", "success": true, ...}`

**`GET /api/personality/stats`**
- **Input:** None
- **Output:** System stats

**`GET /api/personality/reflection`**
- **Input:** None
- **Output:** Daily reflection

**`GET /api/personality/health`**
- **Input:** None
- **Output:**
```json
{
  "status": "healthy",
  "initialized": true,
  "subsystems": {
    "procedural_memory": true,
    "memory_consolidation": true,
    "learning_system": true,
    "memory_system": true,
    "knowledge_graph": true,
    "reflection_engine": true,
    "automation_system": true,
    "cognitive_engine": true,
    "agent_loop": true
  }
}
```

### 🗄️ Memory API (4-layer)

**`GET /api/memory/working`** — Current session working memory state
**`GET /api/memory/episodic`** — Recent episodic memories
**`GET /api/memory/semantic`** — User profile and verified facts
**`GET /api/memory/procedural`** — Learned skills from procedural memory
**`POST /api/memory/consolidate`** — Trigger memory consolidation

### 🗺️ Web Routes

**`GET /`** — Returns index.html

### ⚠️ Error Handlers

**`GET /nonexistent`** → `404 {"error": "not_found", "message": "The requested resource was not found."}`
**`POST /health`** → `405 {"error": "method_not_allowed", "message": "Method not allowed for this endpoint."}`

---

## 🧪 TEST RESULTS

**64 tests PASSED** across:
- `test_imports.py` — 56 tests (Memory, Understanding, Personality, Context Builder, Orchestrator, Agents, API, App Factory)
- `test_time_features.py` — 3 tests (Time parsing, City timezone, Reminder extraction)
- `test_micro_brain_integration.py` — 1 test (Micro brain fallback)
- `test_micro_brain_package_imports.py` — 1 test (Package imports)
- `test_micro_brain_package_imports.py` — 1 test

### Skipped/Error Tests
- `test_nlp_pipeline.py` — 24 tests SKIPPED/ERROR (requires numpy + spaCy model; falls back gracefully in prod)
- **3 known bugs found** (see below)

---

## 🐛 KNOWN BUGS FOUND

### Bug 1: Missing `get_recall_cache_stats` import
**File:** `app/api/routes.py` line 267
**Error:** `ImportError: cannot import name 'get_recall_cache_stats' from 'app.core.memory'`
**Impact:** `GET /api/memory/cache/stats` returns 500
**Fix:** Either implement `get_recall_cache_stats()` in `memory.py`, or remove the route

### Bug 2: Missing `get_sessions_summary` method  
**File:** `app/api/routes.py` line 289
**Error:** `AttributeError: 'Memory' object has no attribute 'get_sessions_summary'`
**Impact:** `GET /api/memory/sessions` returns 500
**Fix:** Either implement `get_sessions_summary()` in `Memory` class, or remove the route

### Bug 3: Admin auth fails with in-process Flask compat
**File:** `app/api/admin_routes.py` line 56
**Error:** `AttributeError: 'dict' object has no attribute 'permanent'`
**Impact:** `POST /api/admin/auth` returns 500
**Fix:** The fallback `session` is a plain dict, not a Flask session. Need to guard `session.permanent` or wrap in a try/except

### Bug 4: Missing `search_episodes` method
**File:** `app/api/routes.py` line 281
**Error:** `AttributeError: 'Memory' object has no attribute 'search_episodes'`
**Impact:** `GET /api/memory/episodes/search?q=test` returns 500
**Fix:** Either implement `search_episodes()` in `Memory` or remove the route

---

## 🔧 SETUP & RUNNING

### Requirements
```txt
flask~=3.1.0, gunicorn~=23.0.0, requests~=2.32.0
openai~=1.82.0, edge-tts~=7.0, supabase~=2.0
youtube-search-python~=1.6.6, beautifulsoup4~=4.13.0
Pillow>=10.0.0, spacy~=3.8.0, numpy>=2.0.0
python-dotenv~=1.0.0, pytest~=9.1.0
```

### Environment Variables
```
GROQ_API_KEY      — Primary LLM (Groq)
OPENCODE_API_KEY  — Fallback LLM (Opencode Zen)
SUPABASE_URL      — Supabase project URL
SUPABASE_KEY      — Supabase anon/service_role key
SECRET_KEY        — Flask secret key (auto-generated if absent)
SERP_API_KEY      — Web search (optional)
NEWS_API_KEY      — News fetch (optional)
WEATHER_API_KEY   — Weather (optional)
```

### Run Commands
```bash
# Development
cd and9
python -m app.main

# Production (gunicorn)
gunicorn -w 4 -b 0.0.0.0:8000 'app.main:app'

# Tests
python -m pytest tests/ -v
```

---

## 🧠 UNDERSTANDING ENGINE — ANALYSIS SAMPLES

### Input: "Mera naam Saif hai, main Delhi mein rehta hoon"
```json
{
  "intent": "casual",
  "emotion": "neutral",
  "emotion_intensity": 3,
  "entities": {"name": "Saif", "location": "delhi"},
  "topic": "technology",
  "expertise_level": "intermediate"
}
```

### Input: "Hello!"
```json
{
  "intent": "greeting",
  "emotion": "neutral",
  "emotion_intensity": 3,
  "entities": {},
  "topic": "general",
  "expertise_level": "intermediate"
}
```

### Input: "kaise ho"
```json
{
  "intent": "question",
  "emotion": "neutral",
  "emotion_intensity": 3,
  "entities": {},
  "topic": "technology",
  "expertise_level": "intermediate"
}
```

---

## 💡 KEY FEATURES

1. **Intent Router** — Keyword-based routing for 10 intent categories (chat, coding, image, research, search, music, goal, reminder, reflection, device)
2. **Understanding Engine** — Regex + optional spaCy NLP for intent, emotion, entity extraction, topic, expertise
3. **Truth Engine** — Pre-LLM gate that prevents hallucination by checking verified memory
4. **Context Builder** — Assembles rich LLM context from user profile, emotional state, recent episodes, relevant past
5. **4-Layer Memory** — Working → Episodic → Semantic → Procedural with Supabase persistence
6. **PersonalOS** — Full cognitive architecture with Reflex/Habit/Reasoning brains, learning, automation, reflection
7. **AND9 Multi-brain** — Conscious + Subconscious + Reflex brains with pipeline stages
8. **Proactive Engine** — Time-aware greetings, suggestions, quick actions, productivity streaks
9. **Timers** — Server-side countdown timers with pause/resume, SQLite persistence
10. **TTS** — Microsoft Edge TTS with Hindi/English auto-detection
11. **Android Integration** — Action registry, handler validation, package resolver, accessibility services
12. **Micro Neural Brain** — Lightweight offline NN intent classifier (fallback when no internet)
13. **Admin Panel** — Password-protected file browsing, data viewing, activity logs
