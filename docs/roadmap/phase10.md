# Phase 10: Reflex Brain

## Purpose
Fastest processing layer — uses priority-ordered regex pattern matching to provide responses for well-known commands (greetings, farewells, thanks, time/date queries, help) without requiring the NLU pipeline. Each `ReflexAction` has a regex pattern, priority, optional response text, and optional dynamic handler function.

## Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `JARVIS_REFLEX_ENABLE_DEFAULT_ACTIONS` | true | Register built-in defaults |
| `JARVIS_REFLEX_CASE_SENSITIVE` | false | Case-sensitive matching |
| `JARVIS_REFLEX_MAX_ACTIONS` | 100 | Max registered actions |
| `JARVIS_REFLEX_DEFAULT_CONFIDENCE` | 0.95 | Default match confidence |

## Architecture
```
User Input → ReflexBrain.process(text)
  └── Iterates actions sorted by priority (ascending)
        └── First match wins
              ├── Static response or dynamic handler
              └── Returns ReflexResult(matched, intent, response, confidence)
```

## Code
```python
class ReflexBrain:
    def process(self, text: str) -> ReflexResult:
        for action in sorted(self._actions.values(), key=lambda a: a.priority):
            if action.is_enabled and action.match(text):
                result.matched = True; result.intent = action.intent
                if action.handler: result.response = action.handler(text)
                else: result.response = action.response
                return result
        return ReflexResult(matched=False)
```

## Location
`app/brain/reflex/` — fast pattern-matching brain module
