"""
╔══════════════════════════════════════════════════╗
║           BRAIN 5: LEARNING BRAIN               ║
║   Pattern learning and habit discovery           ║
╚══════════════════════════════════════════════════╝

Purpose:
    Learn patterns from user behavior without expensive retraining.

Tracks:
    - Success/Failure rates
    - Frequency of actions
    - Time-based patterns
    - Day-of-week patterns
    - Habit formation and prediction

Uses:
    Lightweight statistics (no neural networks needed)
"""

import time
import math
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass, field
from threading import Lock

from config import LEARNING_CONFIG, INTENTS
from utils.logger import get_logger

logger = get_logger()


@dataclass
class Habit:
    """A learned habit pattern."""
    name: str
    pattern_type: str  # 'time', 'day', 'sequence', 'frequency'
    pattern_data: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    occurrences: int = 0
    last_triggered: Optional[str] = None
    enabled: bool = True


@dataclass
class Observation:
    """A single observed event for learning."""
    intent: str
    action: str
    timestamp: float
    success: bool
    duration_ms: float
    day_of_week: int
    hour: int
    context: Dict[str, Any] = field(default_factory=dict)


class LearningBrain:
    """
    Learning Brain - Discovers patterns and forms habits.

    Uses lightweight statistical learning to:
    1. Track action success/failure rates
    2. Discover time-based patterns
    3. Form habit predictions
    4. Learn user preferences over time
    """

    def __init__(self):
        self.observations: deque = deque(maxlen=10000)
        self.habits: Dict[str, Habit] = {}
        self._lock = Lock()

        # Frequency counters
        self._intent_frequency: Dict[str, int] = defaultdict(int)
        self._action_frequency: Dict[str, int] = defaultdict(int)
        self._hour_frequency: Dict[str, Dict[int, int]] = defaultdict(lambda: defaultdict(int))
        self._day_frequency: Dict[str, Dict[int, int]] = defaultdict(lambda: defaultdict(int))

        # Success tracking
        self._success_counts: Dict[str, int] = defaultdict(int)
        self._failure_counts: Dict[str, int] = defaultdict(int)

        # Sequence patterns (intent transitions)
        self._transitions: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._last_intent: Optional[str] = None

        self._prediction_cache: Dict[str, Any] = {}

    def observe(self, intent: str, action: str, success: bool,
                duration_ms: float = 0.0, context: Optional[Dict] = None) -> None:
        """
        Observe an action outcome for learning.

        This is the main input method for the learning brain.
        """
        now = datetime.now()
        obs = Observation(
            intent=intent,
            action=action,
            timestamp=time.time(),
            success=success,
            duration_ms=duration_ms,
            day_of_week=now.weekday(),
            hour=now.hour,
            context=context or {},
        )

        with self._lock:
            self.observations.append(obs)

            # Update frequencies
            self._intent_frequency[intent] += 1
            self._action_frequency[action] += 1
            self._hour_frequency[intent][now.hour] += 1
            self._day_frequency[intent][now.weekday()] += 1

            if success:
                self._success_counts[intent] += 1
            else:
                self._failure_counts[intent] += 1

            # Track transitions
            if self._last_intent and self._last_intent != intent:
                self._transitions[self._last_intent][intent] += 1
            self._last_intent = intent

        # Check for new habits periodically
        if len(self.observations) % 5 == 0:
            self._discover_habits()

    def predict_next_intent(self) -> Optional[Dict]:
        """
        Predict the most likely next intent based on learned patterns.

        Returns:
            Dict with predicted intent, confidence, and reasoning.
        """
        now = datetime.now()
        predictions = []

        # 1. Time-based prediction
        time_preds = self._predict_by_time(now.hour, now.weekday())
        if time_preds:
            predictions.extend(time_preds)

        # 2. Transition-based prediction (sequence)
        if self._last_intent:
            seq_pred = self._predict_by_sequence(self._last_intent)
            if seq_pred:
                predictions.append(seq_pred)

        # 3. Habit-based prediction
        habit_preds = self._predict_by_habit(now.hour, now.weekday())
        if habit_preds:
            predictions.extend(habit_preds)

        if not predictions:
            return None

        # Combine and rank predictions
        combined = defaultdict(lambda: {"confidence": 0.0, "sources": []})
        for pred in predictions:
            intent = pred["intent"]
            combined[intent]["confidence"] = max(
                combined[intent]["confidence"], pred["confidence"]
            )
            combined[intent]["sources"].append(pred["source"])

        # Find the best prediction
        best_intent = max(combined, key=lambda k: combined[k]["confidence"])
        best = combined[best_intent]

        if best["confidence"] >= LEARNING_CONFIG["prediction_confidence_threshold"]:
            return {
                "intent": best_intent,
                "confidence": best["confidence"],
                "sources": best["sources"],
            }

        return None

    def _predict_by_time(self, hour: int, day: int) -> List[Dict]:
        """Predict intent based on time of day and day of week."""
        predictions = []
        total_observations = len(self.observations)

        if total_observations < LEARNING_CONFIG["min_observations_for_habit"]:
            return predictions

        for intent in self._intent_frequency:
            hour_count = self._hour_frequency[intent].get(hour, 0)
            total_for_intent = self._intent_frequency[intent]

            if total_for_intent > 0 and hour_count > 1:
                # P(intent | hour) = count(intent, hour) / count(all, hour)
                all_at_hour = sum(
                    self._hour_frequency[i].get(hour, 0)
                    for i in self._intent_frequency
                )
                if all_at_hour > 0:
                    prob = hour_count / all_at_hour
                    if prob > 0.2:  # Minimum threshold
                        predictions.append({
                            "intent": intent,
                            "confidence": min(0.95, prob),
                            "source": "time_pattern",
                        })

        return predictions

    def _predict_by_sequence(self, last_intent: str) -> Optional[Dict]:
        """Predict next intent based on transition patterns."""
        transitions = self._transitions.get(last_intent, {})
        if not transitions:
            return None

        total = sum(transitions.values())
        best_next = max(transitions, key=transitions.get)
        prob = transitions[best_next] / total

        if prob > 0.3:  # Minimum confidence for sequence prediction
            return {
                "intent": best_next,
                "confidence": min(0.9, prob),
                "source": "sequence_pattern",
            }

        return None

    def _predict_by_habit(self, hour: int, day: int) -> List[Dict]:
        """Predict based on learned habits."""
        predictions = []
        for habit in self.habits.values():
            if not habit.enabled or habit.confidence < 0.3:
                continue

            if habit.pattern_type == "time":
                habit_hour = habit.pattern_data.get("hour")
                if habit_hour is not None and habit_hour == hour:
                    predictions.append({
                        "intent": habit.pattern_data.get("intent", ""),
                        "confidence": habit.confidence * 0.9,
                        "source": f"habit:{habit.name}",
                    })

        return predictions

    def _discover_habits(self):
        """Discover new habits from observation patterns."""
        with self._lock:
            # Time-based habit discovery
            self._discover_time_habits()
            # Frequency-based habit discovery
            self._discover_frequency_habits()

    def _discover_time_habits(self):
        """Discover habits based on time patterns."""
        for intent in self._intent_frequency:
            hour_counts = self._hour_frequency[intent]
            if not hour_counts:
                continue

            total = sum(hour_counts.values())
            if total < LEARNING_CONFIG["min_observations_for_habit"]:
                continue

            # Find the peak hour for this intent
            peak_hour = max(hour_counts, key=hour_counts.get)
            peak_ratio = hour_counts[peak_hour] / total

            if peak_ratio > 0.4:  # Strong time preference
                habit_name = f"{intent}_at_{peak_hour}h"
                if habit_name not in self.habits:
                    self.habits[habit_name] = Habit(
                        name=habit_name,
                        pattern_type="time",
                        pattern_data={
                            "intent": intent,
                            "hour": peak_hour,
                            "ratio": peak_ratio,
                        },
                        confidence=min(0.95, peak_ratio),
                        occurrences=hour_counts[peak_hour],
                    )
                    logger.info(
                        f"LearningBrain: New habit discovered: "
                        f"{intent} at {peak_hour}:00 (conf={peak_ratio:.2f})"
                    )

    def _discover_frequency_habits(self):
        """Discover habits based on overall frequency."""
        min_obs = LEARNING_CONFIG["min_observations_for_habit"]
        total = len(self.observations)

        for intent, count in self._intent_frequency.items():
            if count >= min_obs and total > 0:
                ratio = count / total
                if ratio > 0.3:  # Frequently used intent
                    habit_name = f"frequent_{intent}"
                    if habit_name not in self.habits:
                        self.habits[habit_name] = Habit(
                            name=habit_name,
                            pattern_type="frequency",
                            pattern_data={
                                "intent": intent,
                                "count": count,
                                "ratio": ratio,
                            },
                            confidence=min(0.9, ratio),
                            occurrences=count,
                        )
                        logger.info(
                            f"LearningBrain: Frequent habit: {intent} "
                            f"({count}x, {ratio:.1%})"
                        )

    def get_success_rate(self, intent: Optional[str] = None) -> float:
        """Get success rate for an intent or overall."""
        if intent:
            total = self._success_counts[intent] + self._failure_counts[intent]
            if total == 0:
                return 0.0
            return self._success_counts[intent] / total
        else:
            total_success = sum(self._success_counts.values())
            total = total_success + sum(self._failure_counts.values())
            if total == 0:
                return 0.0
            return total_success / total

    def get_intent_frequency(self, intent: str) -> float:
        """Get the frequency of a specific intent."""
        total = sum(self._intent_frequency.values())
        if total == 0:
            return 0.0
        return self._intent_frequency[intent] / total

    def get_frequent_intents(self, min_count: int = 2) -> List[Dict]:
        """Get most frequent intents."""
        return [
            {"intent": intent, "count": count}
            for intent, count in sorted(
                self._intent_frequency.items(),
                key=lambda x: x[1],
                reverse=True,
            )
            if count >= min_count
        ]

    def get_habits(self, min_confidence: float = 0.0) -> List[Dict]:
        """Get all learned habits."""
        return [
            {
                "name": h.name,
                "type": h.pattern_type,
                "data": h.pattern_data,
                "confidence": h.confidence,
                "occurrences": h.occurrences,
                "enabled": h.enabled,
            }
            for h in sorted(
                self.habits.values(),
                key=lambda x: x.confidence,
                reverse=True,
            )
            if h.confidence >= min_confidence
        ]

    def get_common_transitions(self, limit: int = 5) -> List[Dict]:
        """Get most common intent transitions."""
        transitions = []
        for from_intent, to_intents in self._transitions.items():
            total = sum(to_intents.values())
            for to_intent, count in to_intents.items():
                if count > 1:
                    transitions.append({
                        "from": from_intent,
                        "to": to_intent,
                        "count": count,
                        "probability": round(count / total, 2),
                    })

        return sorted(transitions, key=lambda x: x["count"], reverse=True)[:limit]

    def get_total_observations(self) -> int:
        """Get total observations made."""
        return len(self.observations)

    def get_hourly_heatmap(self) -> Dict[str, Dict[int, int]]:
        """Get hourly heatmap data for each intent."""
        heatmap = {}
        for intent, hours in self._hour_frequency.items():
            heatmap[intent] = dict(hours)
        return heatmap

    def get_stats(self) -> dict:
        """Get learning brain statistics."""
        total = len(self.observations)
        return {
            "total_observations": total,
            "habits_learned": len(self.habits),
            "unique_intents_seen": len(self._intent_frequency),
            "unique_actions_seen": len(self._action_frequency),
            "overall_success_rate": round(self.get_success_rate(), 3),
            "total_transitions": sum(
                sum(v.values()) for v in self._transitions.values()
            ),
            "active_habits": sum(1 for h in self.habits.values() if h.enabled),
        }
