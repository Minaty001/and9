"""
╔══════════════════════════════════════════════════════════════╗
║           LEARNING SYSTEM — Continuous Self-Improvement      ║
║   Pattern Learning | Skill Learning | Preference Learning    ║
╚══════════════════════════════════════════════════════════════╝

The Learning System is the AI's ability to continuously improve
by learning from every interaction. Three subsystems:

1. PATTERN LEARNING — Detect recurring behaviors and routines
   - Usage patterns (time-based, day-based)
   - Command patterns (frequent queries, action sequences)
   - Context patterns (what the user does in specific contexts)

2. SKILL LEARNING — Convert successful workflows into reusable skills
   - Repeated task detection (same task done N times)
   - Workflow extraction (capture the steps)
   - Skill compilation (convert to reusable module)

3. PREFERENCE LEARNING — Learn user preferences over time
   - App preferences (which apps for which tasks)
   - Style preferences (communication, response format)
   - Schedule preferences (when user does what)
"""

import logging
import time
import json
import threading
from collections import defaultdict, Counter
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# PATTERN LEARNING
# ═══════════════════════════════════════════════════════════════

@dataclass
class UsagePattern:
    """A learned pattern of user behavior."""
    pattern_type: str  # 'time', 'day', 'sequence', 'frequency'
    key: str           # e.g., "hour:9", "sequence:open_app→play_music"
    action: str        # The action being performed
    count: int = 1
    confidence: float = 0.5
    last_seen: float = 0.0
    metadata: dict = field(default_factory=dict)


class PatternLearner:
    """Detects recurring patterns in user behavior.

    Tracks:
    - Time-based patterns (actions at specific hours)
    - Day-based patterns (actions on specific days)
    - Sequence patterns (action A → action B)
    - Frequency patterns (actions done N+ times)
    """

    def __init__(self, min_observations: int = 3):
        """Initialize the PatternLearner with observation thresholds.

        Sets up counters for hourly, daily, sequence, and frequency
        patterns, along with thread-safe locking.

        Args:
            min_observations: Minimum observations required before a
                pattern is considered valid (default: 3).
        """
        self.min_observations = min_observations
        self._lock = threading.Lock()

        # Raw observation counters
        self._hourly: Dict[str, Counter] = defaultdict(Counter)  # "hour:9" → {action: count}
        self._daily: Dict[str, Counter] = defaultdict(Counter)   # "day:Monday" → {action: count}
        self._sequences: Dict[str, Counter] = defaultdict(Counter)  # "prev_action" → {next_action: count}
        self._frequencies: Counter = Counter()  # action → total count

        # Learned patterns
        self._patterns: Dict[str, UsagePattern] = {}

        # Track last action for sequence detection
        self._last_action: Optional[str] = None
        self._total_observations: int = 0

    def observe(self, action: str, context: Optional[Dict] = None):
        """Record an action observation for pattern learning."""
        now = datetime.now()
        hour_key = f"hour:{now.hour}"
        day_key = f"day:{now.strftime('%A')}"

        with self._lock:
            self._hourly[hour_key][action] += 1
            self._daily[day_key][action] += 1
            self._frequencies[action] += 1
            self._total_observations += 1

            # Track sequences
            if self._last_action and self._last_action != action:
                seq_key = self._last_action
                self._sequences[seq_key][action] += 1
            self._last_action = action

            # Check for new patterns periodically
            if self._total_observations % 3 == 0:
                self._discover_patterns()

    def _discover_patterns(self):
        """Discover new patterns from accumulated observations."""
        # Time-based patterns
        for hour_key, action_counts in self._hourly.items():
            total = sum(action_counts.values())
            if total < self.min_observations:
                continue
            for action, count in action_counts.most_common(3):
                if count >= self.min_observations and count / total >= 0.3:
                    pattern_key = f"time:{hour_key}:{action}"
                    if pattern_key not in self._patterns:
                        self._patterns[pattern_key] = UsagePattern(
                            pattern_type="time",
                            key=hour_key,
                            action=action,
                            count=count,
                            confidence=min(0.95, count / total),
                            last_seen=time.time(),
                            metadata={"hour": int(hour_key.split(":")[1]), "occurrences": count},
                        )

        # Sequence patterns
        for prev_action, next_counts in self._sequences.items():
            total = sum(next_counts.values())
            if total < 2:
                continue
            for next_action, count in next_counts.most_common(2):
                if count >= 2 and count / total >= 0.3:
                    pattern_key = f"seq:{prev_action}→{next_action}"
                    if pattern_key not in self._patterns:
                        self._patterns[pattern_key] = UsagePattern(
                            pattern_type="sequence",
                            key=f"{prev_action}→{next_action}",
                            action=next_action,
                            count=count,
                            confidence=min(0.9, count / total),
                            last_seen=time.time(),
                            metadata={
                                "previous_action": prev_action,
                                "next_action": next_action,
                                "occurrences": count,
                            },
                        )

        # Frequency patterns
        total_obs = self._total_observations
        for action, count in self._frequencies.most_common(10):
            if count >= self.min_observations and count / total_obs >= 0.1:
                pattern_key = f"freq:{action}"
                if pattern_key not in self._patterns:
                    self._patterns[pattern_key] = UsagePattern(
                        pattern_type="frequency",
                        key=action,
                        action=action,
                        count=count,
                        confidence=min(0.9, count / total_obs),
                        last_seen=time.time(),
                        metadata={"occurrences": count, "ratio": round(count / total_obs, 3)},
                    )

    def predict(self, current_hour: int, current_day: str,
                last_action: Optional[str] = None) -> Optional[Dict]:
        """Predict the most likely next action based on learned patterns."""
        hour_key = f"hour:{current_hour}"

        predictions = []

        # Time-based prediction
        if hour_key in self._hourly:
            total = sum(self._hourly[hour_key].values())
            if total >= self.min_observations:
                for action, count in self._hourly[hour_key].most_common(3):
                    confidence = count / total
                    if confidence >= 0.3:
                        predictions.append({
                            "action": action, "confidence": confidence,
                            "source": "time_pattern", "occurrences": count,
                        })

        # Sequence prediction
        if last_action and last_action in self._sequences:
            total = sum(self._sequences[last_action].values())
            if total >= 2:
                for action, count in self._sequences[last_action].most_common(2):
                    confidence = count / total
                    if confidence >= 0.3:
                        predictions.append({
                            "action": action, "confidence": confidence,
                            "source": "sequence_pattern", "occurrences": count,
                        })

        if not predictions:
            return None

        # Pick highest confidence prediction
        best = max(predictions, key=lambda p: p["confidence"])
        return best

    def get_patterns(self, min_confidence: float = 0.0) -> List[Dict]:
        """Get all learned patterns."""
        return [
            {
                "type": p.pattern_type,
                "key": p.key,
                "action": p.action,
                "count": p.count,
                "confidence": round(p.confidence, 3),
                "metadata": p.metadata,
            }
            for p in sorted(
                self._patterns.values(),
                key=lambda x: x.confidence,
                reverse=True,
            )
            if p.confidence >= min_confidence and p.count >= self.min_observations
        ]

    def get_stats(self) -> dict:
        """Return summary statistics for the pattern learner.

        Returns:
            dict with keys:
                - total_observations: number of raw observations recorded
                - patterns_discovered: number of learned patterns
                - unique_actions: number of distinct actions observed
                - top_actions: list of (action, count) tuples for the 5 most
                  frequent actions.
        """
        return {
            "total_observations": self._total_observations,
            "patterns_discovered": len(self._patterns),
            "unique_actions": len(self._frequencies),
            "top_actions": self._frequencies.most_common(5),
        }


# ═══════════════════════════════════════════════════════════════
# SKILL LEARNING
# ═══════════════════════════════════════════════════════════════

@dataclass
class LearnedSkill:
    """A reusable skill learned from repeated successful workflows."""
    name: str
    description: str
    trigger_patterns: List[str]  # Keywords/phrases that trigger this skill
    steps: List[Dict]            # The execution steps
    success_count: int = 0
    failure_count: int = 0
    confidence: float = 0.5
    created_at: float = 0.0
    last_used: float = 0.0
    category: str = "general"
    metadata: dict = field(default_factory=dict)


class SkillLearner:
    """Learns reusable skills from repeated successful workflows.

    When the same task is performed N times successfully:
    1. Detect the pattern
    2. Extract the workflow steps
    3. Create a skill
    4. Register it for reuse

    Skills are stored in procedural memory for future use.
    """

    def __init__(self, min_repetitions: int = 3):
        """Initialize the SkillLearner with repetition threshold.

        Sets up task history storage, a skills registry, and
        thread-safe locking.  Procedural memory attachment is
        deferred for external wiring.

        Args:
            min_repetitions: Minimum successful repetitions before a
                workflow is promoted to a skill (default: 3).
        """
        self.min_repetitions = min_repetitions
        self._lock = threading.Lock()
        self._task_history: Dict[str, List[Dict]] = defaultdict(list)  # task_key → [executions]
        self._skills: Dict[str, LearnedSkill] = {}
        self._procedural_memory = None  # Set externally

    def observe(self, ctx) -> Optional[LearnedSkill]:
        """Observe a task execution. Returns a new skill if learned."""
        action = ctx.detected_intent or ctx.detected_action or "unknown"
        query = ctx.raw_input.lower().strip()

        if not action or action in ("unknown", "chat"):
            return None

        with self._lock:
            # Extract task key from the action and query
            task_key = self._extract_task_key(action, query)

            # Record this execution
            execution = {
                "timestamp": time.time(),
                "action": action,
                "query": query,
                "success": ctx.success,
                "parameters": ctx.parameters,
                "brain_used": ctx.processing_level.value,
            }
            self._task_history[task_key].append(execution)

            # Check if we have enough successful repetitions
            records = self._task_history[task_key]
            successful = [r for r in records if r["success"]]

            if len(successful) >= self.min_repetitions and task_key not in self._skills:
                return self._create_skill(task_key, successful)

            return None

    def _extract_task_key(self, action: str, query: str) -> str:
        """Extract a task key from action and query."""
        # For open_app actions, use the app name
        if action == "open_app" or action == "LAUNCH_APP":
            for word in query.split():
                if word not in ("open", "kholo", "launch", "start", "chalao", "karo"):
                    return f"open_{word}"
            return f"open_{action}"

        # For other actions, use action name directly
        return action

    def _create_skill(self, task_key: str, executions: List[Dict]) -> LearnedSkill:
        """Create a skill from repeated successful executions."""
        latest = executions[-1]
        action = latest["action"]

        # Determine trigger patterns from queries
        trigger_patterns = list(set(
            e["query"] for e in executions[-5:]
        ))

        # Extract steps from the execution pattern
        steps = [{
            "type": "action",
            "action": action,
            "parameters": latest.get("parameters", {}),
        }]

        skill = LearnedSkill(
            name=f"skill_{task_key}",
            description=f"Automated: {task_key}",
            trigger_patterns=trigger_patterns,
            steps=steps,
            success_count=len(executions),
            confidence=min(0.95, len(executions) / (len(executions) + 2)),
            created_at=time.time(),
            last_used=time.time(),
            category=self._categorize(action),
        )

        self._skills[task_key] = skill
        logger.info(f"SkillLearner: New skill '{skill.name}' ({skill.confidence:.2f}) from {len(executions)} repetitions")

        # Store in procedural memory if available
        if self._procedural_memory:
            try:
                self._procedural_memory.store_skill(skill)
            except Exception as e:
                logger.warning(f"SkillLearner: Failed to store skill: {e}")

        return skill

    def _categorize(self, action: str) -> str:
        """Categorize a skill based on action type."""
        action_lower = action.lower()
        if "app" in action_lower or "launch" in action_lower or "open" in action_lower:
            return "app_control"
        if "music" in action_lower or "play" in action_lower:
            return "media"
        if "call" in action_lower or "message" in action_lower:
            return "communication"
        if "alarm" in action_lower or "reminder" in action_lower or "timer" in action_lower:
            return "time_management"
        if "flash" in action_lower or "wifi" in action_lower or "bluetooth" in action_lower:
            return "device_control"
        return "general"

    def get_skills(self, category: Optional[str] = None) -> List[Dict]:
        """Get all learned skills."""
        skills = []
        for skill in self._skills.values():
            if category and skill.category != category:
                continue
            skills.append({
                "name": skill.name,
                "description": skill.description,
                "confidence": round(skill.confidence, 3),
                "success_count": skill.success_count,
                "category": skill.category,
                "trigger_patterns": skill.trigger_patterns[:3],
                "last_used": skill.last_used,
            })
        return sorted(skills, key=lambda s: s["confidence"], reverse=True)

    def get_stats(self) -> dict:
        """Return summary statistics for the skill learner.

        Returns:
            dict with keys:
                - skills_learned: number of skills created
                - tasks_tracked: number of distinct task keys observed
                - total_executions: total number of task execution
                  records across all task keys.
        """
        return {
            "skills_learned": len(self._skills),
            "tasks_tracked": len(self._task_history),
            "total_executions": sum(len(v) for v in self._task_history.values()),
        }


# ═══════════════════════════════════════════════════════════════
# PREFERENCE LEARNING
# ═══════════════════════════════════════════════════════════════

@dataclass
class UserPreference:
    """A learned user preference."""
    key: str
    value: Any
    category: str  # 'app', 'style', 'schedule', 'general'
    confidence: float = 0.5
    observations: int = 1
    first_seen: float = 0.0
    last_updated: float = 0.0


class PreferenceLearner:
    """Learns user preferences over time from behavior patterns.

    Learns:
    - Which apps the user prefers for different tasks
    - Communication style preferences
    - Schedule preferences (when user does what)
    - General preferences (likes, dislikes, favorites)
    """

    def __init__(self):
        """Initialize the PreferenceLearner with empty stores.

        Sets up thread-safe storage for learned preferences and raw
        observation counters used to compute confidence scores.
        """
        self._lock = threading.Lock()
        self._preferences: Dict[str, UserPreference] = {}
        self._observations: Dict[str, Counter] = defaultdict(Counter)  # key → {value: count}

    def observe_action(self, ctx) -> Optional[UserPreference]:
        """Learn preferences from action context.

        Returns a new preference if one was learned.
        """
        action = ctx.detected_intent or ctx.detected_action or ""

        with self._lock:
            now = time.time()

            # Learn app preferences
            if "open_app" in action or "LAUNCH_APP" in action:
                app_name = self._extract_app_name(ctx.raw_input, ctx.parameters)
                if app_name:
                    pref_key = "preferred_app"
                    self._observations[pref_key][app_name] += 1
                    return self._update_preference(pref_key, app_name, "app", now)

            # Learn media preferences
            if "music" in action.lower() or "play" in action.lower():
                query = ctx.raw_input.lower()
                for mood in ["soft", "sad", "romantic", "party", "ghazal", "bhajan", "lofi", "punjabi"]:
                    if mood in query:
                        pref_key = "music_mood"
                        self._observations[pref_key][mood] += 1
                        return self._update_preference(pref_key, mood, "media", now)

            # Learn time-based preferences (when user does what)
            hour = datetime.now().hour
            if action:
                pref_key = "peak_hour"
                self._observations[pref_key][str(hour)] += 1
                return self._update_preference(pref_key, str(hour), "schedule", now)

        return None

    def _extract_app_name(self, query: str, params: dict) -> Optional[str]:
        """Extract app name from query or parameters."""
        if params and params.get("app_name"):
            return params["app_name"]

        # Try to extract from query
        query = query.lower().strip()
        for prefix in ["open ", "kholo ", "launch ", "chalao "]:
            if query.startswith(prefix):
                name = query[len(prefix):].strip()
                if name and len(name) < 30:
                    return name
        return None

    def _update_preference(self, key: str, value: str,
                            category: str, now: float) -> Optional[UserPreference]:
        """Update or create a preference based on observations."""
        counter = self._observations[key]
        total = sum(counter.values())
        current_value = counter.most_common(1)[0][0]
        current_count = counter.most_common(1)[0][1]

        # Need minimum observations for confident preference
        if total < 2:
            return None

        confidence = min(0.95, current_count / total)

        if key in self._preferences:
            pref = self._preferences[key]
            if pref.value != current_value or abs(pref.confidence - confidence) > 0.05:
                pref.value = current_value
                pref.confidence = confidence
                pref.observations = current_count
                pref.last_updated = now
                return pref
        else:
            pref = UserPreference(
                key=key,
                value=current_value,
                category=category,
                confidence=confidence,
                observations=current_count,
                first_seen=now,
                last_updated=now,
            )
            self._preferences[key] = pref
            logger.info(f"PreferenceLearner: New preference '{key}' = '{current_value}' (conf={confidence:.2f})")
            return pref

        return None

    def get_preferences(self, category: Optional[str] = None) -> List[Dict]:
        """Get all learned preferences."""
        prefs = []
        for pref in self._preferences.values():
            if category and pref.category != category:
                continue
            prefs.append({
                "key": pref.key,
                "value": pref.value,
                "category": pref.category,
                "confidence": round(pref.confidence, 3),
                "observations": pref.observations,
            })
        return sorted(prefs, key=lambda p: p["confidence"], reverse=True)

    def get(self, key: str, default=None):
        """Get a preference value by key."""
        pref = self._preferences.get(key)
        return pref.value if pref else default

    def get_stats(self) -> dict:
        """Return summary statistics for the preference learner.

        Returns:
            dict with keys:
                - preferences_learned: number of distinct preferences
                - total_observations: aggregate count across all
                  preference observation counters
                - categories: list of unique preference categories
                  (e.g. 'app', 'media', 'schedule').
        """
        return {
            "preferences_learned": len(self._preferences),
            "total_observations": sum(sum(c.values()) for c in self._observations.values()),
            "categories": list(set(p.category for p in self._preferences.values())),
        }


# ═══════════════════════════════════════════════════════════════
# UNIFIED LEARNING SYSTEM
# ═══════════════════════════════════════════════════════════════

class LearningSystem:
    """Unified learning system combining pattern, skill, and preference learning.

    This is the main entry point for all learning in the cognitive architecture.
    Every action flows through this system, enabling continuous improvement.
    """

    def __init__(self, enable_all: bool = True):
        """Initialize the unified LearningSystem.

        Creates the three sub-learners (pattern, skill, preference)
        only when ``enable_all`` is True, allowing callers to
        selectively disable learning subsystems.

        Args:
            enable_all: If True, all three learners are instantiated.
                If False, all are set to None and learning is
                effectively disabled.
        """
        self.pattern_learner = PatternLearner() if enable_all else None
        self.skill_learner = SkillLearner() if enable_all else None
        self.preference_learner = PreferenceLearner() if enable_all else None
        self.enabled = enable_all

        # Stats
        self._stats = {"total_learning_events": 0}

    def observe(self, ctx) -> Dict:
        """Process an action through all learning subsystems.

        Called after every action execution. Runs all learners
        in parallel to extract patterns, skills, and preferences.

        Args:
            ctx: CognitiveContext from the action execution.

        Returns:
            Dict with any new learnings.
        """
        if not self.enabled:
            return {"learned": False}

        learnings = {"patterns": [], "skills": [], "preferences": []}
        action = ctx.detected_intent or ctx.detected_action or "unknown"

        try:
            # 1. Pattern learning
            if self.pattern_learner:
                self.pattern_learner.observe(action, {"query": ctx.raw_input})
                prediction = self.pattern_learner.predict(
                    datetime.now().hour,
                    datetime.now().strftime("%A"),
                    action,
                )
                if prediction:
                    learnings["patterns"].append(prediction)

            # 2. Skill learning
            if self.skill_learner:
                new_skill = self.skill_learner.observe(ctx)
                if new_skill:
                    learnings["skills"].append({
                        "name": new_skill.name,
                        "confidence": new_skill.confidence,
                    })

            # 3. Preference learning
            if self.preference_learner:
                new_pref = self.preference_learner.observe_action(ctx)
                if new_pref:
                    learnings["preferences"].append({
                        "key": new_pref.key,
                        "value": new_pref.value,
                        "confidence": new_pref.confidence,
                    })

            self._stats["total_learning_events"] += 1

        except Exception as e:
            logger.warning(f"LearningSystem: Error during learning: {e}")

        return learnings

    def get_stats(self) -> dict:
        """Return aggregate statistics from all learning subsystems.

        Merges the top-level event counter with per-learner stats
        from the pattern, skill, and preference learners (if they
        are enabled).

        Returns:
            dict containing 'total_learning_events' and optionally
            'patterns', 'skills', and 'preferences' sub-dicts.
        """
        stats = {**self._stats}
        if self.pattern_learner:
            stats["patterns"] = self.pattern_learner.get_stats()
        if self.skill_learner:
            stats["skills"] = self.skill_learner.get_stats()
        if self.preference_learner:
            stats["preferences"] = self.preference_learner.get_stats()
        return stats

    def get_all_learnings(self) -> Dict:
        """Get all accumulated learnings."""
        return {
            "patterns": self.pattern_learner.get_patterns(min_confidence=0.3) if self.pattern_learner else [],
            "skills": self.skill_learner.get_skills() if self.skill_learner else [],
            "preferences": self.preference_learner.get_preferences() if self.preference_learner else [],
        }

    # ── Phase 26 convenience methods ─────────────────────────────
    # These provide the phase26-style API on the existing app learners.

    def observe_preference(self, category: str, key: str, value: Any, **kwargs) -> Optional[Dict]:
        """Convenience: observe a preference (phase26-style).

        Args:
            category: Preference category.
            key: Preference key.
            value: The preferred value.
            **kwargs: Ignored extra kwargs for API compatibility.

        Returns:
            Preference dict if learned, None otherwise.
        """
        if not self.preference_learner:
            return None
        # Use a simple mock context to satisfy the existing API
        class MockCtx:
            def __init__(self, action, query):
                self.detected_intent = action
                self.detected_action = action
                self.raw_input = query
                self.parameters = {"app_name": value} if "app" in category else {}
                self.success = True
                self.processing_level = type("Level", (), {"value": "normal"})()

        ctx = MockCtx(key, str(value))
        pref = self.preference_learner.observe_action(ctx)
        if pref:
            return {"key": pref.key, "value": pref.value, "confidence": pref.confidence, "category": pref.category}
        return None

    def forget_preference(self, category: str, key: str) -> bool:
        """Forget a learned preference (phase26-style).

        Args:
            category: Preference category (unused, kept for API compat).
            key: Preference key to forget.

        Returns:
            True if forgotten.
        """
        if not self.preference_learner:
            return False
        # Remove from preferences dict
        removed = False
        for cat_prefs in list(self.preference_learner._preferences.keys()):
            if key in self.preference_learner._preferences:
                del self.preference_learner._preferences[key]
                removed = True
        return removed

    def record_pattern(self, trigger: str, action: str, **kwargs) -> Optional[Dict]:
        """Convenience: record a pattern observation (phase26-style).

        Args:
            trigger: The trigger condition.
            action: The action taken.
            **kwargs: Ignored extra kwargs for API compatibility.

        Returns:
            Pattern dict if recorded, None otherwise.
        """
        if not self.pattern_learner:
            return None
        # Use the existing observe method
        self.pattern_learner.observe(action, {"trigger": trigger, **kwargs})
        return {"trigger": trigger, "action": action}

    def find_patterns(self, context: Dict[str, Any]) -> List[Dict]:
        """Find patterns matching context (phase26-style).

        Args:
            context: Context dict.

        Returns:
            List of matching pattern dicts.
        """
        if not self.pattern_learner:
            return []
        hour = context.get("hour", datetime.now().hour)
        day = context.get("day", datetime.now().strftime("%A"))
        last_action = context.get("last_action")
        prediction = self.pattern_learner.predict(hour, day, last_action)
        if prediction:
            return [prediction]
        return []


# ═══════════════════════════════════════════════════════════════
# ACTIVITY SUMMARIZER  (Phase 26)
# ═══════════════════════════════════════════════════════════════

@dataclass
class ActivitySummary:
    """A summary of activity over a period."""

    period: str  # hourly/daily/weekly
    start_time: datetime = field(default_factory=lambda: datetime.now())
    end_time: datetime = field(default_factory=lambda: datetime.now())
    total_interactions: int = 0
    top_intents: List[Dict] = field(default_factory=list)
    top_entities: List[Dict] = field(default_factory=list)
    avg_confidence: float = 0.0
    top_queries: List[Dict] = field(default_factory=list)
    insights: List[str] = field(default_factory=list)


class ActivitySummarizer:
    """Generates activity summaries from observations.

    Summarizes interactions, intents, entities, and produces insights
    over hourly, daily, or weekly periods.

    Usage:
        summarizer = ActivitySummarizer()
        summarizer.add_observation("query", "preference", {"intent": "greeting"})
        summary = summarizer.generate_summary("daily")
    """

    def __init__(self):
        self._observations: List[Dict] = []

    def add_observation(
        self,
        observation_type: str,
        category: str,
        context: Optional[Dict] = None,
        confidence: float = 1.0,
    ) -> None:
        """Add an observation for future summarization.

        Args:
            observation_type: Type of observation (e.g., "preference", "pattern").
            category: Observation category.
            context: Context dict (may include "intent", "entity", "query").
            confidence: Confidence score.
        """
        obs = {
            "type": observation_type,
            "category": category,
            "context": context or {},
            "confidence": confidence,
            "timestamp": datetime.now(timezone.utc),
        }
        self._observations.append(obs)
        # Keep bounded
        if len(self._observations) > 50000:
            self._observations = self._observations[-25000:]

    def generate_summary(self, period: str = "daily") -> ActivitySummary:
        """Generate an activity summary for the given period.

        Args:
            period: Summary period: "hourly", "daily", or "weekly".

        Returns:
            An ActivitySummary instance.
        """
        now = datetime.now(timezone.utc)

        if period == "hourly":
            start_time = now - timedelta(hours=1)
        elif period == "weekly":
            start_time = now - timedelta(weeks=1)
        else:  # daily
            start_time = now - timedelta(days=1)

        # Filter observations in the period
        period_obs = [o for o in self._observations if start_time <= o["timestamp"] <= now]

        # Count by type
        type_counts = Counter(o["type"] for o in period_obs)

        # Top intents
        intents = [o["context"].get("intent", o["type"]) for o in period_obs]
        intent_counts = Counter(intents)

        # Top entities
        entities = [o["context"].get("entity", "") for o in period_obs if o["context"].get("entity")]
        entity_counts = Counter(entities)

        # Top queries
        queries = [o["context"].get("query", "") for o in period_obs if o["context"].get("query")]
        query_counts = Counter(queries)

        # Average confidence
        avg_conf = sum(o["confidence"] for o in period_obs) / len(period_obs) if period_obs else 0.0

        # Generate insights
        insights = self._generate_insights(period_obs, period, intent_counts, query_counts)

        return ActivitySummary(
            period=period,
            start_time=start_time,
            end_time=now,
            total_interactions=len(period_obs),
            top_intents=[{"intent": k, "count": v} for k, v in intent_counts.most_common(5)],
            top_entities=[{"entity": k, "count": v} for k, v in entity_counts.most_common(5)],
            avg_confidence=round(avg_conf, 3),
            top_queries=[{"query": k, "count": v} for k, v in query_counts.most_common(5)],
            insights=insights,
        )

    def get_observation_count(self) -> int:
        """Return total observation count."""
        return len(self._observations)

    def clear(self) -> None:
        """Clear all observations."""
        self._observations.clear()

    def _generate_insights(
        self,
        observations: List[Dict],
        period: str,
        intent_counts: Counter,
        query_counts: Counter,
    ) -> List[str]:
        """Generate human-readable insights from observations.

        Args:
            observations: Observations in the period.
            period: Period string.
            intent_counts: Counter of intents.
            query_counts: Counter of queries.

        Returns:
            List of insight strings.
        """
        insights = []

        if not observations:
            insights.append(f"No activity detected in the last {period}.")
            return insights

        insights.append(f"Total interactions: {len(observations)} in the last {period}.")

        if intent_counts:
            top_intent = intent_counts.most_common(1)[0]
            insights.append(f"Most frequent intent: '{top_intent[0]}' ({top_intent[1]} times).")

        if query_counts:
            insights.append(f"Top query: '{query_counts.most_common(1)[0][0]}'.")

        # Check for new topics (observed only once)
        new_topics = [q for q, c in query_counts.most_common() if c <= 2]
        if new_topics:
            insights.append(f"New topics detected: {len(new_topics)}.")

        return insights
