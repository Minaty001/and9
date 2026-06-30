# Phase 14 — Decision Engine

Route across Reflex / Habit / Conscious brains based on confidence,
latency, permissions, and cost.

## Components

### `DecisionConfig`
Configuration with Pydantic v2 `model_config = {"env_prefix": "JARVIS_PHASE14_"}`.

| Field | Default | Description |
|-------|---------|-------------|
| `reflex_confidence_threshold` | `0.9` | Min confidence to route to reflex brain |
| `habit_confidence_threshold` | `0.7` | Min confidence to route to habit brain |
| `conscious_min_confidence` | `0.5` | Min confidence for conscious brain routing |
| `enable_escalation` | `True` | Allow escalation through brain tiers |
| `max_decision_time_ms` | `500` | Max decision latency before fallback |
| `track_latency` | `True` | Track routing decision latency |
| `cost_aware_routing` | `True` | Consider cost in routing decisions |
| `max_cost_per_decision` | `0.05` | Max cost in USD per decision |

### Models
- **`DecisionRequest`**: `query`, `intent`, `confidence`, `entities`, `context`, `available_brains`, `latency_budget_ms`, `max_cost`.
- **`DecisionResult`**: `selected_brain`, `confidence`, `reasoning`, `routing_path`, `latency_ms`, `estimated_cost`.

### `BrainRouter`
Core routing logic:
- **`route(request)`**: Pick brain based on confidence thresholds. Reflex if confidence >= 0.9, Habit if >= 0.7, Conscious otherwise.
- Respects `available_brains` — won't route to unavailable brains.
- Checks latency budget and cost budget; reroutes if constraints are violated.
- Tracks routing latency.

### `DecisionEngineService`
Lifecycle wrapper (`ServiceBase`):
- `initialize()` / `shutdown()` / `health()` / `stats()`
- `decide(request) → DecisionResult`

## Usage

```python
from services.phase14_decision import DecisionEngineService, DecisionConfig, DecisionRequest

config = DecisionConfig()
service = DecisionEngineService(config)
await service.initialize()

# High confidence → reflex brain
request = DecisionRequest(query="What is 2+2?", confidence=0.95)
result = await service.decide(request)
print(f"Routing to: {result.selected_brain}")

# Low confidence → conscious brain
request = DecisionRequest(query="Complex analysis", confidence=0.55)
result = await service.decide(request)
print(f"Routing to: {result.selected_brain}")
```
