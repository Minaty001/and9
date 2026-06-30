# Phase 26: Learning Engine

## Overview

Learns from user feedback, corrections, and repeated queries. Stores interaction patterns for preference learning, pattern recognition, and activity summarization.

## Architecture

```
User Feedback / Interactions
          │
          ▼
┌─────────────────────┐
│  PreferenceLearner   │  ◄── Learns user preferences from observations
│                      │       Supports context-aware retrieval
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│   PatternLearner     │  ◄── Recognizes recurring interaction patterns
│                      │       Matches by context, tracks success rate
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ ActivitySummarizer   │  ◄── Generates hourly/daily/weekly summaries
│                      │       Produces insights from observations
└─────────┬───────────┘
          │
          ▼
     Insights / Summaries
```

## Components

- **PreferenceLearner**: Observes user preferences, supports context-aware retrieval and forgetting
- **PatternLearner**: Records and matches interaction patterns by context, tracks success rates
- **ActivitySummarizer**: Generates period-based activity summaries with insights

## Usage

```python
from services.phase26_learning import LearningEngineService
svc = LearningEngineService()
await svc.initialize()

# Observe a preference
await svc.observe("theme", "color", "dark", {"time": "night"})

# Get preference
pref = await svc.get_preference("theme", "color")

# Record a pattern
await svc.record_pattern("morning", "play music", {"time": "08:00"})

# Generate summary
summary = await svc.generate_summary("daily")
print(summary.insights)
```
