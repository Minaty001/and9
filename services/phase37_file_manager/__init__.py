"""
Phase 37 — File Manager
========================

Virtual file system, read/write, directory navigation, file metadata,
search, trash/recovery.

Components:
    - VirtualFileSystem: In-memory virtual filesystem with CRUD operations
    - FileSearchEngine: Index and search files by content/name/metadata
    - TrashManager: Move to trash, restore, empty trash, cleanup
    - FileManagerService: ServiceBase wrapper
"""

from .config import FileManagerConfig
from .models import FileItem, FileOperationResult, DirectoryEntry
from .virtual_fs import VirtualFileSystem
from .file_search import FileSearchEngine
from .trash_manager import TrashManager
from .service import FileManagerService

__all__ = [
    "FileManagerConfig",
    "FileItem",
    "FileOperationResult",
    "DirectoryEntry",
    "VirtualFileSystem",
    "FileSearchEngine",
    "TrashManager",
    "FileManagerService",
]
