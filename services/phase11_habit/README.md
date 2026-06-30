# Phase 11: Habit Brain

## Overview

Learns recurring routines and user preferences by observing command patterns over time. Suggests automation candidates for user approval.

## Architecture

```
User Commands
     │
     ▼
┌─────────────────────┐
│   HabitTracker       │  ◄── Observes time/location/command patterns
│                      │       Builds confidence via frequency + recency
│   ┌───────────────┐  │
│   │ Pattern DB     │  │  Pattern: command + typical_time + confidence
│   └───────────────┘  │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  HabitSuggester      │  ◄── Context-aware ranking
│                      │       Time proximity + day match + location
└─────────┬───────────┘
          │
          ▼
    Ranked Suggestions
```

## Scoring

Confidence = `0.3 + 0.5 × (1 - e^(-frequency/5)) + 0.2 × (1/(1+age_days/30))`
Decay = `decay_rate ^ days_since_last` (applied daily)

## Usage

```python
from services.phase11_habit import HabitBrainService
svc = HabitBrainService()
await svc.initialize()

# Observe commands
await svc.observe("play music", intent="play_music", hour=9)
await svc.observe("play music", hour=9)

# Get suggestions for current context
suggestions = await svc.suggest(hour=9, day_of_week=0)
for s in suggestions:
    print(f"{s.command} (confidence={s.confidence}): {s.reason}")

# Approve or reject
await svc.approve(suggestions[0].pattern_id)
```

## Audit Log

All suggestions, approvals, and rejections are logged for review.
