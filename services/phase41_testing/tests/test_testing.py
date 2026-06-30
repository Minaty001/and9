"""
Tests for Phase 41 — Testing Framework.
"""

import pytest
from services.phase41_testing import (
    TestingConfig,
    TestCase,
    TestSuite,
    TestResult,
    TestReport,
    MockEndpoint,
    CoverageSnapshot,
    MockApiServer,
    TestRunner,
    CoverageTracker,
    CiIntegrator,
    TestingService,
)


# ── Config Tests ─────────────────────────────────────────────────

class TestTestingConfig:
    """Verify configuration defaults and env prefix."""

    def test_default_config(self):
        config = TestingConfig()
        assert config.service_name == "jarvis_testing"
        assert config.enable_mock_server is True
        assert config.enable_coverage_tracking is True
        assert config.enable_ci_mode is False
        assert config.default_timeout_ms == 5000
        assert config.coverage_threshold == 0.7
        assert config.max_test_workers == 4
        assert config.report_dir == "./test_reports"

    def test_env_prefix(self):
        assert TestingConfig.model_config["env_prefix"] == "JARVIS_PHASE41_"

    def test_custom_config(self):
        config = TestingConfig(
            service_name="custom_testing",
            enable_mock_server=False,
            coverage_threshold=0.85,
            max_test_workers=8,
        )
        assert config.service_name == "custom_testing"
        assert config.enable_mock_server is False
        assert config.coverage_threshold == 0.85
        assert config.max_test_workers == 8


# ── Model Tests ──────────────────────────────────────────────────

class TestModels:
    """Verify data model creation and defaults."""

    def test_test_case_defaults(self):
        tc = TestCase(id="tc_1", name="Test basic feature")
        assert tc.description == ""
        assert tc.category == "unit"
        assert tc.priority == 3
        assert tc.skip is False
        assert tc.dependencies == []

    def test_test_case_skip(self):
        tc = TestCase(id="tc_skip", name="Skippy", skip=True)
        assert tc.skip is True

    def test_test_suite_with_cases(self):
        tc1 = TestCase(id="tc_1", name="Test 1")
        tc2 = TestCase(id="tc_2", name="Test 2")
        suite = TestSuite(
            id="suite_1",
            name="My Suite",
            test_cases=[tc1, tc2],
            setup_hooks=["setup_db"],
            teardown_hooks=["teardown_db"],
            parallel=True,
        )
        assert len(suite.test_cases) == 2
        assert suite.parallel is True
        assert "setup_db" in suite.setup_hooks

    def test_test_result_defaults(self):
        result = TestResult(test_id="tc_1")
        assert result.passed is False
        assert result.duration_ms == 0.0
        assert result.error is None
        assert result.assertion_errors == []

    def test_test_report_sums(self):
        report = TestReport(
            suite_id="suite_1",
            total_tests=10,
            passed=7,
            failed=2,
            skipped=1,
            duration_ms=1234.5,
            coverage_percent=72.5,
            failures=[{"test_id": "tc_3", "error": "assert failed"}],
            recommendations=["Fix failing tests"],
        )
        assert report.total_tests == 10
        assert report.passed == 7
        assert report.failed == 2
        assert report.skipped == 1
        assert len(report.recommendations) == 1

    def test_mock_endpoint_call_count(self):
        ep = MockEndpoint(method="GET", path="/api/test", response_data={"ok": True})
        assert ep.call_count == 0
        assert ep.status_code == 200

    def test_coverage_snapshot_empty(self):
        snap = CoverageSnapshot(module="test_mod", total_lines=100, covered_lines=75)
        assert snap.coverage_percent == 75.0
        assert snap.uncovered_lines == []


# ── MockApiServer Tests ──────────────────────────────────────────

class TestMockApiServer:
    """Verify mock endpoint registration, handling, and lifecycle."""

    def test_register_and_handle(self):
        server = MockApiServer()
        server.register_endpoint("GET", "/api/test", {"message": "hello"})
        response = server.handle_request("GET", "/api/test")
        assert response["status_code"] == 200
        assert response["data"]["message"] == "hello"

    def test_handle_unknown_returns_404(self):
        server = MockApiServer()
        response = server.handle_request("GET", "/api/nonexistent")
        assert response["status_code"] == 404

    def test_call_count_tracking(self):
        server = MockApiServer()
        server.register_endpoint("POST", "/api/data", {"id": 1})
        server.handle_request("POST", "/api/data")
        server.handle_request("POST", "/api/data")
        server.handle_request("POST", "/api/data")
        stats = server.get_stats()
        key = "POST:/api/data"
        assert stats[key] == 3

    def test_reset_clears_counts(self):
        server = MockApiServer()
        server.register_endpoint("GET", "/api/test", "ok")
        server.handle_request("GET", "/api/test")
        server.reset()
        # After reset, auto endpoints are re-registered but test endpoint is gone
        ep = server.get_endpoint("GET", "/api/test")
        assert ep is None

    def test_delay_ms(self):
        import time
        server = MockApiServer()
        server.register_endpoint("GET", "/api/slow", "slow", delay_ms=50)
        t0 = time.perf_counter()
        server.handle_request("GET", "/api/slow")
        elapsed = (time.perf_counter() - t0) * 1000
        assert elapsed >= 45  # allow small tolerance

    def test_auto_registered_common(self):
        server = MockApiServer()
        weather = server.handle_request("GET", "/api/weather")
        assert weather["status_code"] == 200
        assert "temperature" in weather["data"]

        news = server.handle_request("GET", "/api/news")
        assert news["status_code"] == 200
        assert "articles" in news["data"]

    def test_handle_request_with_base_url_in_path(self):
        server = MockApiServer(base_url="http://mock.jarvis.local")
        server.register_endpoint("GET", "/api/test", "ok")
        response = server.handle_request("GET", "http://mock.jarvis.local/api/test")
        assert response["status_code"] == 200

    def test_clear_endpoints(self):
        server = MockApiServer()
        server.clear_endpoints()
        response = server.handle_request("GET", "/api/weather")
        assert response["status_code"] == 404


# ── TestRunner Tests ─────────────────────────────────────────────

class TestTestRunner:
    """Verify test execution, suites, hooks, and reporting."""

    @pytest.mark.asyncio
    async def test_run_single_test_pass(self):
        runner = TestRunner()
        tc = TestCase(id="simple_pass", name="Simple pass test")
        result = await runner.run_test(tc)
        assert result.passed is True
        assert result.test_id == "simple_pass"

    @pytest.mark.asyncio
    async def test_run_single_test_with_assertion_error(self):
        runner = TestRunner()

        async def failing_test():
            raise AssertionError("Expected value was 42")

        runner.register_hook("test:fail_assert", failing_test)
        tc = TestCase(id="fail_assert", name="Failing assertion test")
        result = await runner.run_test(tc)
        assert result.passed is False
        assert "Expected value was 42" in result.error

    @pytest.mark.asyncio
    async def test_run_single_test_with_timeout(self):
        runner = TestRunner()

        async def slow_test():
            import asyncio
            await asyncio.sleep(10)

        runner.register_hook("test:slow", slow_test)
        tc = TestCase(id="slow", name="Slow test", timeout_ms=50)
        result = await runner.run_test(tc)
        assert result.passed is False
        assert "timed out" in result.error.lower()

    @pytest.mark.asyncio
    async def test_skip_test(self):
        runner = TestRunner()
        tc = TestCase(id="skip_me", name="Skip test", skip=True)
        result = await runner.run_test(tc)
        assert result.passed is False
        assert result.duration_ms == 0

    @pytest.mark.asyncio
    async def test_run_suite_with_setup_teardown(self):
        runner = TestRunner()
        setup_called = []
        teardown_called = []

        def setup_fn():
            setup_called.append(True)

        def teardown_fn():
            teardown_called.append(True)

        runner.register_hook("setup_db", setup_fn)
        runner.register_hook("teardown_db", teardown_fn)

        tc1 = TestCase(id="tc_1", name="Test 1")
        suite = TestSuite(
            id="suite_setup",
            name="Setup Test Suite",
            test_cases=[tc1],
            setup_hooks=["setup_db"],
            teardown_hooks=["teardown_db"],
        )
        report = await runner.run_suite(suite)
        assert report.passed == 1
        assert report.failed == 0
        assert len(setup_called) == 1
        assert len(teardown_called) == 1

    @pytest.mark.asyncio
    async def test_run_suite_setup_failure(self):
        runner = TestRunner()

        def failing_setup():
            raise RuntimeError("Setup crashed")

        runner.register_hook("bad_setup", failing_setup)
        tc = TestCase(id="tc_1", name="Test 1")
        suite = TestSuite(
            id="suite_fail",
            name="Failing Setup Suite",
            test_cases=[tc],
            setup_hooks=["bad_setup"],
        )
        report = await runner.run_suite(suite)
        assert report.failed == 1
        assert report.passed == 0

    @pytest.mark.asyncio
    async def test_run_all_sequential(self):
        runner = TestRunner()
        suites = [
            TestSuite(id="s1", name="Suite 1", test_cases=[TestCase(id="a", name="A")]),
            TestSuite(id="s2", name="Suite 2", test_cases=[TestCase(id="b", name="B")]),
        ]
        reports = await runner.run_all(suites, parallel=False)
        assert len(reports) == 2
        assert reports[0].passed == 1
        assert reports[1].passed == 1

    @pytest.mark.asyncio
    async def test_run_suite_with_mixed_results(self):
        runner = TestRunner()

        async def fail_test():
            raise AssertionError("Failed intentionally")

        runner.register_hook("test:fail_one", fail_test)
        tc_pass = TestCase(id="pass_one", name="Passing test")
        tc_fail = TestCase(id="fail_one", name="Failing test")
        tc_skip = TestCase(id="skip_one", name="Skipped test", skip=True)
        suite = TestSuite(
            id="mixed",
            name="Mixed Results Suite",
            test_cases=[tc_pass, tc_fail, tc_skip],
        )
        report = await runner.run_suite(suite)
        assert report.passed == 1
        assert report.failed == 1
        assert report.skipped == 1
        assert report.total_tests == 3


# ── CoverageTracker Tests ────────────────────────────────────────

class TestCoverageTracker:
    """Verify coverage tracking, threshold checks, and reporting."""

    def test_track_coverage(self):
        tracker = CoverageTracker()
        snap = tracker.track_coverage("module_a", 80, 100)
        assert snap.module == "module_a"
        assert snap.coverage_percent == 80.0
        assert snap.covered_lines == 80
        assert snap.total_lines == 100

    def test_get_coverage(self):
        tracker = CoverageTracker()
        tracker.track_coverage("module_a", 75, 100)
        assert tracker.get_coverage("module_a") == 0.75

    def test_get_coverage_unknown(self):
        tracker = CoverageTracker()
        assert tracker.get_coverage("unknown") == 0.0

    def test_overall_coverage(self):
        tracker = CoverageTracker()
        tracker.track_coverage("mod_a", 50, 100)
        tracker.track_coverage("mod_b", 90, 100)
        overall = tracker.get_overall_coverage()
        assert overall == 0.7  # (50+90)/(100+100) = 140/200 = 0.7

    def test_get_uncovered_lines(self):
        tracker = CoverageTracker()
        tracker.track_coverage("mod_a", 80, 100, uncovered_lines=[10, 20, 30])
        lines = tracker.get_uncovered_lines("mod_a")
        assert lines == [10, 20, 30]

    def test_get_uncovered_lines_unknown(self):
        tracker = CoverageTracker()
        assert tracker.get_uncovered_lines("unknown") == []

    def test_threshold_met(self):
        tracker = CoverageTracker(threshold=0.7)
        tracker.track_coverage("mod_a", 80, 100)  # 80% > 70%
        assert tracker.check_threshold() is True

    def test_threshold_not_met(self):
        tracker = CoverageTracker(threshold=0.8)
        tracker.track_coverage("mod_a", 70, 100)  # 70% < 80%
        assert tracker.check_threshold() is False

    def test_threshold_empty(self):
        tracker = CoverageTracker(threshold=0.8)
        assert tracker.check_threshold() is True  # no modules = pass

    def test_generate_report(self):
        tracker = CoverageTracker(threshold=0.6)
        tracker.track_coverage("mod_a", 80, 100)
        tracker.track_coverage("mod_b", 50, 100)
        report = tracker.generate_report()
        assert "overall_coverage_percent" in report
        assert report["total_modules"] == 2
        assert report["threshold"] == 0.6
        assert report["modules_below_threshold"] == ["mod_b"]


# ── CiIntegrator Tests ───────────────────────────────────────────

class TestCiIntegrator:
    """Verify CI pipeline, gate checking, and report generation."""

    @pytest.mark.asyncio
    async def test_ci_pipeline_all_pass(self):
        runner = TestRunner()
        coverage = CoverageTracker(threshold=0.7)
        ci = CiIntegrator(runner, coverage)
        coverage.track_coverage("mod_a", 80, 100)

        suites = [
            TestSuite(id="s1", name="Suite 1", test_cases=[TestCase(id="a", name="A")]),
        ]
        result = await ci.run_ci_pipeline(suites)
        assert result["status"] == "passed"
        assert result["gate_passed"] is True

    @pytest.mark.asyncio
    async def test_ci_pipeline_fails_on_test_failure(self):
        runner = TestRunner()
        coverage = CoverageTracker(threshold=0.0)
        ci = CiIntegrator(runner, coverage)

        async def fail_test():
            raise AssertionError("fail")

        runner.register_hook("test:fail", fail_test)
        suites = [
            TestSuite(
                id="s_fail",
                name="Failing Suite",
                test_cases=[TestCase(id="fail", name="Fail")],
            ),
        ]
        result = await ci.run_ci_pipeline(suites)
        assert result["status"] == "failed"
        assert result["gate_passed"] is False

    def test_check_gate_before_pipeline(self):
        coverage = CoverageTracker(threshold=0.9)
        coverage.track_coverage("mod_a", 95, 100)
        runner = TestRunner()
        ci = CiIntegrator(runner, coverage)
        assert ci.check_gate() is True  # coverage met

    def test_check_gate_fails_low_coverage(self):
        coverage = CoverageTracker(threshold=0.9)
        coverage.track_coverage("mod_a", 50, 100)
        runner = TestRunner()
        ci = CiIntegrator(runner, coverage)
        assert ci.check_gate() is False

    def test_generate_ci_report_empty(self):
        runner = TestRunner()
        coverage = CoverageTracker()
        ci = CiIntegrator(runner, coverage)
        report = ci.generate_ci_report()
        assert report == "<testsuites/>"

    @pytest.mark.asyncio
    async def test_generate_ci_report_after_pipeline(self):
        runner = TestRunner()
        coverage = CoverageTracker(threshold=0.0)
        ci = CiIntegrator(runner, coverage)
        coverage.track_coverage("mod_a", 100, 100)
        suites = [
            TestSuite(id="s1", name="Suite 1", test_cases=[TestCase(id="a", name="A")]),
        ]
        await ci.run_ci_pipeline(suites)
        report_xml = ci.generate_ci_report()
        assert "<testsuites" in report_xml
        assert 'name="s1"' in report_xml

    @pytest.mark.asyncio
    async def test_get_last_result(self):
        runner = TestRunner()
        coverage = CoverageTracker()
        ci = CiIntegrator(runner, coverage)
        assert ci.get_last_result() is None
        suites = [
            TestSuite(id="s1", name="Suite 1", test_cases=[TestCase(id="a", name="A")]),
        ]
        await ci.run_ci_pipeline(suites)
        assert ci.get_last_result() is not None
        assert ci.get_last_result()["status"] == "passed"


# ── TestingService Tests ─────────────────────────────────────────

class TestTestingService:
    """Verify service lifecycle and operations."""

    @pytest.mark.asyncio
    async def test_initialize(self):
        svc = TestingService()
        assert await svc.initialize() is True
        assert svc.is_initialized()

    @pytest.mark.asyncio
    async def test_health(self):
        svc = TestingService()
        await svc.initialize()
        health = await svc.health()
        assert health["status"] == "healthy"
        assert health["service_name"] == "jarvis_testing"
        assert "uptime_seconds" in health
        assert health["initialized"] is True
        assert "mock_server" in health

    @pytest.mark.asyncio
    async def test_health_before_initialize(self):
        svc = TestingService()
        health = await svc.health()
        assert health["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_stats(self):
        svc = TestingService()
        await svc.initialize()
        stats = await svc.stats()
        assert stats["service"] == "jarvis_testing"
        assert "version" in stats
        assert "uptime_seconds" in stats
        assert "tests" in stats
        assert "coverage" in stats
        assert "mock_server" in stats
        assert "metrics" in stats

    @pytest.mark.asyncio
    async def test_register_and_run_test(self):
        svc = TestingService()
        await svc.initialize()
        tc = TestCase(id="svc_test", name="Service test")
        result = await svc.run_test(tc)
        assert result.passed is True
        assert result.test_id == "svc_test"

    @pytest.mark.asyncio
    async def test_run_suite_via_service(self):
        svc = TestingService()
        await svc.initialize()
        tc = TestCase(id="svc_suite_test", name="Suite test")
        suite = TestSuite(
            id="svc_suite",
            name="Service Suite",
            test_cases=[tc],
        )
        report = await svc.run_suite(suite)
        assert report.passed == 1
        assert report.total_tests == 1

    @pytest.mark.asyncio
    async def test_register_endpoint_via_service(self):
        svc = TestingService()
        await svc.initialize()
        ep = svc.register_endpoint("GET", "/api/via_service", {"result": "ok"})
        assert ep.method == "GET"
        assert ep.status_code == 200

    @pytest.mark.asyncio
    async def test_coverage_via_service(self):
        svc = TestingService()
        await svc.initialize()
        snap = svc.track_coverage("svc_module", 50, 100)
        assert snap.module == "svc_module"
        assert svc.get_coverage("svc_module") == 0.5
        assert svc.get_overall_coverage() == 0.5

    @pytest.mark.asyncio
    async def test_check_threshold_via_service(self):
        svc = TestingService()
        await svc.initialize()
        svc.track_coverage("mod_a", 80, 100)
        assert svc.check_threshold() is True
        svc.track_coverage("mod_b", 30, 100)
        assert svc.check_threshold() is False

    @pytest.mark.asyncio
    async def test_ci_pipeline_via_service(self):
        svc = TestingService()
        await svc.initialize()
        svc.track_coverage("mod_a", 80, 100)
        suites = [
            TestSuite(
                id="ci_suite",
                name="CI Suite",
                test_cases=[TestCase(id="ci_test", name="CI test")],
            ),
        ]
        result = await svc.run_ci_pipeline(suites)
        assert result["gate_passed"] is True
        assert svc.check_ci_gate() is True

    @pytest.mark.asyncio
    async def test_generate_coverage_report(self):
        svc = TestingService()
        await svc.initialize()
        svc.track_coverage("mod_a", 80, 100)
        report = svc.generate_coverage_report()
        assert report["total_modules"] == 1
        assert report["overall_coverage_percent"] == 80.0

    @pytest.mark.asyncio
    async def test_get_reports(self):
        svc = TestingService()
        await svc.initialize()
        tc = TestCase(id="report_test", name="Report test")
        suite = TestSuite(id="r_suite", name="Report Suite", test_cases=[tc])
        await svc.run_suite(suite)
        reports = svc.get_reports()
        assert len(reports) == 1
        assert reports[0].suite_id == "r_suite"

    @pytest.mark.asyncio
    async def test_shutdown(self):
        svc = TestingService()
        await svc.initialize()
        await svc.shutdown()
        assert not svc.is_initialized()

    @pytest.mark.asyncio
    async def test_run_all_via_service(self):
        svc = TestingService()
        await svc.initialize()
        suites = [
            TestSuite(id="s1", name="Suite 1", test_cases=[TestCase(id="a1", name="A1")]),
            TestSuite(id="s2", name="Suite 2", test_cases=[TestCase(id="a2", name="A2")]),
        ]
        reports = await svc.run_all(suites)
        assert len(reports) == 2
        assert all(r.passed == 1 for r in reports)
