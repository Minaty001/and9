# JARVIS PCOS — Personal Cognitive Operating System (Neural Engine v4)

**JARVIS** is a voice-first AI assistant with multi-agent orchestration, LLM-powered intent routing, web dashboard, Android/Termux integration, image generation, memory persistence, and daily activity logging. It supports Hinglish, Hindi, and English natural language commands.

---

## Features

- **LLM-Powered Intent Routing** — Uses Groq (Llama 3.3-70B) to classify user intent and extract parameters from Hinglish/Hindi/English sentences. No rigid keyword matching.
- **14 Intent Categories** — music, device_app, device_call, device_control, timer, reminder, goal, search, research, image, coding, reflection, memory, and general chat.
- **50+ Android App Support** — Open apps via Hinglish aliases (`yt`→YouTube, `wa`→WhatsApp, `calci`→Calculator, `gp`→GPay, etc.).
- **Device Control** — Flashlight, WiFi, Bluetooth, volume, brightness, battery status, camera, screenshot.
- **Music Playback** — YouTube search and auto-play via natural language requests ("Arijit Singh ka gaana bajao").
- **Timer/Countdown** — Server-side timers with full-screen overlay, TTS alerts, and vibration on the frontend.
- **Goal/Task Tracking** — Add, list, and complete goals with priority levels.
- **Reminders & Events** — Natural language event creation and listing.
- **Daily Reflection** — Auto-generated daily reviews and session summaries.
- **Web Search & Research** — Quick search via SerpAPI or deep multi-source research with citations.
- **Image Generation** — AI image generation via Pollinations API.
- **Coding Assistant** — Code generation, debugging, explanation, and Python execution.
- **Memory System** — SQLite-backed episodic, semantic, and emotional memory with fast LRU recall cache.
- **Daily Activity Logging** — Every conversation turn saved to `activities/YYYY-MM-DD.txt`, viewable/editable/copyable from the admin panel.
- **Proactive Intelligence** — Time-aware greetings, suggestions, productivity streaks, and quick action chips for the Android home screen.
- **TTS** — Server-side Microsoft Edge TTS (en-IN-NeerjaNeural / hi-IN-SwaraNeural) with auto-language detection.
- **Admin Panel** — Password-protected admin interface for file browsing, database viewing, data management, and activity log access.
- **Android Client** — Native Android app with overlay UI, voice wake-up, and intent execution.
- **Deployable on Render.com** — Zero audio/Android dependencies in cloud mode.

---

## Architecture

### Three-Brain Cognitive Model

```
User Input
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  REFLEX BRAIN  (LLMIntentRouter — LLM-based classifier) │
│  Classifies intent + extracts parameters from natural   │
│  language in Hinglish/Hindi/English                     │
└──────────────────────────┬──────────────────────────────┘
                           │
    ┌──────────────────────▼──────────────────────┐
    │  SUBCONSCIOUS BRAIN  (Memory + Context)      │
    │  • EpisodicMemory   — what happened          │
    │  • SemanticMemory   — what we know           │
    │  • EmotionalMemory  — how user feels         │
    │  • GoalTracker      — what user wants        │
    │  • EventSystem      — upcoming reminders     │
    │  → Builds full context string for LLM        │
    └──────────────────────┬──────────────────────┘
                           │
    ┌──────────────────────▼──────────────────────┐
    │  CONSCIOUS BRAIN  (LLM — ask_llm)            │
    │  Primary:  Groq (llama-3.3-70b)              │
    │  Fallback: Opencode Zen (deepseek-v4-flash)  │
    └──────────────────────┬──────────────────────┘
                           │
    ┌──────────────────────▼──────────────────────┐
    │  REFLECTION ENGINE  (Post-processing)        │
    │  • Auto-extract facts from every session     │
    │  • Daily review generation                   │
    │  • Session summarization to database         │
    │  • Activity logging to daily text files      │
    └─────────────────────────────────────────────┘
```

### Project Structure

```
and9/
  ├── android/               (Native Android client source app)
  │   ├── app/src/main/java/com/jarvis/assistant/
  │   │   ├── overlay/       (Overlay UI controller)
  │   │   ├── services/      (Accessibility, Session, Voice Interaction)
  │   │   └── voice/         (Backend client, TTS, debug logger)
  │   └── app/src/main/res/  (Layouts, drawables, configs)
  ├── app/
  │   ├── agents/
  │   │   ├── __init__.py    (Agent registry)
  │   │   ├── assistant_agent.py  (Search, image, device, reasoning, chat)
  │   │   ├── coding_agent.py     (Code generation, debugging, execution)
  │   │   └── research_agent.py   (Multi-source research with citations)
  │   ├── api/
  │   │   ├── routes.py      (Chat, memory, goals, events, TTS, timer, proactive)
  │   │   ├── admin_routes.py(Admin auth, file browser, DB viewer, activity logs)
  │   │   └── web_routes.py  (HTML page routes)
  │   ├── core/
  │   │   ├── orchestrator.py     (Central cognitive pipeline)
  │   │   ├── intent_router.py    (LLM-powered intent classifier)
  │   │   ├── brain.py            (LLM interface: Groq + Opencode fallback)
  │   │   ├── config.py           (Environment-based configuration)
  │   │   ├── memory.py           (SQLite episodic/semantic/emotional memory)
  │   │   ├── context_builder.py  (Prompt context assembly)
  │   │   ├── understanding.py    (Intent, emotion, entity extraction)
  │   │   ├── goal_tracker.py     (Goal/project management)
  │   │   ├── events.py           (Reminder/event scheduling)
  │   │   ├── reflection.py       (Daily review & session summary)
  │   │   ├── timer.py            (Thread-safe countdown timer service)
  │   │   ├── activity_logger.py  (Daily conversation logging)
  │   │   ├── proactive.py        (Proactive suggestions & briefing)
  │   │   └── personality.py      (System prompts)
  │   ├── skills/
  │   │   ├── intent_executor.py  (Android intent payload generation, 50+ apps)
  │   │   ├── tasks.py            (Device commands, search, image gen)
  │   │   ├── youtube.py          (YouTube search and playback)
  │   │   ├── research.py         (Source fetching + synthesis)
  │   │   └── img.py              (Image generation)
  │   ├── static/                 (JS, CSS for web UI)
  │   ├── templates/              (HTML templates: admin panel, main UI)
  │   └── main.py                 (Flask application factory)
  ├── scripts/                    (APK rebuild and patching utilities)
  ├── tests/                      (Test suite)
  ├── .env.example                (Environment variable template)
  ├── requirements.txt            (Python dependencies)
  ├── Dockerfile                  (Container build)
  ├── docker-compose.yml          (Multi-service orchestration)
  └── render.yaml                 (Render.com deployment config)
```

---

## Intent Routing

Commands are classified by the **LLMIntentRouter** which uses Groq's LLM to understand natural language in Hinglish, Hindi, and English.

### Intent Categories

| Intent | Description | Example |
|--------|-------------|---------|
| `music` | Play songs on YouTube | "Tum Hi Ho sunao", "gaana chalao", "Arijit Singh ka gaana bajao" |
| `device_app` | Open Android apps | "youtube open karo", "calculator kholo", "whatsapp chalao" |
| `device_call` | Make phone calls | "Mummy ko call karo", "dial 9876543210" |
| `device_control` | Change device settings | "flashlight on karo", "wifi band karo", "volume up karo" |
| `timer` | Set countdowns | "5 minute ka timer laga do", "30 second ka alarm" |
| `reminder` | Set/list reminders | "kal subah 8 baje yaad dilana", "meri reminders dikhao" |
| `goal` | Manage goals/tasks | "goal add karo", "mera goal complete karo" |
| `search` | Quick web search | "weather kya hai", "who is Narendra Modi" |
| `research` | Deep research | "research karo climate change", "deep dive history of India" |
| `image` | Generate AI images | "ek sher ka photo banao", "draw a cat wearing a hat" |
| `coding` | Code help | "python mein calculator ka code likho", "debug karo" |
| `reflection` | Daily review | "aaj kya kiya", "daily review karo" |
| `memory` | Recall conversations | "kya bola tha maine", "pehle wali baat yaad karo" |
| `chat` | General conversation | "hello", "kaise ho", "what's up" |

### System Architecture Flow

```
User says "JARVIS, Arijit Singh ka gaana bajao"
    → POST /api/chat { message }
        → Orchestrator.run()
            → UnderstandingEngine.analyze()
            → LLMIntentRouter.classify() → music intent
                → Parameters: { "song": null, "artist": "Arijit Singh" }
            → _handle_music() → YouTube search
            → _post_process() → save to memory + activity log
        → Response with youtube_url
    → Frontend auto-plays in YouTube app
```

---

## API Endpoints

### Chat & Core

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat` | Process a message through the full cognitive pipeline |
| GET | `/api/agents` | List available agents/intents |
| GET | `/api/history` | Get recent chat history |
| GET | `/api/health` | Health check |

### Memory

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/memory/facts` | Get stored user facts |
| POST | `/api/memory/learn` | Store a fact |
| DELETE | `/api/memory/fact` | Delete a fact |
| GET | `/api/memory/search?q=` | Search facts |
| GET | `/api/memory/recall?q=` | Fast cross-session recall |
| GET | `/api/memory/episodes/search?q=` | Search episodic memory |
| GET | `/api/memory/sessions` | Session summaries |

### Goals

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/goals` | List goals |
| POST | `/api/goals` | Create a goal |
| PATCH | `/api/goals/<id>` | Update goal status |
| DELETE | `/api/goals/<id>` | Delete a goal |

### Events/Reminders

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/events` | List upcoming events |
| POST | `/api/events` | Create an event |
| PATCH | `/api/events/<id>/done` | Mark event as done |

### Timer

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/timer` | Create a countdown timer |
| GET | `/api/timer/alerts` | Poll for expired timers |
| GET | `/api/timer/<id>` | Get timer status |
| DELETE | `/api/timer/<id>` | Cancel a timer |

### TTS

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/tts` | Convert text to speech (MP3) |
| GET | `/api/tts/voices` | List available Indian voices |

### Proactive Intelligence

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/proactive/briefing` | Full briefing for Android home screen |
| GET | `/api/proactive/suggestion` | Context-aware suggestion |

### Admin (password: `code10` / `codeten`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/admin/panel` | Admin panel HTML |
| POST | `/api/admin/auth` | Authenticate |
| POST | `/api/admin/logout` | Logout |
| GET | `/api/admin/check` | Check auth status |
| GET | `/api/admin/files?path=` | List files |
| GET | `/api/admin/file?path=` | Read a file |
| PUT | `/api/admin/file` | Write/edit a file |
| GET | `/api/admin/data` | View database contents |
| POST | `/api/admin/data/clear` | Clear chat/facts/all |
| GET | `/api/admin/images` | List generated images |
| GET | `/api/admin/activities` | List activity log files |
| GET | `/api/admin/activity?date=` | Read a day's activity log |
| PUT | `/api/admin/activity` | Edit an activity log |

---

## Quick Start

### Prerequisites

- Python 3.11+
- A [Groq](https://console.groq.com) API key (primary LLM)
- (Optional) [SerpAPI](https://serpapi.com) key for web search

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/Minaty001/and9.git
cd and9

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your API keys (at minimum GROQ_API_KEY)

# 4. Run the server
gunicorn app.main:app --workers 2 --threads 4 --bind 0.0.0.0:8000
```

Or for development:

```bash
python app/main.py
# Server starts at http://localhost:8000
```

---

## Android Client

### Building from Source

The Android interface is in the `android/` directory.

1. Create/update `android/local.properties`:
   ```properties
   JARVIS_BASE_URL=https://your-backend-app.onrender.com/api
   ```

2. Build the debug APK:
   ```bash
   cd android
   ./gradlew assembleDebug
   # Output: android/app/build/outputs/apk/debug/app-debug.apk
   ```

### Custom APK Rebuilding

If you have an existing signed APK and need to inject system permissions:

```bash
python3 scripts/rebuild_user_apk.py
```

This script:
1. Decompiles the APK
2. Removes digital assistant service overrides
3. Injects high-access permissions (`MANAGE_EXTERNAL_STORAGE`, `CALL_PHONE`, `READ_CONTACTS`)
4. Repackages, aligns, and signs with a generated key

---

## Deployment

### Render.com

The project is configured for Render.com via `render.yaml`. Required environment variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | Yes | Primary LLM (Groq) |
| `SECRET_KEY` | Yes | Flask session signing |
| `SERP_API_KEY` | No | Web search |
| `SUPABASE_URL` | No | Database URL |
| `SUPABASE_KEY` | No | Database key |
| `OPENCODE_API_KEY` | No | Fallback LLM |

```bash
# Render start command
gunicorn app.main:app --workers 2 --threads 4 --timeout 120
```

### Docker

```bash
docker-compose up --build
```

---

## Environment Variables

See `.env.example` for the full template. Key variables:

```bash
# Required
GROQ_API_KEY=gsk-...                 # Groq LLM access
SECRET_KEY=random-32-char-string     # Flask session signing

# Optional (features degrade gracefully when absent)
SERP_API_KEY=...                     # Web search
OPENCODE_API_KEY=...                 # Fallback LLM
SUPABASE_URL=...                     # Supabase project URL
SUPABASE_KEY=...                     # Supabase anon/service key
WEATHER_API_KEY=...                  # Weather data
```

---

## Admin Panel

Access the admin panel at `/api/admin/panel`.

- **Password**: `code10` or `codeten`
- **Features**: File browser, database viewer, data management, activity log viewer/editor, image gallery

---

## Supported Apps (50+)

JARVIS can open these Android apps using natural language aliases:

| Category | Apps |
|----------|------|
| **Google** | YouTube/yt, Chrome, Google, Gmail, Maps, Photos, Drive, Calendar, Meet |
| **Communication** | WhatsApp/wa, Telegram/tg, Instagram/ig, Facebook/fb, Messenger, Twitter/X |
| **Media** | Spotify, Netflix, Prime Video, Hotstar, JioCinema, Gaana |
| **Tools** | Calculator/calc/calci, Camera, Settings, Files, Clock, Play Store |
| **Browsers** | Firefox, Edge, Brave, Opera, UC Browser |
| **Productivity** | Keep/Notes, Docs, Sheets, Slides |
| **Shopping** | Flipkart, Amazon, Myntra, Meesho |
| **Payments** | GPay/Google Pay, PhonePe, Paytm |
| **Travel** | Uber, Ola, IRCTC, RedBus |
| **Food** | Zomato, Swiggy |
| **Phone** | Phone/Dialer, Contacts, Truecaller |

---

## License

MIT License. Built with love by **Minaty001**.
