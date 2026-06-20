# JARVIS — Personal Cognitive Operating System (PCOS)
## Full Architecture Implementation

---

## Three-Brain Cognitive Model

```
User Input
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  REFLEX BRAIN  (IntentRouter — zero LLM, <1ms)          │
│  Pattern match → route: chat / music / goal /           │
│  reminder / reflection / search / code / image          │
└──────────────────────────┬──────────────────────────────┘
                           │
    ┌──────────────────────▼──────────────────────┐
    │  SUBCONSCIOUS BRAIN  (Memory + Context)     │
    │  • EpisodicMemory   — what happened         │
    │  • SemanticMemory   — what we know          │
    │  • EmotionalMemory  — how user feels        │
    │  • GoalTracker      — what user wants       │
    │  • EventSystem      — upcoming reminders    │
    │  → Builds full context string for LLM       │
    └──────────────────────┬──────────────────────┘
                           │
    ┌──────────────────────▼──────────────────────┐
    │  CONSCIOUS BRAIN  (LLM — ask_llm)           │
    │  Primary:  Groq (llama-3.3-70b) — 90s TO   │
    │  Fallback: Opencode Zen (deepseek-v4-flash) │
    │  Rate: 1.2x TTS via edge-tts (en-IN)        │
    └──────────────────────┬──────────────────────┘
                           │
    ┌──────────────────────▼──────────────────────┐
    │  REFLECTION ENGINE  (Post-processing)       │
    │  • Auto-extract facts from every session    │
    │  • Daily review generation                  │
    │  • Session summarization to Supabase        │
    └─────────────────────────────────────────────┘
```

---

## Component Map

| Layer | File | Status |
|-------|------|--------|
| Reflex Brain | `app/core/orchestrator.py` → `IntentRouter` | ✅ |
| Subconscious — Episodic | `app/core/memory.py` → `Memory` | ✅ |
| Subconscious — Semantic | `app/core/memory.py` → `semantic_memory` table | ✅ |
| Subconscious — Emotional | `app/core/memory.py` → `emotional_memory` table | ✅ |
| Subconscious — Goals | `app/core/goal_tracker.py` → `GoalTracker` | ✅ |
| Subconscious — Events | `app/core/events.py` → `EventSystem` | ✅ |
| Context Builder | `app/core/context_builder.py` | ✅ |
| Conscious Brain | `app/core/brain.py` → `ask_llm()` | ✅ |
| Personality | `app/core/personality.py` | ✅ |
| Reflection Engine | `app/core/reflection.py` | ✅ |
| Voice Input | `app/static/script.js` → SpeechRecognition (en-IN) | ✅ |
| Voice Output | `app/api/routes.py` → `/api/tts` → edge-tts | ✅ |
| YouTube (Music) | `app/skills/youtube.py` | ✅ |
| Agent: Chat | `app/agents/assistant_agent.py` | ✅ |
| Agent: Code | `app/agents/coding_agent.py` | ✅ |
| Agent: Research | `app/agents/research_agent.py` | ✅ |
| Database | Supabase (PostgreSQL) | ✅ |

---

## Intent Routing

```
"soft song laga do"     → music     → YouTube search + auto-play
"mera goal add karo"    → goal      → GoalTracker.add_goal()
"remind me kal 5 baje"  → reminder  → EventSystem.add_event()
"aaj kya kiya"          → reflection → ReflectionEngine.daily_review()
"Taj Mahal kya hai"     → search    → SearchAgent
"code mein bug hai"     → coding    → CodingAgent
"generate image"        → image     → ImageSkill
everything else         → chat      → AssistantAgent (LLM)
```

---

## Supabase Tables (9 total)

```sql
chat_history          — raw message log
user_facts            — key-value knowledge (backward compat)
conversation_sessions — session lifecycle
episodic_memory       — timestamped conversation events
semantic_memory       — structured long-term facts (category/key/value)
emotional_memory      — per-topic emotion history
goals                 — user goals with priority + status
projects              — user projects
events                — reminders with event_time + repeat
```
Schema: `app/core/supabase_schema.sql`

---

## LLM Pipeline

```
ask_llm(messages, context=..., max_tokens=512)
    │
    ├─► Groq API (primary, 90s timeout)
    │       llama-3.3-70b-versatile
    │
    └─► Opencode Zen (fallback, 95s timeout)
            deepseek-v4-flash-free
```

---

## Voice Pipeline

```
Mic → SpeechRecognition (en-IN, Hinglish) → text
                                              │
                                              ▼
                                        Orchestrator.run()
                                              │
                                              ▼
                                         LLM response text
                                              │
                                              ▼
                              POST /api/tts { text, rate: "+20%" }
                                              │
                                         edge-tts (Microsoft Neural)
                                         en-IN-NeerjaNeural (Hinglish)
                                         hi-IN-SwaraNeural  (Hindi)
                                              │
                                         MP3 audio → HTMLAudioElement
```

---

## Deployment

- **Platform**: Render.com (Web Service)
- **Server**: Gunicorn + gthread workers
- **Env vars required**:
  - `GROQ_API_KEY` — primary LLM
  - `OPENCODE_API_KEY` — fallback LLM
  - `SUPABASE_URL` — already set in config
  - `SUPABASE_KEY` — from Supabase dashboard → API → anon key
