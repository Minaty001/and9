"""
╔══════════════════════════════════════════════════╗
║        MICRO NEURAL BRAIN - METRICS TRACKER      ║
║   Self improvement through measurable data        ║
╚══════════════════════════════════════════════════╝
"""

import os
import json
import time
try:
    import psutil
except ImportError:  # pragma: no cover - optional in minimal envs
    psutil = None
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path

from config import BASE_DIR
from utils.logger import get_logger

logger = get_logger()


class MetricsTracker:
    """
    Tracks all performance metrics for the brain system.
    Monitors accuracy, response time, memory usage, etc.
    """

    def __init__(self, max_history=1000):
        self.max_history = max_history
        self.metrics_file = BASE_DIR / "metrics_history.json"

        # Runtime counters
        self.start_time = time.time()
        self.intent_count = 0
        self.action_count = 0
        self.success_count = 0
        self.failure_count = 0

        # Timing
        self.response_times = deque(maxlen=100)
        self.neural_inference_times = deque(maxlen=100)

        # Accuracy tracking
        self.prediction_history = deque(maxlen=500)
        self.confidence_scores = deque(maxlen=500)

        # Learning metrics
        self.habits_learned = 0
        self.habit_predictions = 0
        self.habit_accuracy = 0.0

        # Memory
        self.memory_count = 0

        # Neural network
        self.nn_accuracy = 0.0
        self.nn_loss_history = deque(maxlen=100)

        # Load saved state
        self._load()

    def _load(self):
        """Load metrics from disk."""
        try:
            if self.metrics_file.exists():
                data = json.loads(self.metrics_file.read_text())
                self.intent_count = data.get("intent_count", 0)
                self.action_count = data.get("action_count", 0)
                self.success_count = data.get("success_count", 0)
                self.failure_count = data.get("failure_count", 0)
                self.habits_learned = data.get("habits_learned", 0)
                logger.debug("Metrics loaded from disk")
        except (json.JSONDecodeError, IOError) as e:
            logger.debug(f"Could not load metrics: {e}")

    def _save(self):
        """Save metrics to disk."""
        try:
            data = {
                "intent_count": self.intent_count,
                "action_count": self.action_count,
                "success_count": self.success_count,
                "failure_count": self.failure_count,
                "habits_learned": self.habits_learned,
                "last_updated": datetime.now().isoformat(),
            }
            self.metrics_file.write_text(json.dumps(data, indent=2))
        except IOError as e:
            logger.debug(f"Could not save metrics: {e}")

    def log_intent(self, intent, confidence, correct=None):
        """Log an intent prediction."""
        self.intent_count += 1
        self.confidence_scores.append(confidence)
        if correct is not None:
            self.prediction_history.append(1 if correct else 0)
            if correct:
                self.success_count += 1
            else:
                self.failure_count += 1
            # Update running accuracy
            if len(self.prediction_history) > 0:
                self.nn_accuracy = sum(self.prediction_history) / len(self.prediction_history)
        self._save()

    def log_action(self, action, success=True, duration_ms=0):
        """Log an executed action."""
        self.action_count += 1
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
        self.response_times.append(duration_ms)
        self._save()

    def log_neural_inference(self, duration_ms):
        """Log neural network inference time."""
        self.neural_inference_times.append(duration_ms)

    def log_habit_learned(self):
        """Increment habit count."""
        self.habits_learned += 1
        self._save()

    def log_nn_loss(self, loss):
        """Log training loss."""
        self.nn_loss_history.append(loss)

    def set_memory_count(self, count):
        """Update memory count."""
        self.memory_count = count

    # ─── Getters ─────────────────────────────────────────────

    def get_accuracy(self):
        """Get overall accuracy."""
        if len(self.prediction_history) == 0:
            return 0.0
        return float(self.nn_accuracy)

    def get_average_response_time(self):
        """Get average response time in ms."""
        if len(self.response_times) == 0:
            return 0.0
        return sum(self.response_times) / len(self.response_times)

    def get_ram_usage_mb(self):
        """Get current process RAM usage in MB."""
        if psutil is None:
            return 0.0
        try:
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / (1024 * 1024)
        except (AttributeError, Exception):
            return 0.0

    def get_cpu_usage_percent(self):
        """Get current CPU usage percent."""
        if psutil is None:
            return 0.0
        try:
            process = psutil.Process(os.getpid())
            return process.cpu_percent(interval=0.1)
        except (AttributeError, Exception):
            return 0.0

    def get_uptime_seconds(self):
        """Get system uptime in seconds."""
        return time.time() - self.start_time

    def get_summary(self):
        """Get a summary dict of all metrics."""
        ram = self.get_ram_usage_mb()
        return {
            "accuracy": self.get_accuracy(),
            "avg_response_time_ms": self.get_average_response_time(),
            "ram_usage_mb": ram,
            "cpu_percent": self.get_cpu_usage_percent(),
            "intents_processed": self.intent_count,
            "actions_executed": self.action_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "memory_count": self.memory_count,
            "habits_learned": self.habits_learned,
            "uptime_seconds": self.get_uptime_seconds(),
            "nn_accuracy": float(self.nn_accuracy),
            "budget_remaining_mb": max(0, 50 - ram),
        }


# Global metrics instance
brain_metrics = MetricsTracker()


def get_metrics():
    """Get the global metrics tracker instance."""
    return brain_metrics
