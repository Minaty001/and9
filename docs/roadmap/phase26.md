# Phase 26: Learning Engine

## Purpose
Continuous self-improvement through pattern learning, skill learning, and preference learning from every interaction. `PatternLearner` detects recurring user behaviors (time-based, day-based, sequence, frequency). `SkillLearner` converts repeated successful workflows into reusable skills. `PreferenceLearner` learns user preferences over time (apps, music mood, schedule). `LearningSystem` unifies all three subsystems as the main entry point. `ActivitySummarizer` generates hourly/daily/weekly activity summaries with insights.

## Architecture
```
LearningSystem
  ├── observe(ctx) — process action through all learners in parallel
  ├── get_all_learnings() → {patterns, skills, preferences}
  ├── get_stats()
  │
  ├── PatternLearner
  │     ├── observe(action, context) — record observation
  │     ├── predict(hour, day, last_action) → best action prediction
  │     └── get_patterns(min_confidence) → List[UsagePattern]
  │
  ├── SkillLearner
  │     ├── observe(ctx) → Optional[LearnedSkill]
  │     └── get_skills(category) → List[LearnedSkill]
  │
  └── PreferenceLearner
        ├── observe_action(ctx) → Optional[UserPreference]
        └── get_preferences(category) → List[UserPreference]

ActivitySummarizer
  ├── add_observation(type, category, context, confidence)
  └── generate_summary(period) → ActivitySummary
```

## Code
```python
class PatternLearner:
    def observe(self, action, context=None):
        now = datetime.now()
        self._hourly[f"hour:{now.hour}"][action] += 1
        self._daily[f"day:{now.strftime('%A')}"][action] += 1
        self._frequencies[action] += 1

    def predict(self, current_hour, current_day, last_action=None):
        hour_key = f"hour:{current_hour}"
        if hour_key in self._hourly:
            total = sum(self._hourly[hour_key].values())
            for action, count in self._hourly[hour_key].most_common(3):
                if count / total >= 0.3:
                    return {"action": action, "confidence": count / total, "source": "time_pattern"}
        return None

class LearningSystem:
    def observe(self, ctx) -> Dict:
        learnings = {"patterns": [], "skills": [], "preferences": []}
        if self.pattern_learner:
            self.pattern_learner.observe(action, {"query": ctx.raw_input})
        if self.skill_learner:
            new_skill = self.skill_learner.observe(ctx)
        if self.preference_learner:
            new_pref = self.preference_learner.observe_action(ctx)
        return learnings
```

## Location
`app/core/learning_system.py` — pattern, skill, preference learners, learning system, and activity summarizer
