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

JARVIS parses natural language requests and converts them into intent payloads executed natively on Android or via web fallbacks.

### 📅 Timezone, Alarm & Reminder Commands

| Function | Intent Type | English Example | Hinglish Example |
| :--- | :--- | :--- | :--- |
| **Check Time Zone / City Time** | `get_time` | `what is the time in Mumbai` / `current time in Delhi` | `dilli ka time` / `mumbai me kya time ho raha hai` |
| **Set Alarm** | `set_alarm` | `alarm 7 am` / `alarm tomorrow 7 am` / `alarm after 5 minutes` | `alarm lagao 7 baje` / `kal subah 7 baje alarm lagao` |
| **Set Reminder** | `set_reminder` | `remind me after 5 min` / `remind me tomorrow` / `remind me to call mummy at 7 pm` | `5 minute baad yaad dilana` / `reminder set karo` |

For exact API payloads, JSON structures, and more natural language command examples, refer to the **[Commands Reference & Intent Guide](COMMANDS_REFERENCE.md)** (or see `app/and9/utils/time_parser.py` for direct syntax mapping).

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
  │    │    ├── intents/                 ← Intent parsers (delegate to router)
  │    │    │    ├── call_intents.py
  │    │    │    ├── alarm_intents.py
  │    │    │    ├── timer_intents.py
  │    │    │    ├── reminder_intents.py
  │    │    │    ├── media_intents.py
  │    │    │    ├── app_intents.py
  │    │    │    └── search_intents.py
  │    │    │
  │    │    ├── actions/                 ← Action executors
  │    │    │    ├── call_actions.py     (Call/SMS with contact resolution)
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
  │    │    │    └── resolver.py         (20+ Hindi contacts, fuzzy matching)
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

## 🛠️ Recent Stability & Bug Fixes

A comprehensive sweep was performed to resolve critical runtime errors and logic flaws across the intent execution and orchestration pipelines:

1. **Parameter Mismatches in Device Actions**: Fixed a `TypeError` where action handlers (`handle_flashlight`, `handle_wifi`, `handle_bluetooth`, `handle_airplane_mode`, `handle_volume`) expected `query` or custom arguments, but `skill_registry` invoked them with mismatched keywords (e.g., `q`, `keyword`).
2. **Missing Search Action Handler**: Implemented the missing `handle_search()` function in [device_actions.py](file:///root/and9/app/and9/actions/device_actions.py) which was mapped in the registry but not actually defined.
3. **Skill Registry Omissions**: Corrected missing skill registrations for `flashlight_on`, `flashlight_off`, and `search` in [skill_registry.py](file:///root/and9/app/and9/android/skill_registry.py) which previously fell back to empty configurations.
4. **Orchestrator Log Operator Precedence**: Resolved a logical bug in [orchestrator.py](file:///root/and9/app/and9/brain/orchestrator.py)'s `_log_result()` where intent logging dropped when `result.intent` was `None` due to incorrect logical evaluation.
5. **Datetime Manipulation in Reminders**: Fixed a runtime `TypeError` in [reminder_actions.py](file:///root/and9/app/and9/actions/reminder_actions.py) where `datetime.replace()` was incorrectly passed `None` values (e.g. `hour=None`).
6. **Local Variable Anti-pattern in Alarms**: Removed dynamic local evaluation anti-pattern (`locals().get("day_offset", 0)`) in [alarm_actions.py](file:///root/and9/app/and9/actions/alarm_actions.py), replacing it with clean, explicit initialization.
7. **Nested Event Loop Block in API Routes**: Replaced problematic `asyncio.run()` invocation in [routes.py](file:///root/and9/app/api/routes.py) with a robust helper `_run_async()` to avoid throwing runtime errors when an event loop is already running.

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
