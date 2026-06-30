"""
Phase 37 — File Manager Models.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class FileItem(BaseModel):
    """Represents a file or directory entry."""

    id: str = Field(..., description="Unique identifier")
    name: str = Field(..., description="File or directory name")
    path: str = Field(..., description="Full path")
    file_type: str = Field(..., description="Type: file or directory")
    extension: str = Field(default="", description="File extension")
    size_bytes: int = Field(default=0, ge=0, description="Size in bytes")
    mime_type: str = Field(default="", description="MIME type")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    modified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_hidden: bool = Field(default=False, description="Whether the file is hidden")
    tags: List[str] = Field(default_factory=list, description="User-defined tags")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class FileOperationResult(BaseModel):
    """Result of a file operation."""

    success: bool = Field(..., description="Whether the operation succeeded")
    operation: str = Field(..., description="Operation type: read/write/delete/copy/move/search")
    path: str = Field(default="", description="Path involved")
    error: str = Field(default="", description="Error message if failed")
    duration_ms: float = Field(default=0.0, description="Operation duration in milliseconds")
    file_item: Optional[FileItem] = Field(default=None, description="Resulting file item if applicable")


class DirectoryEntry(BaseModel):
    """Represents a directory listing."""

    name: str = Field(..., description="Directory name")
    path: str = Field(..., description="Directory path")
    entries: List[FileItem] = Field(default_factory=list, description="Files and subdirectories")
    entry_count: int = Field(default=0, description="Number of entries")
    total_size_bytes: int = Field(default=0, description="Total size of all entries in bytes")
