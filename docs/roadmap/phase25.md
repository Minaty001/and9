# Phase 25: Personality Engine

## Purpose
Manages JARVIS personality, tone, and persona switching. `PersonalityEngine` provides persona management, tone application, greeting generation, response constraints, and tone detection. `PersonalityService` wraps the engine with a service lifecycle. Built-in personas include `jarvis_default` (helpful), `jarvis_casual` (friendly), and `jarvis_professional` (formal). Supports user profile enrichment, emotional context, and expertise-level prompt building.

## Architecture
```
PersonalityEngine
  ├── set_persona(id) / get_persona() / register_persona() / list_personas()
  ├── apply_tone(text, persona) — formality adjustments, contraction expansion
  ├── generate_greeting(context) — time-based greetings
  ├── constrain_response(text, persona) — length, blacklist, emoji filtering
  ├── detect_tone(text) → "formal" | "casual" | "empathetic" | "humorous" | "helpful"
  ├── get_profile() → PersonalityProfile
  └── built-in: BUILTIN_PERSONAS (jarvis_default, jarvis_casual, jarvis_professional)

PersonalityService
  ├── initialize() / shutdown()
  ├── apply_tone() / generate_greeting() / constrain_response()
  ├── set_persona() / get_persona() / list_personas() / register_persona()
  ├── detect_tone()
  ├── health() / stats()
  └── wraps PersonalityEngine

build_personality_prompt(user_profile, emotional_context, expertise_level) → str
Models: Persona, PersonalityProfile
```

## Code
```python
class PersonalityEngine:
    def set_persona(self, persona_id: str) -> bool:
        if persona_id not in self._personas: return False
        self._active_persona_id = persona_id
        return True

    def apply_tone(self, text, persona=None) -> str:
        p = persona or self.get_persona()
        if p.formality_level >= 9:
            for casual, formal in {"i'm": "I am", "don't": "do not"}.items():
                text = text.replace(casual, formal)
        return text

    def constrain_response(self, text, persona=None) -> str:
        p = persona or self.get_persona()
        max_len = p.response_constraints.get("max_length", 500)
        if len(text) > max_len: text = text[:max_len].rsplit(" ", 1)[0] + "..."
        return text

class PersonalityService:
    async def initialize(self):
        self.engine = PersonalityEngine(active_persona_id=self._active_persona)
        self._initialized = True
```

## Location
`app/core/personality.py` — personality engine, service, personas, and prompt builder
