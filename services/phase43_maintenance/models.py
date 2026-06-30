"""
Phase 43 — Maintenance Models.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Version(BaseModel):
    """Software version descriptor."""

    major: int = Field(default=1, ge=0, description="Major version number")
    minor: int = Field(default=0, ge=0, description="Minor version number")
    patch: int = Field(default=0, ge=0, description="Patch version number")
    build: Optional[str] = Field(default=None, description="Build identifier")
    release_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Release date")
    changelog: List[str] = Field(default_factory=list, description="Changelog entries for this version")
    is_stable: bool = Field(default=True, description="Whether this is a stable release")
    compatibility: Dict[str, str] = Field(default_factory=dict, description="Compatibility map (component: version)")
    api_version: Optional[str] = Field(default=None, description="API version string")


class Backup(BaseModel):
    """Backup record."""

    id: str = Field(..., description="Unique backup identifier")
    name: str = Field(..., description="Human-readable backup name")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation timestamp")
    size_bytes: int = Field(default=0, ge=0, description="Backup size in bytes")
    entries_count: int = Field(default=0, ge=0, description="Number of backed-up entries")
    type: str = Field(default="full", description="Backup type: full or incremental")
    checksum: str = Field(default="", description="Backup integrity checksum (SHA256)")
    path: str = Field(default="", description="File path to backup data")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class MigrationScript(BaseModel):
    """Database or schema migration script record."""

    id: str = Field(..., description="Unique migration identifier")
    name: str = Field(..., description="Migration script name")
    version_from: str = Field(..., description="Source version")
    version_to: str = Field(..., description="Target version")
    description: str = Field(default="", description="Change description")
    script_path: str = Field(default="", description="Path to migration script file")
    checksum: str = Field(default="", description="Script content checksum")
    applied_at: Optional[datetime] = Field(default=None, description="When the migration was applied")
    duration_ms: int = Field(default=0, ge=0, description="Execution time in milliseconds")
    success: bool = Field(default=False, description="Whether migration succeeded")


class DeprecationNotice(BaseModel):
    """Notice about a deprecated item."""

    item_name: str = Field(..., description="Name of the deprecated item")
    item_type: str = Field(default="api", description="Type: api, feature, config, or endpoint")
    deprecated_in_version: str = Field(..., description="Version in which it was deprecated")
    removal_in_version: str = Field(..., description="Version in which it will be removed")
    alternative: Optional[str] = Field(default=None, description="Recommended replacement")
    notice: str = Field(default="", description="Detailed deprecation notice")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Notice creation time")


class DiagnosticReport(BaseModel):
    """System diagnostic report."""

    id: str = Field(..., description="Unique report identifier")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="When the diagnostic ran")
    service_health: Dict[str, Any] = Field(default_factory=dict, description="Health status per service")
    error_counts: Dict[str, int] = Field(default_factory=dict, description="Error counts by category")
    resource_usage: Dict[str, Any] = Field(default_factory=dict, description="CPU, memory, disk usage")
    recommendations: List[str] = Field(default_factory=list, description="Suggested improvements")
    system_info: Dict[str, Any] = Field(default_factory=dict, description="System information snapshot")
