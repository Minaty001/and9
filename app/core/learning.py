"""
app/core/learning.py — Pattern learning engine for AND9

Tracks user behaviour to provide better suggestions and
automate repetitive tasks.

What it learns:
  - Frequently used apps (top 10 tracked)
  - Typical alarm times ("user usually sets alarm at 7 AM")
  - Common phrases ("play music" -> user prefers YouTube)
  - User corrections (wrong answer -> store correction)
  - Command shortcuts ("YT" means "open YouTube")
"""

import logging
from collections import Counter, defaultdict
from typing import Dict, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class LearningEngine:
    def __init__(self, memory):
        self._mem = memory
        self._app_usage: Counter = Counter()
        self._command_patterns: Dict[str, int] = defaultdict(int)
        self._corrections: List[dict] = []

    def observe(self, query: str, intent: str,
                response: str, success: bool) -> None:
        """Record an interaction for learning."""
        self._command_patterns[intent] += 1

    def record_app_open(self, app_name: str) -> None:
        """Track which apps are opened most often."""
        self._app_usage[app_name] += 1

    def record_correction(self, wrong: str, correct: str,
                          query: str) -> None:
        """User corrected JARVIS — remember this."""
        self._corrections.append({
            "query": query, "wrong": wrong,
            "correct": correct,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    def get_frequent_apps(self, top_n: int = 5) -> List[str]:
        """Return top N most used apps."""
        return [app for app, _ in self._app_usage.most_common(top_n)]

    def get_patterns(self) -> Dict[str, int]:
        return dict(self._command_patterns)

    def suggest(self, context: dict) -> List[str]:
        """Suggest likely next actions based on context."""
        suggestions = []
        hour = datetime.now().hour
        if 6 <= hour <= 9:
            suggestions.append("Set morning alarm")
        frequent_apps = self.get_frequent_apps(3)
        for app in frequent_apps:
            suggestions.append(f"Open {app}")
        return suggestions