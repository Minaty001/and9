"""
Phase 41 — Testing Framework Data Models.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TestCase(BaseModel):
    """A single test case definition."""

    id: str = Field(..., description="Unique test case identifier")
    name: str = Field(..., description="Human-readable test name")
    description: str = Field(default="", description="Test description")
    category: str = Field(default="unit", description="Test category: unit/integration/e2e/regression")
    module: str = Field(default="", description="Module under test")
    priority: int = Field(default=3, ge=1, le=5, description="Priority (1=highest, 5=lowest)")
    tags: List[str] = Field(default_factory=list, description="Arbitrary tags for filtering")
    timeout_ms: int = Field(default=5000, ge=100, description="Timeout in milliseconds")
    skip: bool = Field(default=False, description="Skip this test case")
    dependencies: List[str] = Field(default_factory=list, description="Test case IDs that must pass first")


class TestSuite(BaseModel):
    """A collection of test cases with lifecycle hooks."""

    id: str = Field(..., description="Unique suite identifier")
    name: str = Field(..., description="Human-readable suite name")
    description: str = Field(default="", description="Suite description")
    test_cases: List[TestCase] = Field(default_factory=list, description="Test cases in this suite")
    setup_hooks: List[str] = Field(default_factory=list, description="Hook names executed before suite")
    teardown_hooks: List[str] = Field(default_factory=list, description="Hook names executed after suite")
    parallel: bool = Field(default=False, description="Run test cases in parallel")


class TestResult(BaseModel):
    """Result of executing a single test case."""

    test_id: str = Field(..., description="Test case identifier")
    suite_id: str = Field(default="", description="Suite identifier")
    passed: bool = Field(default=False, description="Whether the test passed")
    duration_ms: float = Field(default=0.0, description="Execution duration in ms")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    assertion_errors: List[str] = Field(default_factory=list, description="List of assertion failures")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    coverage_snapshot: Optional[Dict[str, float]] = Field(default=None, description="Coverage at test time")


class TestReport(BaseModel):
    """Report for an entire test suite run."""

    suite_id: str = Field(..., description="Suite identifier")
    total_tests: int = Field(default=0, description="Total test cases")
    passed: int = Field(default=0, description="Tests passed")
    failed: int = Field(default=0, description="Tests failed")
    skipped: int = Field(default=0, description="Tests skipped")
    duration_ms: float = Field(default=0.0, description="Total duration in ms")
    coverage_percent: float = Field(default=0.0, description="Overall coverage percent")
    failures: List[Dict[str, Any]] = Field(default_factory=list, description="Failure details")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    recommendations: List[str] = Field(default_factory=list, description="Improvement recommendations")


class MockEndpoint(BaseModel):
    """A registered mock endpoint."""

    method: str = Field(..., description="HTTP method (GET, POST, PUT, DELETE, etc.)")
    path: str = Field(..., description="URL path")
    status_code: int = Field(default=200, ge=100, le=599, description="Response status code")
    response_data: Any = Field(default=None, description="Response payload")
    delay_ms: int = Field(default=0, ge=0, description="Artificial delay in ms")
    headers: Dict[str, str] = Field(default_factory=dict, description="Response headers")
    call_count: int = Field(default=0, ge=0, description="Number of times called")


class CoverageSnapshot(BaseModel):
    """Coverage snapshot for a module."""

    module: str = Field(..., description="Module name")
    total_lines: int = Field(default=0, ge=0, description="Total executable lines")
    covered_lines: int = Field(default=0, ge=0, description="Covered lines")
    coverage_percent: float = Field(default=0.0, ge=0.0, le=100.0, description="Coverage percentage")
    uncovered_lines: List[int] = Field(default_factory=list, description="Line numbers not covered")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
