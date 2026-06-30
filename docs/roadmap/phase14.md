# Phase 14: Decision Engine

## Purpose
Routes requests across Reflex/Habit/Conscious brains based on confidence thresholds, latency budget, and cost awareness. `BrainRouter` selects the appropriate brain tier: Reflex (confidence ≥ 0.9, fastest/cheapest), Habit (≥ 0.7), or Conscious (≥ 0.5, most capable). Re-routes if latency or cost budgets are violated.

## Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `JARVIS_PHASE14_REFLEX_CONFIDENCE_THRESHOLD` | 0.9 | Min confidence for reflex routing |
| `JARVIS_PHASE14_HABIT_CONFIDENCE_THRESHOLD` | 0.7 | Min confidence for habit routing |
| `JARVIS_PHASE14_CONSCIOUS_MIN_CONFIDENCE` | 0.5 | Min confidence for conscious routing |
| `JARVIS_PHASE14_ENABLE_ESCALATION` | true | Allow escalation through brain tiers |
| `JARVIS_PHASE14_MAX_DECISION_TIME_MS` | 500 | Max decision latency |
| `JARVIS_PHASE14_COST_AWARE_ROUTING` | true | Consider cost in routing |

## Architecture
```
BrainRouter.route(request)
  ├── _route_by_confidence(request) → brain name + reasoning
  ├── Check latency_budget_ms vs BRAIN_LATENCY_ESTIMATES
  ├── Check max_cost vs BRAIN_COST_ESTIMATES
  └── Re-route to faster/cheaper brain if constraints violated
```

## Code
```python
class BrainRouter:
    BRAIN_COST_ESTIMATES = {"reflex": 0.001, "habit": 0.005, "conscious": 0.05}
    BRAIN_LATENCY_ESTIMATES = {"reflex": 10, "habit": 50, "conscious": 500}

    def route(self, request: DecisionRequest) -> DecisionResult:
        selected, reasoning = self._route_by_confidence(request)
        est_latency = BRAIN_LATENCY_ESTIMATES.get(selected, 100)
        if est_latency > request.latency_budget_ms:
            selected = self._find_faster_brain(selected, request)
        return DecisionResult(selected_brain=selected, reasoning=..., ...)

    def _route_by_confidence(self, request):
        if request.confidence >= 0.9 and request.has_brain("reflex"): return "reflex", ...
        if request.confidence >= 0.7 and request.has_brain("habit"): return "habit", ...
        return "conscious", ...
```

## Location
`app/brain/decision/` — routing and decision logic
