# Phase 25 — Personality Engine

Separate personality from reasoning. Tone, style, greetings, response constraints. Configurable personas.

## Components

### PersonalityConfig
Configuration for the personality engine. Uses environment variable prefix `JARVIS_PHASE25_`.

| Field | Default | Description |
|---|---|---|
| service_name | `jarvis_personality` | Service name |
| active_persona | `jarvis_default` | Active persona ID |
| enable_persona_switching | `True` | Enable persona switching |
| enable_greeting_rules | `True` | Enable greeting rules |
| max_response_length | `500` | Max response length |
| default_tone | `helpful` | Default tone |

### Persona
Pydantic model: `id`, `name`, `tone`, `style_guide`, `greeting_rules`, `response_constraints`, `vocabulary_whitelist`, `vocabulary_blacklist`, `emoji_usage` (never/rarely/normal/expressive), `formality_level` (1-10), `metadata`.

### PersonalityProfile
Pydantic model: `active_persona_id`, `tone_scores`, `style_attributes`, `greeting_history`, `response_count`, `created_at`.

### PersonalityEngine
Core engine with built-in personas:
- **jarvis_default** — Helpful, professional, normal emoji, formality 7
- **jarvis_casual** — Friendly, conversational, normal emoji, formality 4
- **jarvis_professional** — Formal, precise, never emoji, formality 10

Methods:
- `set_persona(persona_id)` / `get_persona()` — Active persona management
- `register_persona(persona)` / `list_personas()` — Persona registry
- `apply_tone(text, persona)` — Tone adjustment (formality, contractions)
- `generate_greeting(context)` — Time-based or static greetings
- `constrain_response(text, persona)` — Length, vocabulary, emoji constraints
- `detect_tone(text)` — Keyword-based tone classification

### PersonalityEngineService
ServiceBase wrapper providing `apply_tone()`, `generate_greeting()`, `constrain_response()`, `set_persona()`, `get_persona()`, `detect_tone()`, `list_personas()`, `register_persona()`, `get_profile()`.
