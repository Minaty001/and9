# Phase 15 — Skill Router

Plugin registry for skills, route by intent+entities, versioning, fallbacks.

## Components

- **SkillConfig**: Configuration with max_skills, versioning, fallback, plugin discovery settings.
- **SkillDefinition**: Pydantic model for a skill's id, name, version, intents, entities, priority, etc.
- **SkillResult**: Pydantic model for execution results with success, output, confidence, duration.
- **SkillRegistry**: Manages skill registration, unregistration, lookup, intent-based discovery with priority sorting and entity matching, version history.
- **SkillRouter**: Routes intents to matching skills, executes in priority order, falls back on failure.
- **SkillRouterService(ServiceBase)**: Full lifecycle service wrapper.

## Usage

```python
from services.phase15_skill import SkillRouterService, SkillDefinition

svc = SkillRouterService()
await svc.initialize()

skill = SkillDefinition(
    id="greeter",
    name="Greeter",
    intents=["greeting"],
    priority=10,
)
svc.register_skill(skill)

results = svc.route("greeting", {"name": "Jarvis"})
await svc.shutdown()
```

## Configuration

Environment variables with prefix `JARVIS_PHASE15_`:

| Variable | Default | Description |
|---|---|---|
| MAX_SKILLS | 100 | Maximum registered skills |
| ENABLE_VERSIONING | True | Version history tracking |
| ENABLE_FALLBACK | True | Fallback on skill failure |
| FALLBACK_TIMEOUT_MS | 5000 | Fallback execution timeout |
| ENABLE_PLUGIN_DISCOVERY | True | Automatic plugin discovery |
