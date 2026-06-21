# 🧠 JARVIS PCOS (Personal Cognitive Operating System) — Definitive Repository

Welcome to the official production repository for **JARVIS PCOS (Neural Engine v4)**. This project contains the high-performance Flask AI orchestrator, dynamic intent execution engines, and local custom Android client wrappers.

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
  │    ├── and9/             ← 🆕 AND9 — Multi-Brain AI Operating System
  │    │    ├── brain_types.py        (BrainType/IntentType enums, BrainResult)
  │    │    ├── normalizer.py         (Hindi → English command normalization)
  │    │    ├── priority_router.py    (20-intent priority-ordered detection)
  │    │    ├── reflex_brain.py       (Instant <100ms reflex dispatcher)
  │    │    ├── reflex_apps.py        (40+ app alias resolution)
  │    │    ├── reflex_device.py      (Flashlight/volume/WiFi/BT handlers)
  │    │    ├── reflex_media.py       (YouTube search/play handlers)
  │    │    ├── reflex_calls.py       (Call/message with contact resolution)
  │    │    ├── reflex_alarm.py       (Alarm/timer/reminder with time parsing)
  │    │    ├── subconscious_brain.py (Pattern learning & habit detection)
  │    │    ├── conscious_brain.py    (LLM reasoning via JARVIS Orchestrator)
  │    │    ├── and9.py              (Main orchestrator — routing pipeline)
  │    │    └── __init__.py          (Public API exports)
  │    ├── agents/           (LLM orchestrators & coding/research agents)
  │    ├── api/              (REST endpoints & socket routers)
  │    ├── core/
  │    │    ├── truth_engine.py      ← 🆕 Truth-First validation gate
  │    │    ├── memory.py            (Supabase memory with source tracking)
  │    │    ├── personality.py       (Truth-First system prompt)
  │    │    ├── orchestrator.py      (Cognitive pipeline with Truth Engine)
  │    │    ├── context_builder.py   (Truth-first context assembly)
  │    │    ├── understanding.py     (Regex-only entity extraction)
  │    │    ├── reflection.py        (No LLM fact extraction)
  │    │    ├── brain.py             (LLM interface, no fact extraction)
  │    │    ├── goal_tracker.py      (Goal management)
  │    │    ├── events.py            (Event/reminder system)
  │    │    └── supabase_schema.sql  (DB schema with source/confidence/verified)
  │    ├── skills/           (command actions — no LLM command parsing)
  │    └── templates/        (control dashboard frontend)
  ├── scripts/               (automated APK patching utilities)
  ├── tests/                 (50+ tests — core modules)
  ├── COMMANDS_REFERENCE.md  (extensive usage command catalog)
  └── AUDIT.md               (system design audit & structural findings)
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

## 🧠 AND9 — Multi-Brain AI Operating System

**AND9** (`app/and9/`) is a cognitive architecture that layers three brains on top of JARVIS v4, inspired by cognitive science:

### Brain Layers

| Brain | Target Latency | Capability | Intent Examples |
|-------|---------------|------------|----------------|
| 🧠 **Reflex** | <100ms | Deterministic, no-LLM actions | App launch, flashligth, call, alarm, timer |
| 🧠 **Subconscious** | ~200ms | Pattern learning, habit detection | Time-of-day suggestions, sequential automation |
| 🧠 **Conscious** | ~1-5s | LLM reasoning, planning, complex tasks | Chat, search, goals, code generation |

### Processing Pipeline

```
User Query → Normalize (Hindi→English) → Priority Router → Route to Brain → Execute → Record Pattern → Response
```

### Key Design Decisions

1. **Priority-Ordered Intent Detection**: 20 intents checked in strict priority order. Emergency (1) > Call (2) > Camera (5) > Flashlight (6) > Bluetooth (7) > WiFi (8) > Volume (10) > Open App (4) > ... > Chat (20). Device-specific intents checked BEFORE generic `open` to prevent misclassification.

2. **Single-Pass Hindi Normalization**: Uses regex alternation (longest-match-first) instead of sequential `str.replace()` to prevent double-replacement (e.g., "home jao" → "go home", not "go go home").

3. **Fully Stateless Reflex Layer**: All reflex handlers are pure functions — parse query, return intent payload. No LLM calls, no state mutations, zero side effects.

4. **Pattern Learning Background**: Subconscious brain records every action (max 1000 entries) and detects time-based patterns (3+ occurrences at same hour) and sequential patterns (2+ occurrences of action follow).

5. **Lazy-Loaded Conscious Brain**: JARVIS Orchestrator is only imported when a Chat/Search/Goal intent is detected — zero overhead for reflex-only interactions.

### API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/and9` | `{"query": "..."}` → Full AND9 processing result |
| `GET` | `/api/and9/stats` | Pattern learning statistics and history |

### Example Usage

```bash
# Reflex: App launch
curl -X POST http://localhost:8000/api/and9 \
  -H "Content-Type: application/json" \
  -d '{"query":"youtube kholo"}'
# → {"response":"Youtube khol raha hoon... 📱","action":"LAUNCH_APP","brain":"reflex","time_ms":3.2,...}

# Reflex: Device control
curl -X POST http://localhost:8000/api/and9 \
  -H "Content-Type: application/json" \
  -d '{"query":"torch on karo"}'
# → {"response":"Flashlight on kar diya! 💡","action":"FLASHLIGHT","brain":"reflex","time_ms":1.8,...}

# Reflex: Call with contact
curl -X POST http://localhost:8000/api/and9 \
  -H "Content-Type: application/json" \
  -d '{"query":"call mummy"}'
# → {"response":"Call kar raha hoon Mummy ko... 📞","action":"CALL","brain":"reflex","time_ms":2.1,...}

# Conscious: LLM chat
curl -X POST http://localhost:8000/api/and9 \
  -H "Content-Type: application/json" \
  -d '{"query":"hello kaise ho"}'
# → {"response":"...","brain":"conscious","time_ms":1250,...}
```

---

## 🧪 Running Tests

```bash
# Run all core module tests
pytest tests/ -v

# Run specific test categories
pytest tests/ -k "semantic" -v    # Memory semantic tests
pytest tests/ -k "intent" -v       # Intent detection tests
pytest tests/ -k "emotion" -v      # Emotion detection tests
```

---

## 📄 License
Licensed under the MIT License. Built with love by **Minaty001**.
