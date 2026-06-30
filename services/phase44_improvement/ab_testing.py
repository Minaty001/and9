"""
Phase 44 — A/B Test Runner.

Creates A/B tests, records outcomes, analyzes results to determine winners,
and manages the test lifecycle.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .models import ABTest
from .config import ImprovementConfig

logger = logging.getLogger(__name__)


class ABTestRunner:
    """Manages A/B testing lifecycle.

    Usage:
        ab = ABTestRunner()
        test = ab.create_test("prompt-v1-vs-v2", {"prompt": "Hello"}, {"prompt": "Hi"}, "accuracy")
        ab.record_result(test.id, "A", {"score": 0.85})
        analysis = ab.analyze(test.id)
    """

    def __init__(self, config: Optional[ImprovementConfig] = None):
        self.config = config or ImprovementConfig()
        self._tests: Dict[str, ABTest] = {}

    def create_test(
        self,
        name: str,
        variant_a: Dict[str, Any],
        variant_b: Dict[str, Any],
        metric: str = "accuracy",
    ) -> ABTest:
        """Create a new A/B test.

        Args:
            name: Test name.
            variant_a: Control variant configuration.
            variant_b: Treatment variant configuration.
            metric: Metric to compare (e.g., "accuracy", "latency", "score").

        Returns:
            The created ABTest.
        """
        test_id = uuid.uuid4().hex[:12]
        test = ABTest(
            id=test_id,
            name=name,
            variant_a=variant_a,
            variant_b=variant_b,
            metric=metric,
            sample_size=0,
            results={"A": {"count": 0, "total": 0.0}, "B": {"count": 0, "total": 0.0}},
        )
        self._tests[test_id] = test
        logger.info("Created A/B test '%s' (metric=%s)", name, metric)
        return test

    def record_result(self, test_id: str, variant: str, outcome: Dict[str, Any]) -> bool:
        """Record an outcome for a variant.

        Args:
            test_id: Test ID.
            variant: "A" or "B".
            outcome: Dict with the metric value (e.g., {"score": 0.85}).

        Returns:
            True if recorded, False if test not found.
        """
        test = self._tests.get(test_id)
        if not test:
            return False

        variant = variant.upper()
        if variant not in ("A", "B"):
            return False

        metric_value = outcome.get(test.metric, outcome.get("score", 0))
        test.results.setdefault(variant, {"count": 0, "total": 0.0})
        test.results[variant]["count"] += 1
        test.results[variant]["total"] += float(metric_value)
        test.sample_size += 1
        return True

    def analyze(self, test_id: str) -> Dict[str, Any]:
        """Analyze test results and determine the winner.

        Compares the average of the metric between variant A and B.

        Args:
            test_id: Test ID.

        Returns:
            Dict with analysis results including winner if determinable.
        """
        test = self._tests.get(test_id)
        if not test:
            return {"error": f"Test not found: {test_id}"}

        res_a = test.results.get("A", {"count": 0, "total": 0.0})
        res_b = test.results.get("B", {"count": 0, "total": 0.0})

        avg_a = res_a["total"] / max(res_a["count"], 1)
        avg_b = res_b["total"] / max(res_b["count"], 1)

        analysis = {
            "test_id": test_id,
            "test_name": test.name,
            "metric": test.metric,
            "sample_size": test.sample_size,
            "variant_a_avg": round(avg_a, 4),
            "variant_b_avg": round(avg_b, 4),
            "variant_a_count": res_a["count"],
            "variant_b_count": res_b["count"],
            "difference": round(avg_b - avg_a, 4),
            "winner": None,
        }

        if res_a["count"] > 0 and res_b["count"] > 0:
            # Higher is better for most metrics; lower is better for latency
            if test.metric == "latency":
                analysis["winner"] = "A" if avg_a < avg_b else "B" if avg_b < avg_a else "tie"
            else:
                analysis["winner"] = "A" if avg_a > avg_b else "B" if avg_b > avg_a else "tie"

        return analysis

    def get_running_tests(self) -> List[ABTest]:
        """Get all tests that are still running (no winner declared yet)."""
        return [
            test for test in self._tests.values()
            if test.winner is None
        ]

    def complete_test(self, test_id: str) -> Optional[ABTest]:
        """Finalize a test by analyzing and declaring the winner.

        Args:
            test_id: Test ID.

        Returns:
            The finalized ABTest, or None if not found.
        """
        test = self._tests.get(test_id)
        if not test:
            return None

        analysis = self.analyze(test_id)
        if "winner" in analysis:
            test.winner = analysis["winner"]
        test.ended_at = datetime.now(timezone.utc)
        logger.info("Completed A/B test '%s': winner=%s", test.name, test.winner)
        return test
