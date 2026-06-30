# Phase 11: Habit Brain

## Purpose
Learns recurring routines and user preferences by observing command patterns over time (time, day, location, entities). `HabitTracker` builds confidence via frequency (`1-e^(-freq/5)`) and recency decay, while `HabitSuggester` ranks habits by context match (time proximity, day match, location) for user approval.

## Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `JARVIS_HABIT_MIN_OBSERVATIONS` | 3 | Min occurrences before suggesting |
| `JARVIS_HABIT_CONFIDENCE_THRESHOLD` | 0.6 | Min confidence to surface suggestion |
| `JARVIS_HABIT_DECAY_RATE` | 0.9 | Per-day decay multiplier |
| `JARVIS_HABIT_TIME_WINDOW_MINUTES` | 30 | Time tolerance for matching |
| `JARVIS_HABIT_REQUIRE_USER_APPROVAL` | true | Require approval before auto-exec |

## Architecture
```
HabitTracker.observe(command, hour, day, location)
  └── Match existing pattern by command + time proximity
        └── Update frequency, confidence, typical_hour (EMA)
              └── New pattern if no match found
HabitSuggester.suggest(hour, day, location)
  └── Score patterns: confidence + time_proximity + day_match + location + approval_boost
```

## Code
```python
class HabitTracker:
    def observe(self, observation) -> HabitPattern:
        pattern = self._find_matching_pattern(observation)
        if pattern: self._update_pattern(pattern, observation)
        else: pattern = HabitPattern(pattern_id=uuid, command=observation.command, ...)
        confidence = 0.3 + 0.5*(1 - e^(-frequency/5)) + 0.2*(1/(1+age_days/30))
        return pattern

class HabitSuggester:
    def suggest(self, current_hour, current_day=-1, location=None) -> List[HabitSuggestion]:
        for pattern in self.tracker.get_patterns():
            score = pattern.confidence
            if time_diff <= time_window: score += 0.15*(1 - time_diff/2)
            if pattern.typical_day == current_day: score += 0.1
            if pattern.location == location: score += 0.1
        sorted(score, reverse=True)[:limit]
```

## Location
`app/brain/subconscious/` — habit learning module
