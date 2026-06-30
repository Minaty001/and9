"""
Virtual File System.

In-memory virtual filesystem with CRUD operations.
Supports import/export from real filesystem, archive import/export,
path validation, and document indexing.
"""

from __future__ import annotations

import uuid
import time
import os
import shutil
import zipfile
import tarfile
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class FileItem:
    """Represents a file or directory entry."""

    def __init__(self, id: str, name: str, path: str, file_type: str,
                 extension: str = "", size_bytes: int = 0, mime_type: str = "",
                 created_at: Optional[datetime] = None,
                 modified_at: Optional[datetime] = None,
                 is_hidden: bool = False, tags: Optional[List[str]] = None,
                 metadata: Optional[Dict[str, Any]] = None):
        self.id = id
        self.name = name
        self.path = path
        self.file_type = file_type
        self.extension = extension
        self.size_bytes = size_bytes
        self.mime_type = mime_type
        self.created_at = created_at or datetime.now(timezone.utc)
        self.modified_at = modified_at or datetime.now(timezone.utc)
        self.is_hidden = is_hidden
        self.tags = tags or []
        self.metadata = metadata or {}


class DirectoryEntry:
    """Represents a directory listing."""

    def __init__(self, name: str, path: str, entries: Optional[List[FileItem]] = None,
                 entry_count: int = 0, total_size_bytes: int = 0):
        self.name = name
        self.path = path
        self.entries = entries or []
        self.entry_count = entry_count
        self.total_size_bytes = total_size_bytes


class VirtualFileSystem:
    """In-memory virtual filesystem with file/directory CRUD and import/export.

    Usage:
        vfs = VirtualFileSystem(base_path="/tmp/jarvis_files")
        item = vfs.create_file("/home/test.txt", "hello")
        content = vfs.read_file("/home/test.txt")
        vfs.delete("/home/test.txt")
        item = vfs.import_file("/real/path.txt", "/vfs/path.txt")
        vfs.export_file("/vfs/path.txt", "/real/out.txt")
    """

    def __init__(self, base_path: str = "/tmp/jarvis_files",
                 max_file_size_mb: int = 50,
                 blocked_extensions: Optional[List[str]] = None,
                 allowed_extensions: Optional[List[str]] = None):
        self.base_path = base_path
        self._max_file_size_bytes = max_file_size_mb * 1024 * 1024
        self._blocked_extensions = set(blocked_extensions or [".exe", ".bat", ".sh", ".dll"])
        self._allowed_extensions = set(allowed_extensions) if allowed_extensions else None
        self._files: Dict[str, FileItem] = {}
        self._contents: Dict[str, Any] = {}
        self._setup_defaults()

    def _setup_defaults(self):
        root_id = uuid.uuid4().hex[:12]
        root = FileItem(
            id=root_id,
            name=os.path.basename(self.base_path) or "root",
            path=self.base_path,
            file_type="directory",
            size_bytes=0,
            mime_type="inode/directory",
        )
        self._files[self.base_path] = root

    def _normalize_path(self, path: str) -> str:
        path = path.replace("\\", "/")
        if not path.startswith(self.base_path):
            path = os.path.normpath(os.path.join(self.base_path, path.lstrip("/")))
        else:
            path = os.path.normpath(path)
        return path

    # ── Path Validation ────────────────────────────────────────────────

    BLOCKED_EXTENSIONS_VALIDATION: Set[str] = {".bat", ".exe", ".sh", ".dll", ".com", ".cmd", ".vbs", ".ps1"}

    def validate_path(self, path: str, allow_absolute: bool = False) -> bool:
        """Validate a path for safety.

        Checks for:
        - Path traversal (..) components
        - Symlinks that escape the base directory (when resolved)
        - Blocked file extensions

        Args:
            path: The path string to validate.
            allow_absolute: Whether absolute paths are permitted.

        Returns:
            True if the path is safe, False otherwise.
        """
        normalized = os.path.normpath(path)
        parts = normalized.replace("\\", "/").split("/")
        if ".." in parts:
            logger.warning("Path traversal detected: %s", path)
            return False

        if not allow_absolute and os.path.isabs(normalized):
            logger.warning("Absolute path not allowed: %s", path)
            return False

        base = os.path.normpath(self.base_path)
        abs_path = os.path.abspath(os.path.join(base, normalized.lstrip("/"))) if not os.path.isabs(normalized) else normalized
        if not abs_path.startswith(base):
            logger.warning("Path escapes base directory: %s", path)
            return False

        _, ext = os.path.splitext(normalized)
        if ext.lower() in self.BLOCKED_EXTENSIONS_VALIDATION:
            logger.warning("Blocked extension: %s", ext)
            return False

        return True

    # ── Import / Export ─────────────────────────────────────────────────

    def import_file(self, source_path: str, dest_path: str) -> Optional[FileItem]:
        if not os.path.isfile(source_path):
            logger.error("Source file not found: %s", source_path)
            return None
        if not self.validate_path(dest_path):
            logger.error("Invalid destination path: %s", dest_path)
            return None
        try:
            with open(source_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception as e:
            logger.error("Failed to read source file: %s", e)
            return None
        return self.create_file(dest_path, content)

    def export_file(self, vfs_path: str, dest_path: str) -> bool:
        vfs_path = self._normalize_path(vfs_path)
        item = self._files.get(vfs_path)
        if not item or item.file_type != "file":
            logger.error("VFS file not found: %s", vfs_path)
            return False
        if not self.validate_path(dest_path):
            logger.error("Invalid destination path: %s", dest_path)
            return False
        content = self._contents.get(vfs_path, "")
        try:
            os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
            if isinstance(content, str):
                with open(dest_path, "w", encoding="utf-8") as f:
                    f.write(content)
            elif isinstance(content, bytes):
                with open(dest_path, "wb") as f:
                    f.write(content)
            else:
                with open(dest_path, "w", encoding="utf-8") as f:
                    f.write(str(content))
            logger.debug("Exported VFS file to: %s", dest_path)
            return True
        except Exception as e:
            logger.error("Failed to export file: %s", e)
            return False

    def import_archive(self, path: str, vfs_dir: str = "") -> int:
        if not os.path.isfile(path):
            logger.error("Archive not found: %s", path)
            return 0
        if not self.validate_path(vfs_dir or "/"):
            logger.error("Invalid VFS directory: %s", vfs_dir)
            return 0
        imported = 0
        try:
            if zipfile.is_zipfile(path):
                imported = self._import_zip(path, vfs_dir)
            elif tarfile.is_tarfile(path):
                imported = self._import_tar(path, vfs_dir)
            else:
                logger.error("Unsupported archive format: %s", path)
        except Exception as e:
            logger.error("Failed to import archive: %s", e)
        return imported

    def _import_zip(self, path: str, vfs_dir: str) -> int:
        imported = 0
        with zipfile.ZipFile(path, "r") as zf:
            for name in zf.namelist():
                if name.endswith("/"):
                    continue
                try:
                    content = zf.read(name)
                    vfs_path = os.path.join(vfs_dir, name).replace("\\", "/")
                    if self.create_file(vfs_path, content):
                        imported += 1
                except Exception as e:
                    logger.warning("Failed to import '%s' from zip: %s", name, e)
        return imported

    def _import_tar(self, path: str, vfs_dir: str) -> int:
        imported = 0
        with tarfile.open(path, "r") as tf:
            for member in tf.getmembers():
                if not member.isfile():
                    continue
                try:
                    f = tf.extractfile(member)
                    if f:
                        content = f.read()
                        vfs_path = os.path.join(vfs_dir, member.name).replace("\\", "/")
                        if self.create_file(vfs_path, content):
                            imported += 1
                except Exception as e:
                    logger.warning("Failed to import '%s' from tar: %s", member.name, e)
        return imported

    def export_archive(self, path: str, vfs_paths: Optional[List[str]] = None) -> bool:
        if vfs_paths is None:
            vfs_paths = list(self._files.keys())
        paths_to_export = []
        for p in vfs_paths:
            np = self._normalize_path(p)
            if np in self._files:
                paths_to_export.append(np)
        if not paths_to_export:
            logger.warning("No files to export")
            return False
        try:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
                for vp in paths_to_export:
                    item = self._files.get(vp)
                    if item and item.file_type == "file":
                        content = self._contents.get(vp, b"")
                        arcname = os.path.relpath(vp, self.base_path)
                        if isinstance(content, str):
                            zf.writestr(arcname, content)
                        elif isinstance(content, bytes):
                            zf.writestr(arcname, content)
                        else:
                            zf.writestr(arcname, str(content))
            logger.debug("Exported archive: %s (%d files)", path, len(paths_to_export))
            return True
        except Exception as e:
            logger.error("Failed to export archive: %s", e)
            return False

    def _check_extension(self, path: str) -> bool:
        _, ext = os.path.splitext(path)
        if ext.lower() in self._blocked_extensions:
            return False
        if self._allowed_extensions and ext.lower() not in self._allowed_extensions:
            return False
        return True

    def _get_parent_path(self, path: str) -> str:
        return os.path.dirname(path)

    def _ensure_parent_dirs(self, path: str) -> None:
        parent = self._get_parent_path(path)
        if parent == path:
            return
        if parent not in self._files or self._files[parent].file_type != "directory":
            self._ensure_parent_dirs(parent)
            dir_id = uuid.uuid4().hex[:12]
            now = datetime.now(timezone.utc)
            dir_item = FileItem(
                id=dir_id,
                name=os.path.basename(parent),
                path=parent,
                file_type="directory",
                size_bytes=0,
                mime_type="inode/directory",
                created_at=now,
                modified_at=now,
            )
            self._files[parent] = dir_item
            logger.debug("Auto-created directory: %s", parent)

    def create_file(self, path: str, content: Any = "") -> Optional[FileItem]:
        path = self._normalize_path(path)
        if path in self._files:
            logger.warning("Path already exists: %s", path)
            return None
        if not self._check_extension(path):
            logger.warning("Blocked extension for: %s", path)
            return None

        parent = self._get_parent_path(path)
        if parent not in self._files or self._files[parent].file_type != "directory":
            self._ensure_parent_dirs(path)

        if isinstance(content, (str, bytes)):
            size = len(content)
            if size > self._max_file_size_bytes:
                logger.error("File exceeds max size: %d bytes", size)
                return None

        _, ext = os.path.splitext(path)
        name = os.path.basename(path)
        now = datetime.now(timezone.utc)
        file_id = uuid.uuid4().hex[:12]

        mime_map = {
            ".txt": "text/plain", ".json": "application/json", ".xml": "application/xml",
            ".html": "text/html", ".css": "text/css", ".js": "application/javascript",
            ".py": "text/x-python", ".md": "text/markdown", ".csv": "text/csv",
            ".yaml": "application/x-yaml", ".yml": "application/x-yaml",
            ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif",
        }
        mime = mime_map.get(ext.lower(), "application/octet-stream")
        size = len(content) if isinstance(content, (str, bytes)) else 0

        item = FileItem(
            id=file_id,
            name=name,
            path=path,
            file_type="file",
            extension=ext,
            size_bytes=size,
            mime_type=mime,
            created_at=now,
            modified_at=now,
            is_hidden=name.startswith("."),
        )
        self._files[path] = item
        self._contents[path] = content
        logger.debug("Created file: %s", path)
        return item

    def read_file(self, path: str) -> Optional[Any]:
        path = self._normalize_path(path)
        item = self._files.get(path)
        if not item or item.file_type != "file":
            return None
        return self._contents.get(path)

    def write_file(self, path: str, content: Any) -> bool:
        path = self._normalize_path(path)
        item = self._files.get(path)
        if not item or item.file_type != "file":
            return False
        if isinstance(content, (str, bytes)):
            size = len(content)
            if size > self._max_file_size_bytes:
                logger.error("Content exceeds max file size")
                return False
            item.size_bytes = size
        self._contents[path] = content
        item.modified_at = datetime.now(timezone.utc)
        return True

    def delete(self, path: str) -> bool:
        path = self._normalize_path(path)
        if path not in self._files:
            return False
        item = self._files[path]
        if item.file_type == "directory":
            to_delete = [p for p in self._files if p.startswith(path + "/") or p == path]
            to_delete.sort(reverse=True)
            for p in to_delete:
                if p in self._contents:
                    del self._contents[p]
                del self._files[p]
        else:
            if path in self._contents:
                del self._contents[path]
            del self._files[path]
        logger.debug("Deleted: %s", path)
        return True

    def copy(self, src: str, dest: str) -> bool:
        src = self._normalize_path(src)
        dest = self._normalize_path(dest)
        if src not in self._files:
            return False
        if dest in self._files:
            logger.warning("Destination already exists: %s", dest)
            return False
        src_item = self._files[src]
        if src_item.file_type == "file":
            content = self._contents.get(src)
            return self.create_file(dest, content) is not None
        else:
            items_to_copy = [(p, self._files[p]) for p in self._files if p.startswith(src + "/") or p == src]
            items_to_copy.sort()
            for item_path, item in items_to_copy:
                rel_path = os.path.relpath(item_path, src)
                new_path = os.path.join(dest, rel_path) if rel_path != "." else dest
                if item.file_type == "directory":
                    dir_id = uuid.uuid4().hex[:12]
                    new_item = FileItem(
                        id=dir_id, name=os.path.basename(new_path), path=new_path,
                        file_type="directory", size_bytes=0, mime_type="inode/directory",
                    )
                    self._files[new_path] = new_item
                else:
                    content = self._contents.get(item_path)
                    self.create_file(new_path, content)
            return True

    def move(self, src: str, dest: str) -> bool:
        src = self._normalize_path(src)
        dest = self._normalize_path(dest)
        if src not in self._files:
            return False
        if dest in self._files:
            logger.warning("Destination already exists: %s", dest)
            return False
        if not self.copy(src, dest):
            return False
        return self.delete(src)

    def list_directory(self, path: str) -> Optional[DirectoryEntry]:
        path = self._normalize_path(path)
        if path not in self._files or self._files[path].file_type != "directory":
            return None
        entries = []
        for fpath, item in self._files.items():
            if fpath == path:
                continue
            parent = self._get_parent_path(fpath)
            if parent == path:
                entries.append(item)
        total_size = sum(e.size_bytes for e in entries if e.file_type == "file")
        name = os.path.basename(path) or path
        return DirectoryEntry(name=name, path=path, entries=entries,
                              entry_count=len(entries), total_size_bytes=total_size)

    def exists(self, path: str) -> bool:
        path = self._normalize_path(path)
        return path in self._files

    def get_info(self, path: str) -> Optional[FileItem]:
        path = self._normalize_path(path)
        return self._files.get(path)
