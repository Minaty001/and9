"""
╔══════════════════════════════════════════════════════════════╗
║           AUTOMATION SYSTEM — Proactive Intelligence         ║
║   Scheduled Goals | Habit Tracking | Daily Automation        ║
╚══════════════════════════════════════════════════════════════╝

The Automation System enables the AI to:
1. Track and manage scheduled goals
2. Monitor daily habits and streaks
3. Automate repetitive routines
4. Generate daily summaries and insights
5. Proactively suggest actions based on context

This runs as a background service, checking for automation
opportunities on a schedule.
"""

import logging
import time
import threading
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# SCHEDULED GOALS
# ═══════════════════════════════════════════════════════════════

@dataclass
class Goal:
    """A user goal with tracking."""
    goal_id: str
    title: str
    description: str = ""
    category: str = "personal"  # 'personal', 'work', 'fitness', 'learning', 'health'
    priority: str = "medium"    # 'high', 'medium', 'low'
    status: str = "active"      # 'active', 'paused', 'completed', 'cancelled'
    progress: float = 0.0       # 0.0 to 1.0
    created_at: float = 0.0
    deadline: Optional[float] = None
    completed_at: Optional[float] = None
    tags: List[str] = field(default_factory=list)
    reminders: List[str] = field(default_factory=list)  # Times for reminders
    streak: int = 0
    last_checked_in: Optional[float] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class Habit:
    """A tracked habit with streak data."""
    habit_id: str
    name: str
    description: str = ""
    frequency: str = "daily"  # 'daily', 'weekly', 'weekday', 'custom'
    category: str = "general"
    target_count: int = 1       # Times per frequency period
    current_streak: int = 0
    longest_streak: int = 0
    total_completions: int = 0
    last_completed: Optional[str] = None  # Date string YYYY-MM-DD
    streak_history: List[str] = field(default_factory=list)  # Track dates
    enabled: bool = True
    created_at: float = 0.0
    metadata: dict = field(default_factory=dict)


@dataclass
class ScheduledAction:
    """An action scheduled to run at a specific time."""
    action_id: str
    action_type: str        # 'reminder', 'goal_checkin', 'habit_check', 'routine'
    description: str
    cron_expression: str    # Simple format: "HH:MM" or "day:HH:MM"
    handler: Optional[Callable] = None
    enabled: bool = True
    last_run: Optional[float] = None
    next_run: Optional[float] = None
    metadata: dict = field(default_factory=dict)


class AutomationSystem:
    """Proactive automation and habit tracking system.

    Runs as a background service that:
    1. Checks scheduled actions at their due times
    2. Tracks daily habits and streaks
    3. Generates proactive reminders
    4. Creates daily summaries and insights
    """

    def __init__(
        self,
        check_interval: float = 60.0,  # Check every 60 seconds
        daily_reset_hour: int = 0,      # Reset at midnight
    ):
        self.check_interval = check_interval
        self.daily_reset_hour = daily_reset_hour

        self._lock = threading.RLock()
        self._goals: Dict[str, Goal] = {}
        self._habits: Dict[str, Habit] = {}
        self._scheduled_actions: Dict[str, ScheduledAction] = {}

        # Daily tracking
        self._current_date: str = ""
        self._daily_activity: Dict[str, Counter] = defaultdict(Counter)

        # Stats
        self._running = False
        self._checks_run = 0
        self._actions_triggered = 0
        self._reminders_sent = 0

        # Initialize with default scheduled actions
        self._init_defaults()

    def _init_defaults(self):
        """Set up default scheduled actions."""
        now = datetime.now()
        self._current_date = now.strftime("%Y-%m-%d")

    # ═══════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════

    def start(self):
        """Start the automation background thread."""
        if self._running:
            return
        self._running = True
        thread = threading.Thread(target=self._run_loop, daemon=True)
        thread.start()
        logger.info(f"AutomationSystem: Started (check_interval={self.check_interval}s)")

    def stop(self):
        """Stop the automation thread."""
        self._running = False

    # ═══════════════════════════════════════════════════════════════
    # GOAL MANAGEMENT
    # ═══════════════════════════════════════════════════════════════

    def add_goal(self, title: str, category: str = "personal",
                 priority: str = "medium", deadline: Optional[float] = None,
                 description: str = "") -> Goal:
        """Add a new goal."""
        import uuid
        goal = Goal(
            goal_id=f"goal_{uuid.uuid4().hex[:8]}",
            title=title,
            description=description,
            category=category,
            priority=priority,
            created_at=time.time(),
            deadline=deadline,
        )
        with self._lock:
            self._goals[goal.goal_id] = goal
        logger.info(f"Automation: New goal '{title}' [{category}/{priority}]")
        return goal

    def update_goal_progress(self, goal_id: str, progress: float) -> bool:
        """Update goal progress (0.0 to 1.0)."""
        with self._lock:
            goal = self._goals.get(goal_id)
            if not goal:
                return False
            goal.progress = min(1.0, max(0.0, progress))
            goal.last_checked_in = time.time()

            if goal.progress >= 1.0:
                goal.status = "completed"
                goal.completed_at = time.time()
                logger.info(f"Automation: Goal '{goal.title}' completed! 🎉")

            return True

    def complete_goal(self, goal_id: str) -> bool:
        """Mark a goal as completed."""
        return self.update_goal_progress(goal_id, 1.0)

    def get_active_goals(self) -> List[Goal]:
        """Get all active goals."""
        with self._lock:
            return [
                g for g in self._goals.values()
                if g.status == "active"
            ]

    def get_overdue_goals(self) -> List[Goal]:
        """Get goals past their deadline."""
        now = time.time()
        with self._lock:
            return [
                g for g in self._goals.values()
                if g.status == "active" and g.deadline and g.deadline < now
            ]

    def get_goals_by_category(self, category: str) -> List[Goal]:
        with self._lock:
            return [g for g in self._goals.values() if g.category == category]

    def get_goal_summary(self) -> str:
        """Generate a text summary of all goals."""
        with self._lock:
            active = [g for g in self._goals.values() if g.status == "active"]
            completed = [g for g in self._goals.values() if g.status == "completed"]
            overdue = self.get_overdue_goals()

        lines = []
        if active:
            lines.append(f"📋 **Active Goals ({len(active)}):**")
            for g in sorted(active, key=lambda x: x.priority):
                emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(g.priority, "•")
                deadline = ""
                if g.deadline:
                    remaining = g.deadline - time.time()
                    if remaining > 0:
                        deadline = f" ({int(remaining/86400)}d remaining)"
                    else:
                        deadline = " (⚠️ OVERDUE)"
                progress_bar = "▓" * int(g.progress * 10) + "░" * (10 - int(g.progress * 10))
                lines.append(f"  {emoji} **{g.title}** {progress_bar} {int(g.progress*100)}%{deadline}")
        if completed:
            lines.append(f"\n✅ **Completed:** {len(completed)} goals")
        if overdue:
            lines.append(f"\n⚠️ **Overdue:** {len(overdue)} goals need attention!")

        return "\n".join(lines) if lines else "No goals yet. Bolo kya karna hai! 🎯"

    # ═══════════════════════════════════════════════════════════════
    # HABIT TRACKING
    # ═══════════════════════════════════════════════════════════════

    def add_habit(self, name: str, description: str = "",
                  frequency: str = "daily", category: str = "general") -> Habit:
        """Add a new habit to track."""
        import uuid
        habit = Habit(
            habit_id=f"habit_{uuid.uuid4().hex[:8]}",
            name=name,
            description=description,
            frequency=frequency,
            category=category,
            created_at=time.time(),
        )
        with self._lock:
            self._habits[habit.habit_id] = habit
        logger.info(f"Automation: New habit '{name}' [{frequency}]")
        return habit

    def complete_habit(self, habit_id: str) -> bool:
        """Mark a habit as completed for today."""
        today = datetime.now().strftime("%Y-%m-%d")

        with self._lock:
            habit = self._habits.get(habit_id)
            if not habit:
                return False

            # Check if already completed today
            if habit.last_completed == today:
                return False

            # Update streaks
            habit.total_completions += 1
            habit.last_completed = today
            habit.streak_history.append(today)

            # Calculate current streak
            self._update_streak(habit)

            logger.info(f"Automation: Habit '{habit.name}' done! Streak: {habit.current_streak} 🔥")
            return True

    def _update_streak(self, habit: Habit):
        """Recalculate the current streak."""
        if not habit.streak_history:
            habit.current_streak = 0
            return

        dates = sorted(set(habit.streak_history), reverse=True)
        streak = 0
        check_date = datetime.now()

        for date_str in dates:
            try:
                date = datetime.strptime(date_str, "%Y-%m-%d")
                # Check if dates are consecutive
                if streak == 0:
                    if date_str == check_date.strftime("%Y-%m-%d") or \
                       date_str == (check_date - timedelta(days=1)).strftime("%Y-%m-%d"):
                        streak = 1
                        check_date = date
                    else:
                        break
                else:
                    expected = check_date - timedelta(days=1)
                    if date_str == expected.strftime("%Y-%m-%d"):
                        streak += 1
                        check_date = date
                    else:
                        break
            except ValueError:
                continue

        habit.current_streak = streak
        if streak > habit.longest_streak:
            habit.longest_streak = streak

    def get_habits_due_today(self) -> List[Habit]:
        """Get habits that are due today."""
        today = datetime.now().strftime("%Y-%m-%d")
        weekday = datetime.now().strftime("%A").lower()

        with self._lock:
            due = []
            for habit in self._habits.values():
                if not habit.enabled:
                    continue
                if habit.last_completed == today:
                    continue
                if habit.frequency == "daily":
                    due.append(habit)
                elif habit.frequency == "weekday" and weekday not in ("saturday", "sunday"):
                    due.append(habit)
                elif habit.frequency == "weekly":
                    # Check if completed this week
                    week_start = (datetime.now() - timedelta(days=datetime.now().weekday())).strftime("%Y-%m-%d")
                    if not any(d >= week_start for d in habit.streak_history):
                        due.append(habit)
            return due

    def get_habit_streaks(self) -> List[Dict]:
        """Get streak data for all habits."""
        with self._lock:
            return [
                {
                    "name": h.name,
                    "current_streak": h.current_streak,
                    "longest_streak": h.longest_streak,
                    "total_completions": h.total_completions,
                    "frequency": h.frequency,
                    "category": h.category,
                    "last_completed": h.last_completed,
                }
                for h in sorted(
                    self._habits.values(),
                    key=lambda x: x.current_streak,
                    reverse=True,
                )
            ]

    # ═══════════════════════════════════════════════════════════════
    # SCHEDULED ACTIONS
    # ═══════════════════════════════════════════════════════════════

    def schedule_action(self, action_type: str, description: str,
                         cron_expression: str, handler: Callable = None) -> str:
        """Schedule a recurring action.

        Args:
            action_type: Type of action.
            description: Human-readable description.
            cron_expression: When to run ("HH:MM" or "weekday:HH:MM").
            handler: Optional callable to execute.

        Returns:
            Action ID.
        """
        import uuid
        action_id = f"act_{uuid.uuid4().hex[:8]}"

        # Parse next run time
        next_run = self._parse_cron_next(cron_expression)

        action = ScheduledAction(
            action_id=action_id,
            action_type=action_type,
            description=description,
            cron_expression=cron_expression,
            handler=handler,
            next_run=next_run,
        )

        with self._lock:
            self._scheduled_actions[action_id] = action

        return action_id

    def _parse_cron_next(self, cron: str) -> Optional[float]:
        """Parse a simple cron expression and return next run timestamp.

        Supports: "HH:MM" or "weekday:HH:MM" or "daily:HH:MM"
        """
        now = datetime.now()
        parts = cron.split(":")

        try:
            if len(parts) == 2:
                # "HH:MM" — daily at this time
                hour, minute = int(parts[0]), int(parts[1])
                next_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if next_time <= now:
                    next_time += timedelta(days=1)
                return next_time.timestamp()

            elif len(parts) == 3:
                # "weekday:HH:MM" — specific weekday at this time
                weekday = parts[0].lower()
                hour, minute = int(parts[1]), int(parts[2])
                weekdays = ["monday", "tuesday", "wednesday", "thursday",
                           "friday", "saturday", "sunday"]

                target_day = weekdays.index(weekday) if weekday in weekdays else -1
                if target_day >= 0:
                    days_ahead = target_day - now.weekday()
                    if days_ahead <= 0 or (days_ahead == 0 and now.hour >= hour):
                        days_ahead += 7
                    next_time = (now + timedelta(days=days_ahead)).replace(
                        hour=hour, minute=minute, second=0, microsecond=0
                    )
                    return next_time.timestamp()

        except (ValueError, IndexError) as e:
            logger.warning(f"Automation: Invalid cron expression '{cron}': {e}")

        return None

    # ═══════════════════════════════════════════════════════════════
    # MAIN LOOP
    # ═══════════════════════════════════════════════════════════════

    def _run_loop(self):
        """Background automation loop."""
        while self._running:
            try:
                now = time.time()
                now_dt = datetime.now()

                # Check for date change (daily reset)
                today = now_dt.strftime("%Y-%m-%d")
                if today != self._current_date:
                    self._daily_reset(today)
                    self._current_date = today

                # Check scheduled actions
                self._check_scheduled_actions(now)

                # Check overdue goals
                self._check_overdue_goals()

                self._checks_run += 1
                time.sleep(self.check_interval)

            except Exception as e:
                logger.warning(f"AutomationSystem: Loop error: {e}")
                time.sleep(self.check_interval)

    def _daily_reset(self, new_date: str):
        """Reset daily counters and generate daily summary."""
        logger.info(f"AutomationSystem: Daily reset for {new_date}")
        # Generate summary for yesterday
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        if yesterday in self._daily_activity:
            activity = dict(self._daily_activity[yesterday])
            logger.info(f"Automation: Yesterday's activity: {activity}")

    def _check_scheduled_actions(self, now: float):
        """Check and trigger due scheduled actions."""
        with self._lock:
            due = [
                a for a in self._scheduled_actions.values()
                if a.enabled and a.next_run and a.next_run <= now
            ]

            for action in due:
                try:
                    if action.handler:
                        action.handler()
                    action.last_run = now
                    action.next_run = self._parse_cron_next(action.cron_expression)
                    self._actions_triggered += 1
                    logger.debug(f"Automation: Triggered '{action.description}'")
                except Exception as e:
                    logger.warning(f"Automation: Action '{action.description}' failed: {e}")

    def _check_overdue_goals(self):
        """Check for overdue goals and log warnings."""
        overdue = self.get_overdue_goals()
        if overdue:
            for goal in overdue:
                days_overdue = int((time.time() - goal.deadline) / 86400) if goal.deadline else 0
                logger.info(f"Automation: Goal '{goal.title}' is {days_overdue}d overdue!")

    # ═══════════════════════════════════════════════════════════════
    # DAILY SUMMARY
    # ═══════════════════════════════════════════════════════════════

    def generate_daily_summary(self) -> Dict:
        """Generate a complete daily summary.

        Includes:
        - Goals status
        - Habits status
        - Today's activity
        - Insights and suggestions
        """
        today = datetime.now().strftime("%Y-%m-%d")
        active_goals = self.get_active_goals()
        habits_due = self.get_habits_due_today()
        habit_streaks = self.get_habit_streaks()

        with self._lock:
            activity = dict(self._daily_activity.get(today, Counter()))

        suggestions = []

        # Suggest goals that need attention
        overdue = self.get_overdue_goals()
        if overdue:
            suggestions.append(f"⚠️ {len(overdue)} goals are overdue! Check them out.")

        # Suggest habits
        if habits_due:
            suggestions.append(f"📋 {len(habits_due)} habits still due today.")

        # Generate insights
        insights = []
        if habit_streaks:
            best = max(habit_streaks, key=lambda h: h["current_streak"])
            if best["current_streak"] >= 3:
                insights.append(f"🔥 '{best['name']}' streak: {best['current_streak']} days! Keep going!")

        return {
            "date": today,
            "goals": {
                "active": len(active_goals),
                "completed": len([g for g in self._goals.values() if g.status == "completed"]),
                "overdue": len(overdue),
            },
            "habits": {
                "total": len(self._habits),
                "due_today": len(habits_due),
                "streaks": habit_streaks[:3],
            },
            "activity_today": activity,
            "suggestions": suggestions[:5],
            "insights": insights[:5],
        }

    # ═══════════════════════════════════════════════════════════════
    # STATS
    # ═══════════════════════════════════════════════════════════════

    def get_stats(self) -> dict:
        with self._lock:
            return {
                "running": self._running,
                "checks_run": self._checks_run,
                "actions_triggered": self._actions_triggered,
                "goals": {
                    "total": len(self._goals),
                    "active": sum(1 for g in self._goals.values() if g.status == "active"),
                    "completed": sum(1 for g in self._goals.values() if g.status == "completed"),
                    "overdue": len(self.get_overdue_goals()),
                },
                "habits": {
                    "total": len(self._habits),
                    "enabled": sum(1 for h in self._habits.values() if h.enabled),
                },
                "scheduled_actions": len(self._scheduled_actions),
            }
