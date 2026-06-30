# Phase 29: Automation Engine

## Purpose
Proactive intelligence system for scheduled goals, habit tracking, and daily automation. `AutomationSystem` runs as a background service that checks scheduled actions at their due times, tracks daily habits with streak calculations, generates daily summaries with insights and suggestions, and proactively reminds the user about overdue goals. Supports goal CRUD with progress tracking, habit frequency modes (daily/weekly/weekday), and simple cron expression scheduling.

## Architecture
```
AutomationSystem
  ├── start() / stop() — background loop
  ├── add_goal(title, category, priority, deadline) → Goal
  ├── update_goal_progress(id, progress) / complete_goal(id)
  ├── get_active_goals() / get_overdue_goals() / get_goal_summary()
  ├── add_habit(name, frequency, category) → Habit
  ├── complete_habit(id) → bool (streak tracking)
  ├── get_habits_due_today() / get_habit_streaks()
  ├── schedule_action(type, desc, cron, handler) → action_id
  ├── generate_daily_summary() → {goals, habits, suggestions, insights}
  └── get_stats()

  Background loop: _run_loop → _check_scheduled_actions → _check_overdue_goals → sleep check_interval
```

## Code
```python
class AutomationSystem:
    def add_goal(self, title, category="personal", priority="medium", deadline=None) -> Goal:
        goal = Goal(goal_id=f"goal_{uuid.uuid4().hex[:8]}", title=title, category=category, priority=priority)
        self._goals[goal.goal_id] = goal
        return goal

    def complete_habit(self, habit_id) -> bool:
        habit = self._habits.get(habit_id)
        if not habit or habit.last_completed == datetime.now().strftime("%Y-%m-%d"):
            return False
        habit.total_completions += 1
        habit.last_completed = datetime.now().strftime("%Y-%m-%d")
        self._update_streak(habit)
        return True

    def generate_daily_summary(self) -> Dict:
        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "goals": {"active": len(self.get_active_goals()), "overdue": len(self.get_overdue_goals())},
            "habits": {"due_today": len(self.get_habits_due_today()), "streaks": self.get_habit_streaks()[:3]},
            "suggestions": [f"{len(overdue)} goals are overdue!"] if overdue else [],
        }
```

## Location
`app/services/automation/` — automation system, goals, habits, scheduled actions
