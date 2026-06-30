# Phase 24 — Conversation Manager

Track dialogue state, active topic, user goals, pending questions. Reference resolution, session boundaries.

## Components

### ConversationConfig
Configuration for the conversation manager. Uses environment variable prefix `JARVIS_PHASE24_`.

| Field | Default | Description |
|---|---|---|
| service_name | `jarvis_conversation` | Service name |
| max_session_duration_minutes | `30` | Max session duration |
| max_turns_per_session | `100` | Max turns per session |
| enable_reference_resolution | `True` | Enable reference resolution |
| enable_topic_tracking | `True` | Enable topic tracking |
| enable_goal_tracking | `True` | Enable goal tracking |
| session_timeout_seconds | `1800` | Session timeout |

### DialogueState
Pydantic model: `session_id`, `turn_count`, `active_topic`, `user_goal`, `pending_questions`, `recent_entities`, `references`, `confidence`, `started_at`, `last_active`.

### Session
Pydantic model: `id`, `created_at`, `dialogue_states`, `metadata`, `active`.

### SessionManager
Manages session lifecycle:
- `create_session(metadata)` — Create new session with UUID
- `get_session(id)` — Get active session
- `end_session(id)` — End session
- `list_active_sessions()` — List all active
- `timeout_check()` — Expire timed-out sessions

### DialogueTracker
Tracks dialogue state:
- `update_state(session_id, query, intent, entities)` → DialogueState
- `detect_topic(query)` → Topic from keyword matching (weather, news, time, etc.)
- `track_goal(session_id, goal)` — Register user goals
- `add_pending_question(session_id, question)` — Track pending questions
- `extract_entities(query)` — Simple entity extraction

### ReferenceResolver
Resolves anaphoric references (it, that, this, they, etc.) using context from the last 3 dialogue turns.

### ConversationManagerService
ServiceBase wrapper providing `process_turn()`, `create/get/end_session()`, `get_state()`, `resolve_reference()`, `get_active_sessions()`.
