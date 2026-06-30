"""
app/skills/files/ — File Manager

Virtual file system, read/write, directory navigation, file metadata,
search, trash/recovery, document indexing, import/export (zip/tar).
"""

from .virtual_fs import VirtualFileSystem, FileItem, DirectoryEntry
from .file_search import FileSearchEngine
from .trash_manager import TrashManager
from .service import FileManagerService, FileManagerConfig

__all__ = [
    "VirtualFileSystem",
    "FileItem",
    "DirectoryEntry",
    "FileSearchEngine",
    "TrashManager",
    "FileManagerService",
    "FileManagerConfig",
]
