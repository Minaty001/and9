# Phase 08: Context Builder

## Purpose
Manages conversation context across turns using a sliding window with time-based exponential decay, entity overlap scoring (Jaccard similarity), intent match boosting, and recency weighting. Enables follow-up queries like "and in Mumbai?" after "what's the weather in Delhi?" by scoring past turns against the current query.

## Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `JARVIS_CONTEXT_MAX_TURNS` | 10 | Max turns retained |
| `JARVIS_CONTEXT_DECAY_RATE` | 0.85 | Exponential decay factor |
| `JARVIS_CONTEXT_ENTITY_OVERLAP_WEIGHT` | 0.50 | Entity overlap weight |
| `JARVIS_CONTEXT_INTENT_MATCH_WEIGHT` | 0.25 | Intent match weight |
| `JARVIS_CONTEXT_RECENCY_WEIGHT` | 0.25 | Recency weight |
| `JARVIS_CONTEXT_SESSION_TIMEOUT_MINUTES` | 30 | Session auto-expiry |

## Architecture
```
ContextManager
  ├── add_turn(query, intent, entities) → TurnContext
  ├── get_snapshot() → ContextSnapshot (recent_turns, active_entities, intents)
  ├── search_relevant(query, top_k) → List[TurnScore]
  └── clear() — Reset session
Relevance = recency*0.25*decay + entity_overlap*0.50*decay + intent_match*0.25
```

## Code
```python
class ContextManager:
    def add_turn(self, query, intent="", entities=None, ...) -> TurnContext:
        turn = TurnContext(turn_id=self._next_turn_id++, query=query, ...)
        self._merge_entities(entities or {})
        self._turns.append(turn)
        if len(self._turns) > self.config.max_turns: self._turns.pop(0)
        return turn

    def search_relevant(self, query, top_k=5) -> List[TurnScore]:
        for i, turn in enumerate(self._turns):
            recency = (i + 1) / total_turns
            entity_score = self._compute_entity_overlap(query_entities, turn.entities)
            decay = turn.decay_factor(self.config.decay_rate)
            score = recency * decay * 0.25 + entity_score * decay * 0.50 + intent_score * 0.25
            scored.append((score, turn))
        scored.sort(reverse=True)
        return [TurnScore(turn, s) for s, turn in scored[:top_k]]
```

## Location
`app/brain/subconscious/` or `app/brain/` — context management
