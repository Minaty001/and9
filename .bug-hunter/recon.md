# JARVIS PCOS — Full Project Recon

## Project Overview
**JARVIS (Just A Rather Very Intelligent System)** — Hinglish-speaking Android AI assistant.
Flask web app + AND9 multi-brain cognitive architecture + PersonalOS unified layer.
Designed for Termux/Android deployment.

## Tech Stack
- **Runtime**: Python 3.14, Flask 3.x
- **Database**: Supabase (PostgreSQL via `supabase-py` SDK), in-memory dict fallback
- **LLM Providers**: Groq (primary, llama-3.3-70b) → Opencode Zen (fallback, deepseek-v4)
- **TTS**: Microsoft Edge TTS (`edge-tts` library) — server-side MP3 synthesis
- **AI/ML**: Custom NumPy neural network (micro_brain/), regex-NLP pipeline
- **Mobile**: Android APK (Kotlin/Java via Gradle in `android/`)

## Source Structure (~155 real source files)
```
app/
  main.py                  → Flask factory, rate limiter, startup init
  api/
    routes.py              → JSON API endpoints (chat, goals, events, TTS, AND9, PersonalityOS)
    web_routes.py          → Web UI routes
    admin_routes.py        → Admin endpoints
    memory_api.py          → Memory-specific endpoints
  core/
    brain.py               → LLM interface (Groq → Opencode fallback)
    memory.py              → Supabase-backed cognitive memory (chat, facts, episodes, emotions)
    truth_engine.py        → Truth-First validation (confidence map, verify_before_llm)
    orchestrator.py        → Central cognitive pipeline (Orchestrator class)
    understanding.py       → Regex-based intent/emotion/entity extraction
    context_builder.py     → Builds LLM context from memory layers
    config.py              → Env var config, lazy _ensure_notes_dir()
    goal_tracker.py        → Goal management (Supabase + in-memory)
    events.py              → EventSystem for reminders (Supabase + in-memory)
    reflection.py          → Session/daily reflection via LLM
    proactive.py           → Proactive suggestion engine (morning/evening tips)
    timer.py               → In-memory countdown timer with background thread
    personality_os.py      → PersonalOS — unified cognitive architecture wrapper
    personality.py         → System prompt / personality definitions
  and9/
    __init__.py            → Exports AND9, BrainType, IntentType, BrainResult
    and9.py                → AND9 main entry point
    brain_types.py         → Type definitions
    brain/
      cognitive_engine.py  → ReflexProcessor + HabitProcessor + Reasoning dispatch
      orchestrator.py      → AND9 brain orchestrator
      self_reflection.py   → Self-reflection module
    router/
      intent_router.py     → 18-level priority intent detection
      entity_extractor.py  → Intent-specific entity extraction
    android/
      action_registry.py   → Central action vocabulary (31 actions)
      chrome_firewall.py   → Blocks non-search actions from opening Chrome
      android_executor.py  → Single entry point for ALL Android action execution
      skill_registry.py    → Maps action_type → handler function + arg mapper
      validate_handlers.py → Startup validation of handler coverage
    actions/               → Per-action handler modules
    contacts/              → Contact resolution
    apps/                  → Package resolution
    media/                 → YouTube handler
    utils/
      time_parser.py       → Hinglish time/duration parser
  agents/
    __init__.py            → Agent registry (coding, research, assistant)
    coding_agent.py        → Code-related agent
    research_agent.py      → Research agent
    assistant_agent.py     → General assistant agent (chat, search, image, device)
  reminders/
    worker.py              → Background reminder scheduler
    db.py                  → Reminder DB
    storage.py             → Reminder storage
  skills/
    youtube.py             → YouTube/music skill
  static/                  → Static assets
  templates/               → Jinja2 templates
micro_brain/
  brain/
    neural.py              → TextEmbedding + TinyNeuralNetwork (NumPy)
    brain.py               → NeuralBrain wrapper, training, evaluation
  training/                → Training scripts
  database/                → Training data
  utils/                   → Helpers
  models/                  → Saved model files
tests/
  test_nlp_pipeline.py     → NLP pipeline tests
  test_imports.py          → Import tests
  integration_tests.py     → Integration tests
android/                   → Android APK source (Kotlin/Gradle)
scripts/                   → Build/deploy scripts
```

## Architecture Flow

### Request Lifecycle
```
HTTP Request
  → Flask (RateLimit → RequestID → Blueprint route)
    → Orchestrator.run(query)
      1. UnderstandingEngine.analyze() — intent, emotion, entities (regex)
      2. Memory store/recall check (direct regex ops, no LLM)
      3. Parallel fetch: memory_ctx + goals + events
      4. TRUTH ENGINE: if personal question + no verified memory → "mujhe nahi pata"
      5. ContextBuilder.build() — rich LLM prompt
      6. IntentRouter.route() — keyword-based routing (music/goal/reminder/reflection/device)
      7. Agent dispatch or LLM chat response
      8. Post-process (background thread): save episodes, record emotions

AND9 (separate pipeline, callable via /api/and9):
  → CognitiveEngine.process()
    1. REFLEX (<300ms) — direct keyword match, no LLM, no memory
    2. HABIT (~200ms) — time/day pattern matching
    3. REASONING (1-5s) — LLM dispatch (Orchestrator)
    4. MEMORY (async) — record episode, update habits
    5. REFLECTION (async) — self-evaluation
```

### Android Action Pipeline
```
Intent Detected (router/intent_router.py)
  → AND9.process()
    → android_executor.execute(action_type, params)
      → action_registry.get_action() — validate action exists
      → skill_registry.execute_skill() — import handler, call with mapped args
      → chrome_firewall.assert_not_chrome() — POST-execution check
      → Return result
```

## Trust Boundaries & Security Zones

| Zone | Components | Trust Level | Notes |
|------|-----------|-------------|-------|
| **External** | HTTP requests, Android client | Untrusted | Rate-limited (30/min/IP) |
| **API Layer** | Flask routes, Blueprints | Semi-trusted | Validates input shape, silent=True for JSON |
| **Orchestrator** | Orchestrator, IntentRouter | Trusted | No user input eval'd |
| **LLM Gateway** | brain.py → Groq/Opencode | Trusted outbound | API keys in env vars |
| **Memory** | memory.py → Supabase | Trusted inbound | Parameterized queries only |
| **Android Exec** | android_executor → ADB | Semi-trusted | Chrome Firewall blocks non-search Chrome routing |
| **Truth Gate** | truth_engine.py | Trusted | Configures confidence caps per source type |

### Security Patterns (Verified)
- ✅ All SQL uses parameterized queries (Supabase SDK)
- ✅ No `eval()`, `exec()`, `os.system()` with user input
- ✅ Chrome Firewall — defense-in-depth block on non-search actions opening Chrome
- ✅ Rate limiting — 30 req/min/IP, sliding window
- ✅ Truth Engine — confidence-gated fact storage (Rule 5: llm_inference=0.0, never stored)
- ✅ No LLM output auto-stored as memory (Rule 6)
- ✅ Source tracking on all memory writes (Rule 8)
- ✅ Flask `production` secret key via env var (fallback: random per boot)

## Components Sampled (Full Read)
- `/root/and9/app/main.py` — Flask factory, startup init
- `/root/and9/app/api/routes.py` — All API endpoints
- `/root/and9/app/core/brain.py` — LLM interface
- `/root/and9/app/core/memory.py` — Memory subsystem
- `/root/and9/app/core/truth_engine.py` — Truth validation
- `/root/and9/app/core/orchestrator.py` — Central orchestrator
- `/root/and9/app/core/events.py` — Event system
- `/root/and9/app/core/reflection.py` — Reflection engine
- `/root/and9/app/core/proactive.py` — Proactive engine
- `/root/and9/app/core/timer.py` — Timer service
- `/root/and9/app/core/config.py` — Config
- `/root/and9/app/and9/brain/cognitive_engine.py` — Cognitive engine
- `/root/and9/app/and9/android/action_registry.py` — Action registry
- `/root/and9/app/and9/android/chrome_firewall.py` — Chrome firewall
- `/root/and9/app/and9/android/android_executor.py` — Android executor
- `/root/and9/app/and9/android/skill_registry.py` — Skill registry
- `/root/and9/app/agents/__init__.py` — Agent registry
- `/root/and9/app/and9/utils/time_parser.py` — Time parser (partial)
- `/root/and9/app/and9/router/intent_router.py` — Intent router (partial)
- `/root/and9/app/and9/router/entity_extractor.py` — Entity extractor (partial)
- `/root/and9/micro_brain/brain/neural.py` — Neural network (quick scan)

## Potential Bug Categories Identified

### Logic / Correctness
1. **reflection.py name extraction false positive** — `main ` (Hindi "I") pattern in `extract_key_facts()` matches any sentence starting with "main", not just name declarations. The regex `r'(?:...|main |...)(\w+(?:\s+\w+)?)'` would match "main kya kar raha hoon" and store "kya" as the user's name.
2. **truth_engine.py `has_relevant_memory()`** returns True if ANY profile data exists regardless of confidence/verified status — could let low-confidence regex data through the truth gate.
3. **orchestrator.py `verify_before_llm` scope** — personal investigation keywords include `\bage\b` which matches "message", "page", "language" etc. (false positive).
4. **Goal completion ambiguity** — `_handle_goal()` always completes `goals[0]` (first active goal) without user specifying which one. If multiple goals exist, wrong one may be completed.

### Error Handling
5. **Supabase failures silently swallowed** — `Memory._safe()` catches ALL exceptions and returns `default=None`. Failed writes/reads return empty results silently. Callers don't distinguish "Supabase down" from "no data."
6. **Flask `request.get_json(silent=True)`** — returns `None` on parse failure, so `or {}` gives empty dict. Valid JSON with wrong types still passes.
7. **Timer's `_next_id()`** — `global _timer_id_counter` in a separate `app/core/timer.py` module. Not robust for multiprocessing (gunicorn with workers), though fine for threading.

### Time/Timezone
8. **events.py uses `datetime.utcnow()`** throughout — no timezone awareness. On Render.com (likely UTC) vs India (IST, UTC+5:30), reminder times could be off by 5.5 hours. Example: user says "kal 3 baje" → would set at 3 PM UTC = 8:30 PM IST, not 3 PM IST.
9. **time_parser.py** uses `datetime.now()` (local time) while events.py uses `datetime.utcnow()` — inconsistency could cause reminder-time mismatches.

### Threading/Safety
10. **orchestrator.py `run()`** creates a NEW `ThreadPoolExecutor` (max_workers=3) on every request at line 168, despite having a class-level `self._pool` at line 98. This creates/destroys threads on every call.

### Regressions
11. **chrome_firewall.py `assert_not_chrome()`** checks payload AFTER execution. If a malicious action handler already opened Chrome before the check, the firewall would detect but not prevent.
12. **Skill registry handlers** — lambdas in `skill_registry.py` capture variables but are registered at module import time, so all closure variables are stable. No lambda-in-loop bug here.

## Files Requiring Further Inspection (Hunter Phase)
- `app/and9/actions/*.py` — handler implementations (device_actions, call_actions, etc.)
- `app/and9/intents/*.py` — parameter extraction modules
- `app/core/personality_os.py` — cognitive architecture initialization
- `app/core/context_builder.py` — LLM context assembly
- `app/core/understanding.py` — regex-based analysis
- `app/reminders/worker.py` — background scheduler
- `app/skills/youtube.py` — YouTube integration
- `app/and9/and9.py` — AND9 main entry
- `micro_brain/brain/neural.py` — neural network (deep scan)
- `app/agents/*.py` — agent implementations
