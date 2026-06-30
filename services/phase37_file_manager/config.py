"""
Phase 37 — File Manager Configuration.
"""

from typing import List
from pydantic import Field
from services.base.config_base import BaseConfig


class FileManagerConfig(BaseConfig):
    """Configuration for the file manager service."""

    service_name: str = Field(default="jarvis_file_manager", description="File manager service name")
    base_path: str = Field(default="/tmp/jarvis_files", description="Base path for file operations")
    enable_virtual_fs: bool = Field(default=True, description="Enable virtual filesystem")
    max_file_size_mb: int = Field(default=50, ge=1, le=1024, description="Max file size in MB")
    enable_trash: bool = Field(default=True, description="Enable trash/recovery")
    trash_retention_days: int = Field(default=7, ge=1, le=365, description="Days to keep trashed files")
    enable_search_index: bool = Field(default=True, description="Enable search indexing")
    enable_file_watch: bool = Field(default=False, description="Enable file watching")
    enable_compression: bool = Field(default=False, description="Enable file compression")
    allowed_extensions: List[str] = Field(default_factory=list, description="Allowed file extensions (empty=all)")
    blocked_extensions: List[str] = Field(default_factory=lambda: [".exe", ".bat", ".sh", ".dll"],
                                           description="Blocked file extensions")

    model_config = {"env_prefix": "JARVIS_PHASE37_"}
