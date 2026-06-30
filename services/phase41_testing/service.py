"""
Phase 41 — Testing Framework Service.

ServiceBase wrapper for the Testing Framework.
"""

from __future__ import annotations

import time
import logging
from typing import Any, Dict, List, Optional

from services.base.service_base import ServiceBase
from .config import TestingConfig
from .models import TestCase, TestSuite, TestResult, TestReport, MockEndpoint, CoverageSnapshot
from .mock_server import MockApiServer
from .test_runner import TestRunner
from .coverage_tracker import CoverageTracker
from .ci_integrator import CiIntegrator

logger = logging.getLogger(__name__)


class TestingService(ServiceBase):
    """Testing framework service for managing tests, mocks, coverage, and CI.

    Usage:
        svc = TestingService()
        await svc.initialize()
        report = await svc.run_suite(my_suite)
        health = await svc.health()
    """

    def __init__(self, config: Optional[TestingConfig] = None):
        super().__init__(name="jarvis_testing", version="1.0.0")
        self.config = config or TestingConfig()
        self.mock_server: Optional[MockApiServer] = None
        self.runner: Optional[TestRunner] = None
        self.coverage: Optional[CoverageTracker] = None
        self.ci: Optional[CiIntegrator] = None
        self._start_time = 0.0
        self._suites: Dict[str, TestSuite] = {}

    async def initialize(self) -> bool:
        """Initialize the testing service and all components."""
        self._start_time = time.time()
        try:
            self.mock_server = MockApiServer(base_url=self.config.mock_api_base_url)
            self.runner = TestRunner(default_timeout_ms=self.config.default_timeout_ms)
            self.coverage = CoverageTracker(threshold=self.config.coverage_threshold)
            self.ci = CiIntegrator(
                runner=self.runner,
                coverage=self.coverage,
                fail_fast=self.config.enable_ci_mode,
            )
            self._metrics.reset()
            self._initialized = True
            logger.info("TestingService initialized (mock=%s, coverage=%s, ci=%s)",
                        self.config.enable_mock_server,
                        self.config.enable_coverage_tracking,
                        self.config.enable_ci_mode)
            return True
        except Exception as e:
            logger.error("TestingService init failed: %s", e)
            return False

    async def shutdown(self) -> None:
        """Shut down the testing service."""
        logger.info("TestingService shutting down...")
        self._initialized = False

    # ── Mock API Server ───────────────────────────────────────────

    def register_endpoint(
        self,
        method: str,
        path: str,
        response_data: Any,
        status_code: int = 200,
        delay_ms: int = 0,
        headers: Optional[Dict[str, str]] = None,
    ) -> MockEndpoint:
        """Register a mock endpoint."""
        if not self.mock_server:
            raise RuntimeError("TestingService not initialized")
        return self.mock_server.register_endpoint(method, path, response_data, status_code, delay_ms, headers)

    def clear_endpoints(self) -> None:
        """Clear all mock endpoints."""
        if not self.mock_server:
            raise RuntimeError("TestingService not initialized")
        self.mock_server.clear_endpoints()

    async def mock_endpoint(
        self,
        method: str,
        path: str,
        response_data: Any,
        status_code: int = 200,
        delay_ms: int = 0,
        headers: Optional[Dict[str, str]] = None,
    ) -> MockEndpoint:
        """Register a mock endpoint (alias for register_endpoint)."""
        return self.register_endpoint(method, path, response_data, status_code, delay_ms, headers)

    # ── Test Runner ───────────────────────────────────────────────

    async def register_test(self, test_case: TestCase) -> None:
        """Register a test case (stores for later use)."""
        if not self.runner:
            raise RuntimeError("TestingService not initialized")
        # Tests are stored in the runner via hook registration
        logger.debug("Test case registered: %s", test_case.id)

    async def register_test_suite(self, name: str, description: str = "") -> str:
        """Register a test suite by name and description.

        Returns:
            The suite id string.
        """
        if not self.runner:
            raise RuntimeError("TestingService not initialized")
        suite_id = f"suite_{len(self._suites) + 1}"
        suite = TestSuite(id=suite_id, name=name, description=description)
        self._suites[suite_id] = suite
        logger.debug("Test suite registered: %s", suite_id)
        return suite_id

    async def run_test(self, test_case: TestCase) -> TestResult:
        """Run a single test case."""
        if not self.runner:
            raise RuntimeError("TestingService not initialized")
        t0 = time.perf_counter()
        result = await self.runner.run_test(test_case)
        elapsed = (time.perf_counter() - t0) * 1000
        self._metrics.counter("tests_run", 1)
        self._metrics.histogram("test_duration_ms", elapsed)
        if result.passed:
            self._metrics.counter("tests_passed", 1)
        else:
            self._metrics.counter("tests_failed", 1)
        return result

    async def run_suite(self, suite: TestSuite) -> TestReport:
        """Run a test suite."""
        if not self.runner:
            raise RuntimeError("TestingService not initialized")
        if isinstance(suite, str):
            if suite not in self._suites:
                raise ValueError(f"Unknown suite id: {suite}")
            suite = self._suites[suite]
        t0 = time.perf_counter()
        report = await self.runner.run_suite(suite)
        elapsed = (time.perf_counter() - t0) * 1000
        self._metrics.counter("suites_run", 1)
        self._metrics.histogram("suite_duration_ms", elapsed)
        return report

    async def run_all(self, suites: List[TestSuite], parallel: bool = False) -> List[TestReport]:
        """Run multiple test suites."""
        if not self.runner:
            raise RuntimeError("TestingService not initialized")
        t0 = time.perf_counter()
        reports = await self.runner.run_all(suites, parallel=parallel)
        elapsed = (time.perf_counter() - t0) * 1000
        self._metrics.counter("suites_run", len(reports))
        self._metrics.histogram("all_suites_duration_ms", elapsed)
        return reports

    # ── Coverage Tracker ──────────────────────────────────────────

    def track_coverage(
        self,
        module: str,
        lines_covered: int,
        total_lines: int,
        uncovered_lines: Optional[List[int]] = None,
    ) -> CoverageSnapshot:
        """Track coverage for a module."""
        if not self.coverage:
            raise RuntimeError("TestingService not initialized")
        return self.coverage.track_coverage(module, lines_covered, total_lines, uncovered_lines)

    def get_coverage(self, module: str) -> float:
        """Get coverage percentage for a module."""
        if not self.coverage:
            raise RuntimeError("TestingService not initialized")
        return self.coverage.get_coverage(module)

    def get_overall_coverage(self) -> float:
        """Get overall coverage across all modules."""
        if not self.coverage:
            raise RuntimeError("TestingService not initialized")
        return self.coverage.get_overall_coverage()

    def check_threshold(self) -> bool:
        """Check if all modules meet the coverage threshold."""
        if not self.coverage:
            raise RuntimeError("TestingService not initialized")
        return self.coverage.check_threshold()

    def generate_coverage_report(self) -> Dict[str, Any]:
        """Generate a coverage report."""
        if not self.coverage:
            raise RuntimeError("TestingService not initialized")
        return self.coverage.generate_report()

    # ── CI Integrator ─────────────────────────────────────────────

    async def run_ci_pipeline(
        self,
        suites: List[TestSuite],
        parallel: bool = False,
    ) -> Dict[str, Any]:
        """Run the full CI pipeline."""
        if not self.ci:
            raise RuntimeError("TestingService not initialized")
        t0 = time.perf_counter()
        result = await self.ci.run_ci_pipeline(suites, parallel=parallel)
        elapsed = (time.perf_counter() - t0) * 1000
        self._metrics.counter("ci_pipelines_run", 1)
        self._metrics.histogram("ci_pipeline_duration_ms", elapsed)
        return result

    def generate_ci_report(self) -> str:
        """Generate CI-friendly report."""
        if not self.ci:
            raise RuntimeError("TestingService not initialized")
        return self.ci.generate_ci_report()

    def check_ci_gate(self) -> bool:
        """Check if quality gate passes."""
        if not self.ci:
            raise RuntimeError("TestingService not initialized")
        return self.ci.check_gate()

    # ── Reports ───────────────────────────────────────────────────

    def get_reports(self) -> List[TestReport]:
        """Get all accumulated test reports."""
        if not self.runner:
            raise RuntimeError("TestingService not initialized")
        return self.runner.get_reports()

    # ── Introspection ─────────────────────────────────────────────

    async def health(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        mock_status = "running" if (self.mock_server and self.config.enable_mock_server) else "disabled"
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "service_name": self.name,
            "version": self.version,
            "initialized": self._initialized,
            "uptime_seconds": round(uptime, 1),
            "mock_server": mock_status,
            "coverage_tracking": self.config.enable_coverage_tracking,
            "ci_mode": self.config.enable_ci_mode,
        }

    async def stats(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        reports = self.runner.get_reports() if self.runner else []
        total = sum(r.total_tests for r in reports)
        passed = sum(r.passed for r in reports)
        failed = sum(r.failed for r in reports)
        skipped = sum(r.skipped for r in reports)

        coverage_info = {}
        if self.coverage:
            coverage_info = {
                "overall_coverage": round(self.coverage.get_overall_coverage() * 100, 2),
                "threshold_met": self.coverage.check_threshold(),
                "modules_tracked": len(self.coverage.get_all_snapshots()),
            }

        mock_info = {}
        if self.mock_server:
            mock_info = {
                "endpoints_registered": len(self.mock_server.get_all_endpoints()),
                "calls": self.mock_server.get_stats(),
            }

        return {
            "service": self.name,
            "version": self.version,
            "uptime_seconds": round(uptime, 1),
            "tests": {
                "total_reports": len(reports),
                "total_tests": total,
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
            },
            "coverage": coverage_info,
            "mock_server": mock_info,
            "metrics": self._metrics.snapshot(),
        }
