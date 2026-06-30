# Phase 24: Conversation Manager

## Purpose
Manage multi-turn conversation sessions with dialogue tracking, reference resolution, and session lifecycle. `SessionManager` handles session CRUD and timeout expiry. `DialogueTracker` tracks topics, goals, entities, and pending questions per session. `ReferenceResolver` resolves pronouns and anaphora using recent dialogue context (last N turns).

## Architecture
```
SessionManager
  ├── create_session(metadata) → Session
  ├── get_session(id) → Session | None
  ├── end_session(id) → bool
  ├── list_active_sessions() → List[Session]
  ├── timeout_check() — expire stale sessions
  ├── add_dialogue_state(session_id, state) → bool
  └── get_dialogue_state(session_id) → DialogueState | None

DialogueTracker
  ├── update_state(session_id, query, intent, entities) → DialogueState
  ├── detect_topic(query) — keyword-based topic detection
  ├── track_goal(session_id, goal)
  ├── extract_entities(query) → dict
  └── add_pending_question(session_id, question)

ReferenceResolver
  ├── resolve(reference, session_id, dialogue_states) → str
  └── extract_references(text) → List[str]

Models: Session, DialogueState
```

## Code
```python
class SessionManager:
    def create_session(self, metadata=None) -> Session:
        session = Session(id=str(uuid.uuid4()), metadata=metadata or {})
        self._sessions[session.id] = session
        return session

    def timeout_check(self) -> int:
        expired = 0
        for sid, session in list(self._sessions.items()):
            if not session.active: continue
            last = session.dialogue_states[-1].last_active
            if (datetime.now(timezone.utc) - last).total_seconds() > self._session_timeout:
                session.active = False; expired += 1
        return expired

class DialogueTracker:
    def update_state(self, session_id, query, intent=None, entities=None) -> DialogueState:
        topic = self.detect_topic(query)
        state = DialogueState(session_id=session_id, active_topic=topic, turn_count=1)
        return state

    def detect_topic(self, query) -> str:
        for topic, keywords in TOPIC_KEYWORDS.items():
            for kw in keywords:
                if kw in query.lower(): return topic
        return "general"

class ReferenceResolver:
    def resolve(self, reference, session_id, dialogue_states) -> str:
        context = list(reversed(dialogue_states[-self._max_context_turns:]))
        for state in context:
            if state.references:
                return next(iter(state.references.values()))
        return reference
```

## Location
`app/core/conversation/` — session manager, dialogue tracker, reference resolver, models
