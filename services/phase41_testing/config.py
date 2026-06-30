"""
Phase 41 — Testing Framework Configuration.
"""

from pydantic import Field
from services.base.config_base import BaseConfig


class TestingConfig(BaseConfig):
    """Configuration for the testing framework."""

    service_name: str = Field(default="jarvis_testing", description="Testing service name")
    enable_mock_server: bool = Field(default=True, description="Enable the mock API server")
    enable_coverage_tracking: bool = Field(default=True, description="Enable coverage tracking")
    enable_ci_mode: bool = Field(default=False, description="Run in CI mode (fail-fast, junit output)")
    default_timeout_ms: int = Field(default=5000, ge=100, le=300000, description="Default test timeout in ms")
    mock_api_base_url: str = Field(default="http://mock.jarvis.local", description="Base URL for mock server")
    coverage_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum coverage fraction")
    max_test_workers: int = Field(default=4, ge=1, le=64, description="Max parallel test workers")
    report_dir: str = Field(default="./test_reports", description="Directory for test reports")

    model_config = {"env_prefix": "JARVIS_PHASE41_"}
