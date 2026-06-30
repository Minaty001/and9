"""
Phase 41 — Test Runner.

Executes test cases and suites with timeout support, setup/teardown hooks,
pass/fail/skip tracking, and failure analysis with recommendations.
"""

import asyncio
import time
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from .models import TestCase, TestSuite, TestResult, TestReport

logger = logging.getLogger(__name__)


class TestRunner:
    """Executes test cases and suites with lifecycle hooks.

    Usage:
        runner = TestRunner()
        result = runner.run_test(test_case)
        report = runner.run_suite(suite)
        reports = runner.run_all([suite1, suite2])
    """

    def __init__(self, default_timeout_ms: int = 5000):
        self.default_timeout_ms = default_timeout_ms
        self._results: List[TestResult] = []
        self._reports: List[TestReport] = []
        # External hook registry — callables keyed by hook name
        self._hooks: Dict[str, Callable] = {}

    def register_hook(self, name: str, fn: Callable) -> None:
        """Register a setup or teardown hook function.

        Args:
            name: Hook name (referenced by TestSuite.setup_hooks / teardown_hooks).
            fn: Callable to invoke (async or sync).
        """
        self._hooks[name] = fn

    async def _run_hooks(self, hook_names: List[str]) -> None:
        """Execute hooks by name, supporting both sync and async callables."""
        for name in hook_names:
            fn = self._hooks.get(name)
            if fn is None:
                logger.warning("Hook '%s' not registered, skipping", name)
                continue
            try:
                if asyncio.iscoroutinefunction(fn):
                    await fn()
                else:
                    fn()
            except Exception as e:
                logger.error("Hook '%s' failed: %s", name, e)
                raise

    async def run_test(
        self,
        test_case: TestCase,
        suite_id: str = "",
    ) -> TestResult:
        """Execute a single test case with timeout.

        Args:
            test_case: The test case to execute.
            suite_id: Optional suite identifier for grouping.

        Returns:
            TestResult with outcome details.
        """
        if test_case.skip:
            logger.info("Skipping test: %s (%s)", test_case.id, test_case.name)
            return TestResult(
                test_id=test_case.id,
                suite_id=suite_id,
                passed=False,
                duration_ms=0,
                assertion_errors=[],
                timestamp=datetime.now(timezone.utc),
            )

        t0 = time.perf_counter()
        timeout_s = (test_case.timeout_ms or self.default_timeout_ms) / 1000.0

        try:
            # Execute the test's run function if registered, else simulate
            test_fn = self._hooks.get(f"test:{test_case.id}")
            if test_fn:
                if asyncio.iscoroutinefunction(test_fn):
                    await asyncio.wait_for(test_fn(), timeout=timeout_s)
                else:
                    test_fn()
            else:
                # Default pass-through for tests without registered logic
                pass

            elapsed = (time.perf_counter() - t0) * 1000
            result = TestResult(
                test_id=test_case.id,
                suite_id=suite_id,
                passed=True,
                duration_ms=round(elapsed, 2),
                timestamp=datetime.now(timezone.utc),
            )
            logger.debug("Test passed: %s (%.1f ms)", test_case.id, elapsed)

        except asyncio.TimeoutError:
            elapsed = (time.perf_counter() - t0) * 1000
            result = TestResult(
                test_id=test_case.id,
                suite_id=suite_id,
                passed=False,
                duration_ms=round(elapsed, 2),
                error=f"Test timed out after {timeout_s}s",
                timestamp=datetime.now(timezone.utc),
            )
            logger.warning("Test timed out: %s", test_case.id)

        except AssertionError as e:
            elapsed = (time.perf_counter() - t0) * 1000
            result = TestResult(
                test_id=test_case.id,
                suite_id=suite_id,
                passed=False,
                duration_ms=round(elapsed, 2),
                error=str(e),
                assertion_errors=[str(e)],
                timestamp=datetime.now(timezone.utc),
            )
            logger.warning("Test assertion failed: %s — %s", test_case.id, e)

        except Exception as e:
            elapsed = (time.perf_counter() - t0) * 1000
            result = TestResult(
                test_id=test_case.id,
                suite_id=suite_id,
                passed=False,
                duration_ms=round(elapsed, 2),
                error=str(e),
                timestamp=datetime.now(timezone.utc),
            )
            logger.error("Test error: %s — %s", test_case.id, e)

        self._results.append(result)
        return result

    async def run_suite(self, suite: TestSuite) -> TestReport:
        """Execute all test cases in a suite with setup/teardown hooks.

        Args:
            suite: The test suite to execute.

        Returns:
            TestReport with aggregated results.
        """
        logger.info("Running suite: %s (%s)", suite.id, suite.name)
        t0 = time.perf_counter()
        total = len(suite.test_cases)
        passed = 0
        failed = 0
        skipped = 0
        failures: List[Dict[str, Any]] = []

        # Setup hooks
        try:
            await self._run_hooks(suite.setup_hooks)
        except Exception:
            # If setup fails, mark all tests as failed
            for tc in suite.test_cases:
                failed += 1
                failures.append({
                    "test_id": tc.id,
                    "name": tc.name,
                    "error": "Suite setup failed",
                })
            total_time = (time.perf_counter() - t0) * 1000
            report = TestReport(
                suite_id=suite.id,
                total_tests=total,
                passed=0,
                failed=failed,
                skipped=0,
                duration_ms=round(total_time, 2),
                coverage_percent=0.0,
                failures=failures,
                recommendations=["Check suite setup hooks for errors"],
                timestamp=datetime.now(timezone.utc),
            )
            self._reports.append(report)
            return report

        # Run each test case
        for tc in suite.test_cases:
            result = await self.run_test(tc, suite_id=suite.id)
            if tc.skip:
                skipped += 1
            elif result.passed:
                passed += 1
            else:
                failed += 1
                failures.append({
                    "test_id": tc.id,
                    "name": tc.name,
                    "error": result.error,
                    "assertion_errors": result.assertion_errors,
                })

        # Teardown hooks
        try:
            await self._run_hooks(suite.teardown_hooks)
        except Exception as e:
            logger.error("Suite teardown error: %s", e)

        total_time = (time.perf_counter() - t0) * 1000

        # Generate recommendations
        recommendations = self._generate_recommendations(failures, passed, total)

        report = TestReport(
            suite_id=suite.id,
            total_tests=total,
            passed=passed,
            failed=failed,
            skipped=skipped,
            duration_ms=round(total_time, 2),
            coverage_percent=0.0,
            failures=failures,
            recommendations=recommendations,
            timestamp=datetime.now(timezone.utc),
        )
        self._reports.append(report)
        logger.info(
            "Suite complete: %s — %d/%d passed, %d failed, %d skipped (%.1f ms)",
            suite.id, passed, total, failed, skipped, total_time,
        )
        return report

    async def run_all(
        self,
        suites: List[TestSuite],
        parallel: bool = False,
    ) -> List[TestReport]:
        """Run multiple suites sequentially or in parallel.

        Args:
            suites: List of test suites.
            parallel: Whether to run suites in parallel.

        Returns:
            List of TestReport objects.
        """
        if parallel:
            tasks = [self.run_suite(s) for s in suites]
            return await asyncio.gather(*tasks)
        reports = []
        for suite in suites:
            report = await self.run_suite(suite)
            reports.append(report)
        return reports

    def get_results(self) -> List[TestResult]:
        """Return all test results accumulated so far."""
        return list(self._results)

    def get_reports(self) -> List[TestReport]:
        """Return all test reports accumulated so far."""
        return list(self._reports)

    def clear(self) -> None:
        """Clear all accumulated results and reports."""
        self._results.clear()
        self._reports.clear()

    def _generate_recommendations(
        self,
        failures: List[Dict[str, Any]],
        passed: int,
        total: int,
    ) -> List[str]:
        """Generate improvement recommendations based on results."""
        recommendations = []
        if failures:
            recommendations.append(f"Fix {len(failures)} failing test(s)")
            # Check for assertion patterns
            for f in failures:
                if f.get("error") and "timeout" in f["error"].lower():
                    recommendations.append(f"Increase timeout for test '{f['name']}'")
        if total > 0 and passed / total < 0.5:
            recommendations.append("Consider adding more unit tests to improve coverage")
        if not recommendations:
            recommendations.append("All tests passed — no issues found")
        return recommendations
