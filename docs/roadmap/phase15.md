# Phase 15: Skill Router

## Purpose
Plugin registry and router for skills. `SkillRegistry` manages skill registration with intent-based discovery, priority sorting, entity matching, and version history. `SkillRouter` routes intents to matching skills in priority order, with fallback to the next skill on failure. Skills define their handled intents, required/optional entities, and priority.

## Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `JARVIS_PHASE15_MAX_SKILLS` | 100 | Max registered skills |
| `JARVIS_PHASE15_ENABLE_VERSIONING` | true | Version history tracking |
| `JARVIS_PHASE15_ENABLE_FALLBACK` | true | Fallback on skill failure |
| `JARVIS_PHASE15_FALLBACK_TIMEOUT_MS` | 5000 | Fallback execution timeout |

## Architecture
```
SkillRouterService
  ├── SkillRegistry — register/unregister/find_by_intent/version history
  └── SkillRouter — route(intent, entities) → List[SkillResult], priority order + fallback
```

## Code
```python
class SkillRegistry:
    def find_by_intent(self, intent, entities=None) -> List[SkillDefinition]:
        matches = []
        for skill in self._skills.values():
            if not skill.enabled or intent not in skill.intents: continue
            required_set = set(skill.required_entities)
            if required_set and not required_set.issubset(set(entities.keys())): continue
            matches.append(skill)
        matches.sort(key=lambda s: (-s.priority, -matched_entities))
        return matches

class SkillRouter:
    def route(self, intent, entities=None, context=None) -> List[SkillResult]:
        for skill in self._registry.find_by_intent(intent, entities):
            if not skill.enabled: continue
            result = self._execute_skill(skill, intent, entities, context)
            if result.success: break  # first success wins
```

## Location
`app/skills/` — skill definitions and routing
