"""
Phase 41 — CI Integrator.

Provides a full CI pipeline integration: runs all test suites, checks coverage
gates, and generates CI-friendly output (JUnit XML-like format).
"""

import time
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .test_runner import TestRunner
from .coverage_tracker import CoverageTracker
from .models import TestSuite, TestReport

logger = logging.getLogger(__name__)


class CiIntegrator:
    """Runs the full CI pipeline and checks quality gates.

    Usage:
        ci = CiIntegrator(runner, coverage)
        result = ci.run_ci_pipeline(suites)
        report = ci.generate_ci_report()
        passed = ci.check_gate()
    """

    def __init__(
        self,
        runner: TestRunner,
        coverage: CoverageTracker,
        fail_fast: bool = False,
    ):
        self._runner = runner
        self._coverage = coverage
        self._fail_fast = fail_fast
        self._last_result: Optional[Dict[str, Any]] = None
        self._pipeline_start: float = 0.0

    async def run_ci_pipeline(
        self,
        suites: List[TestSuite],
        parallel: bool = False,
    ) -> Dict[str, Any]:
        """Run the full CI pipeline: execute all suites and check coverage.

        Args:
            suites: List of test suites to run.
            parallel: Whether to run suites in parallel.

        Returns:
            Dict with pipeline status, reports, coverage, and gate result.
        """
        self._pipeline_start = time.time()
        logger.info(
            "CI pipeline started: %d suite(s), parallel=%s",
            len(suites), parallel,
        )

        # Run all test suites
        reports = await self._runner.run_all(suites, parallel=parallel)

        # Aggregate results
        total_tests = sum(r.total_tests for r in reports)
        total_passed = sum(r.passed for r in reports)
        total_failed = sum(r.failed for r in reports)
        total_skipped = sum(r.skipped for r in reports)
        total_duration = sum(r.duration_ms for r in reports)

        # Check coverage gate
        all_passed = total_failed == 0
        coverage_met = self._coverage.check_threshold()
        gate_passed = all_passed and coverage_met

        pipeline_duration = (time.time() - self._pipeline_start) * 1000

        self._last_result = {
            "status": "passed" if gate_passed else "failed",
            "pipeline_duration_ms": round(pipeline_duration, 2),
            "suites": len(suites),
            "total_tests": total_tests,
            "total_passed": total_passed,
            "total_failed": total_failed,
            "total_skipped": total_skipped,
            "total_duration_ms": round(total_duration, 2),
            "all_passed": all_passed,
            "coverage_met": coverage_met,
            "gate_passed": gate_passed,
            "reports": [r.model_dump() for r in reports],
            "coverage_report": self._coverage.generate_report(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        status = "PASSED" if gate_passed else "FAILED"
        logger.info(
            "CI pipeline %s: %d/%d passed, coverage_met=%s",
            status, total_passed, total_tests, coverage_met,
        )
        return self._last_result

    def generate_ci_report(self) -> str:
        """Generate a CI-friendly text report (JUnit XML-like).

        Returns:
            String report in a JUnit XML-like format.
        """
        if self._last_result is None:
            return "<testsuites/>"

        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<testsuites name="jarvis_ci_pipeline"',
            f'  tests="{self._last_result["total_tests"]}"',
            f'  failures="{self._last_result["total_failed"]}"',
            f'  time="{self._last_result["pipeline_duration_ms"] / 1000:.3f}">',
        ]

        for report_dict in self._last_result["reports"]:
            r = TestReport(**report_dict)
            lines.append(
                f'  <testsuite name="{r.suite_id}" tests="{r.total_tests}" '
                f'failures="{r.failed}" time="{r.duration_ms / 1000:.3f}">'
            )
            if r.failures:
                for f in r.failures:
                    lines.append(
                        f'    <testcase name="{f.get("name", f["test_id"])}" '
                        f'classname="{r.suite_id}">'
                    )
                    error_msg = f.get("error", "Unknown error")
                    lines.append(f"      <failure message=\"{error_msg}\"/>")
                    lines.append("    </testcase>")
            lines.append("  </testsuite>")

        lines.append("</testsuites>")
        return "\n".join(lines)

    def check_gate(self) -> bool:
        """Check if the quality gate passes.

        Gate requirements:
            1. All tests pass (zero failures)
            2. Coverage threshold met for all modules

        Returns:
            True if all conditions are met, False otherwise.
        """
        if self._last_result is None:
            # When no pipeline has run yet, check coverage only
            return self._coverage.check_threshold()
        return bool(self._last_result.get("gate_passed", False))

    def get_last_result(self) -> Optional[Dict[str, Any]]:
        """Return the most recent CI pipeline result."""
        return self._last_result
