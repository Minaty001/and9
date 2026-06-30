"""
Phase 41 — Testing Framework
=============================

Provides a comprehensive testing infrastructure for JARVIS including a mock
API server, test runner, coverage tracker, and CI integrator.

Components:
    - MockApiServer: Register mock endpoints and simulate API responses
    - TestRunner: Execute test cases and suites with setup/teardown hooks
    - CoverageTracker: Track code coverage per module against thresholds
    - CiIntegrator: Run full CI pipeline with quality gates
    - TestingService: ServiceBase wrapper
"""

from .config import TestingConfig
from .models import TestCase, TestSuite, TestResult, TestReport, MockEndpoint, CoverageSnapshot
from .mock_server import MockApiServer
from .test_runner import TestRunner
from .coverage_tracker import CoverageTracker
from .ci_integrator import CiIntegrator
from .service import TestingService

__all__ = [
    "TestingConfig",
    "TestCase",
    "TestSuite",
    "TestResult",
    "TestReport",
    "MockEndpoint",
    "CoverageSnapshot",
    "MockApiServer",
    "TestRunner",
    "CoverageTracker",
    "CiIntegrator",
    "TestingService",
]
