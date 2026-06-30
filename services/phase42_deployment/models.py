"""
Phase 42 — Deployment Models.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EnvironmentProfile(BaseModel):
    """A named environment profile with platform-specific settings."""

    name: str = Field(..., description="Profile name")
    platform: str = Field(default="desktop", description="Target platform")
    data_dir: str = Field(default="~/.jarvis", description="Data directory for this profile")
    config_overrides: Dict[str, Any] = Field(default_factory=dict, description="Config overrides")
    startup_services: List[str] = Field(default_factory=list, description="Services to start on launch")
    enabled_features: List[str] = Field(default_factory=list, description="Enabled feature flags")
    resource_limits: Dict[str, Any] = Field(default_factory=dict, description="Resource limits (cpu/memory/disk)")


class Package(BaseModel):
    """A deployable package containing bundled application files."""

    id: str = Field(..., description="Unique package identifier")
    version: str = Field(..., description="Package version string")
    format: str = Field(default="zip", description="Archive format")
    files: List[str] = Field(default_factory=list, description="List of file paths in the package")
    checksum: str = Field(default="", description="SHA-256 checksum of the package archive")
    size_bytes: int = Field(default=0, description="Package archive size in bytes")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary metadata")


class DeploymentState(BaseModel):
    """Current deployment state for the application."""

    environment: str = Field(default="development", description="Current environment")
    platform: str = Field(default="desktop", description="Current platform")
    current_version: str = Field(default="", description="Currently deployed version")
    previous_version: Optional[str] = Field(default=None, description="Previous deployed version")
    uptime_seconds: float = Field(default=0.0, description="Service uptime in seconds")
    last_deployed: Optional[datetime] = Field(default=None, description="Last deployment timestamp")
    last_health_check: Optional[datetime] = Field(default=None, description="Last health check timestamp")
    healthy: bool = Field(default=True, description="Overall health status")
    active_profile: Optional[str] = Field(default=None, description="Active profile name")


class HealthCheckResult(BaseModel):
    """Result of a health check operation."""

    status: str = Field(default="healthy", description="Overall status: healthy/degraded/unhealthy")
    service_checks: List[Dict[str, Any]] = Field(default_factory=list, description="Per-service check results")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional details")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UpdateManifest(BaseModel):
    """Describes an available update."""

    version: str = Field(..., description="Update version")
    release_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Release date")
    changelog: List[str] = Field(default_factory=list, description="List of changes")
    download_url: str = Field(default="", description="URL to download the update")
    checksum: str = Field(default="", description="Expected SHA-256 checksum")
    required_version: str = Field(default="", description="Minimum current version required")
    min_api_version: str = Field(default="", description="Minimum API version required")
    breaking_changes: List[str] = Field(default_factory=list, description="List of breaking changes")
