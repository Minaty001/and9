# Phase 41 — Testing Framework

A comprehensive testing infrastructure for JARVIS, providing mock API servers,
test execution with lifecycle hooks, code coverage tracking, and CI/CD pipeline
integration.

## Purpose

The Testing Framework enables:

- **Mock API Server**: Simulate external API endpoints for isolated integration tests
- **Test Runner**: Execute test cases and suites with setup/teardown hooks, timeouts, and parallel support
- **Coverage Tracker**: Monitor code coverage per module and enforce quality thresholds
- **CI Integrator**: Run full CI pipelines with quality gates and JUnit XML-like output

## Components

### Config (`config.py`)

| Field | Default | Description |
|---|---|---|
| `service_name` | `jarvis_testing` | Service name |
| `enable_mock_server` | `True` | Enable the mock API server |
| `enable_coverage_tracking` | `True` | Enable coverage tracking |
| `enable_ci_mode` | `False` | Run in CI mode (fail-fast) |
| `default_timeout_ms` | `5000` | Default test timeout |
| `coverage_threshold` | `0.7` | Minimum coverage fraction |
| `max_test_workers` | `4` | Max parallel test workers |
| `report_dir` | `./test_reports` | Directory for test reports |

Configuration is loaded from environment variables with prefix `JARVIS_PHASE41_`.

### Models (`models.py`)

- **TestCase**: Test case definition with id, name, category, priority, tags, timeout, skip flag, and dependencies.
- **TestSuite**: Collection of test cases with setup/teardown hooks and parallel execution flag.
- **TestResult**: Outcome of a single test execution (pass/fail, duration, errors).
- **TestReport**: Aggregated results for a full suite run with failure details and recommendations.
- **MockEndpoint**: Registered mock endpoint with method, path, response, delay, and call tracking.
- **CoverageSnapshot**: Per-module coverage data (lines, percent, uncovered lines).

### MockApiServer (`mock_server.py`)

The mock server simulates HTTP APIs for testing:

```python
server = MockApiServer()
server.register_endpoint("GET", "/api/weather", {"temp": 22})
response = server.handle_request("GET", "/api/weather")
# response == {"status_code": 200, "data": {"temp": 22}}
```

Features:
- Register endpoints with any method/path/status code
- Artificial response delays for timeout testing
- Automatic call count tracking per endpoint
- Auto-registered endpoints for common services (weather, news, search)
- Full reset or selective clearing

### TestRunner (`test_runner.py`)

Executes tests with comprehensive lifecycle support:

```python
runner = TestRunner()
result = await runner.run_test(test_case)
report = await runner.run_suite(suite)
reports = await runner.run_all([suite1, suite2], parallel=True)
```

Features:
- Setup/teardown hooks per suite (sync and async)
- Per-test timeout enforcement
- Skip support via `TestCase.skip`
- Failure analysis with recommendations
- Sequential or parallel suite execution

### CoverageTracker (`coverage_tracker.py`)

Tracks code coverage and enforces thresholds:

```python
tracker = CoverageTracker(threshold=0.7)
tracker.track_coverage("module_a", covered_lines=80, total_lines=100)
tracker.check_threshold()  # True if all modules >= 70%
report = tracker.generate_report()
```

Features:
- Per-module coverage tracking with snapshots
- Overall weighted coverage calculation
- Threshold enforcement with per-module checks
- Uncovered line tracking
- Full coverage report generation

### CiIntegrator (`ci_integrator.py`)

Full CI pipeline integration:

```python
result = await ci.run_ci_pipeline(suites)
# result["gate_passed"] == True/False
xml_report = ci.generate_ci_report()  # JUnit XML-like
ci.check_gate()  # Quality gate check
```

Features:
- Run all suites and check coverage in one call
- Generate CI-friendly output (JUnit XML-like format)
- Quality gate: all tests pass + coverage threshold met
- Per-pipeline result tracking

## Usage

### Basic Service Lifecycle

```python
from services.phase41_testing import TestingService, TestCase, TestSuite

svc = TestingService()
await svc.initialize()

# Run a test
tc = TestCase(id="my_test", name="My Test")
result = await svc.run_test(tc)

# Run a suite
suite = TestSuite(id="my_suite", name="My Suite", test_cases=[tc])
report = await svc.run_suite(suite)

await svc.shutdown()
```

### Registering Mock Endpoints

```python
svc.register_endpoint("GET", "/api/users", [{"id": 1, "name": "Alice"}], status_code=200)
svc.register_endpoint("POST", "/api/users", {"id": 2, "name": "Bob"}, status_code=201)
```

### Tracking Coverage

```python
svc.track_coverage("module_a", covered_lines=75, total_lines=100, uncovered_lines=[10, 42])
coverage_pct = svc.get_coverage("module_a")   # 0.75
overall = svc.get_overall_coverage()
threshold_ok = svc.check_threshold()
```

### Running the CI Pipeline

```python
result = await svc.run_ci_pipeline(suites)
ci_report = svc.generate_ci_report()
gate_passed = svc.check_ci_gate()
```

## Configuration

All configuration is via environment variables with the `JARVIS_PHASE41_` prefix:

```bash
export JARVIS_PHASE41_ENABLE_MOCK_SERVER=true
export JARVIS_PHASE41_COVERAGE_THRESHOLD=0.8
export JARVIS_PHASE41_DEFAULT_TIMEOUT_MS=10000
export JARVIS_PHASE41_ENABLE_CI_MODE=true
```

## CI/CD Integration

The CI integrator provides a unified pipeline that:

1. Runs all registered test suites (optionally in parallel)
2. Checks coverage thresholds for all tracked modules
3. Generates a JUnit XML-like report for CI tools
4. Returns a gate result (pass/fail)

Example CI script:

```python
from services.phase41_testing import TestingService, TestCase, TestSuite

svc = TestingService()
await svc.initialize()

# Register suites
suites = create_all_test_suites()

# Track coverage
svc.track_coverage("my_module", covered_lines=120, total_lines=150)

# Run pipeline
result = await svc.run_ci_pipeline(suites)

# Generate CI report
print(svc.generate_ci_report())

# Check gate
if not svc.check_ci_gate():
    exit(1)
```

## Testing

Run the test suite for this phase:

```bash
pytest services/phase41_testing/tests/ -v
```
