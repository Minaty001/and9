"""
File Manager Service.

Wrapper around VirtualFileSystem, FileSearchEngine, and TrashManager
providing a unified async service interface.
"""

from __future__ import annotations

import time
import logging
from typing import Any, Dict, List, Optional

from .virtual_fs import VirtualFileSystem, FileItem, DirectoryEntry
from .file_search import FileSearchEngine
from .trash_manager import TrashManager

logger = logging.getLogger(__name__)


class FileManagerConfig:
    """Configuration for FileManagerService.

    All fields have defaults; pass as keyword args or override after construction.
    """

    def __init__(self,
                 service_name: str = "jarvis_file_manager",
                 base_path: str = "/tmp/jarvis_files",
                 max_file_size_mb: int = 50,
                 blocked_extensions: Optional[List[str]] = None,
                 allowed_extensions: Optional[List[str]] = None,
                 trash_retention_days: int = 7):
        self.service_name = service_name
        self.base_path = base_path
        self.max_file_size_mb = max_file_size_mb
        self.blocked_extensions = blocked_extensions or [".exe", ".bat", ".sh", ".dll"]
        self.allowed_extensions = allowed_extensions or []
        self.trash_retention_days = trash_retention_days


class FileManagerService:
    """File manager service for virtual file operations.

    Usage:
        svc = FileManagerService()
        await svc.initialize()
        item = svc.create_file("/test.txt", "hello")
        content = svc.read_file("/test.txt")
    """

    def __init__(self, config: Optional[FileManagerConfig] = None):
        self.config = config or FileManagerConfig()
        self.vfs: Optional[VirtualFileSystem] = None
        self.search_engine: Optional[FileSearchEngine] = None
        self.trash_manager: Optional[TrashManager] = None
        self._initialized = False
        self._start_time = 0.0
        self._counters: Dict[str, int] = {
            "files_created": 0, "files_read": 0, "files_written": 0,
            "files_deleted": 0, "files_copied": 0, "files_moved": 0,
            "files_imported": 0, "files_exported": 0, "archive_imports": 0,
            "archive_exports": 0,
        }
        self._operation_times: List[float] = []

    async def initialize(self) -> bool:
        self._start_time = time.time()
        try:
            self.vfs = VirtualFileSystem(
                base_path=self.config.base_path,
                max_file_size_mb=self.config.max_file_size_mb,
                blocked_extensions=self.config.blocked_extensions.copy(),
                allowed_extensions=self.config.allowed_extensions.copy() if self.config.allowed_extensions else None,
            )
            self.search_engine = FileSearchEngine()
            self.trash_manager = TrashManager(retention_days=self.config.trash_retention_days)
            self._initialized = True
            logger.info("FileManagerService initialized")
            return True
        except Exception as e:
            logger.error("FileManagerService init failed: %s", e)
            return False

    async def shutdown(self) -> None:
        logger.info("FileManagerService shutting down...")
        self._initialized = False

    def _check_init(self):
        if not self._initialized:
            raise RuntimeError("FileManagerService not initialized")

    def _track_operation(self, counter_name: str, elapsed_ms: float):
        self._counters[counter_name] = self._counters.get(counter_name, 0) + 1
        self._operation_times.append(elapsed_ms)

    # ── File Operations ────────────────────────────────────────────

    async def create_file(self, path: str, content: Any = "") -> Optional[FileItem]:
        self._check_init()
        t0 = time.perf_counter()
        item = self.vfs.create_file(path, content)
        elapsed = (time.perf_counter() - t0) * 1000
        if item:
            if self.search_engine:
                self.search_engine.index_file(path, item, str(content) if content else "")
            self._track_operation("files_created", elapsed)
        return item

    async def read_file(self, path: str) -> Optional[Any]:
        self._check_init()
        t0 = time.perf_counter()
        content = self.vfs.read_file(path)
        elapsed = (time.perf_counter() - t0) * 1000
        if content is not None:
            self._track_operation("files_read", elapsed)
        return content

    async def write_file(self, path: str, content: Any) -> bool:
        self._check_init()
        t0 = time.perf_counter()
        result = self.vfs.write_file(path, content)
        elapsed = (time.perf_counter() - t0) * 1000
        item = self.vfs.get_info(path)
        if result and self.search_engine and item:
            self.search_engine.index_file(path, item, str(content) if content else "")
            self._track_operation("files_written", elapsed)
        return result

    async def delete_file(self, path: str) -> bool:
        self._check_init()
        t0 = time.perf_counter()
        item = self.vfs.get_info(path)
        if item and self.trash_manager:
            self.trash_manager.move_to_trash(path, item)
        result = self.vfs.delete(path)
        elapsed = (time.perf_counter() - t0) * 1000
        if result:
            self._track_operation("files_deleted", elapsed)
        return result

    async def copy(self, src: str, dest: str) -> bool:
        self._check_init()
        t0 = time.perf_counter()
        result = self.vfs.copy(src, dest)
        elapsed = (time.perf_counter() - t0) * 1000
        if result:
            self._track_operation("files_copied", elapsed)
        return result

    async def move(self, src: str, dest: str) -> bool:
        self._check_init()
        t0 = time.perf_counter()
        result = self.vfs.move(src, dest)
        elapsed = (time.perf_counter() - t0) * 1000
        if result:
            self._track_operation("files_moved", elapsed)
        return result

    async def move_to_trash(self, path: str) -> bool:
        self._check_init()
        item = self.vfs.get_info(path)
        if not item:
            return False
        result = self.trash_manager.move_to_trash(path, item)
        if result:
            self.vfs.delete(path)
        return result

    async def list_directory(self, path: str) -> Optional[DirectoryEntry]:
        self._check_init()
        return self.vfs.list_directory(path)

    # ── Search ──────────────────────────────────────────────────────

    async def search(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        self._check_init()
        return self.search_engine.search(query, filters)

    async def index_document(self, path: str, content: str) -> bool:
        self._check_init()
        item = self.vfs.get_info(path)
        if not item:
            return False
        return self.search_engine.index_document(item, content)

    async def search_documents(self, query: str, document_type: Optional[str] = None) -> List[Dict[str, Any]]:
        self._check_init()
        return self.search_engine.search_documents(query, document_type)

    async def reindex_documents(self) -> int:
        self._check_init()
        return self.search_engine.reindex_documents()

    # ── Trash Operations ────────────────────────────────────────────

    async def list_trash(self) -> List[Dict[str, Any]]:
        self._check_init()
        return self.trash_manager.list_trash()

    async def restore_from_trash(self, path: str) -> bool:
        self._check_init()
        return self.trash_manager.restore(path)

    async def empty_trash(self) -> int:
        self._check_init()
        return self.trash_manager.empty_trash()

    async def recover_file(self, trash_id: str) -> Optional[FileItem]:
        self._check_init()
        return self.trash_manager.recover_file(trash_id)

    async def cleanup_expired_trash(self) -> int:
        self._check_init()
        return self.trash_manager.cleanup_expired()

    # ── Info ────────────────────────────────────────────────────────

    async def get_info(self, path: str) -> Optional[FileItem]:
        self._check_init()
        return self.vfs.get_info(path)

    async def exists(self, path: str) -> bool:
        self._check_init()
        return self.vfs.exists(path)

    # ── Import / Export ────────────────────────────────────────────────

    async def import_file(self, source_path: str, dest_path: str) -> Optional[FileItem]:
        self._check_init()
        t0 = time.perf_counter()
        item = self.vfs.import_file(source_path, dest_path)
        elapsed = (time.perf_counter() - t0) * 1000
        if item:
            self._track_operation("files_imported", elapsed)
        return item

    async def export_file(self, vfs_path: str, dest_path: str) -> bool:
        self._check_init()
        t0 = time.perf_counter()
        result = self.vfs.export_file(vfs_path, dest_path)
        elapsed = (time.perf_counter() - t0) * 1000
        if result:
            self._track_operation("files_exported", elapsed)
        return result

    async def import_archive(self, path: str, vfs_dir: str = "") -> int:
        self._check_init()
        t0 = time.perf_counter()
        count = self.vfs.import_archive(path, vfs_dir)
        elapsed = (time.perf_counter() - t0) * 1000
        if count:
            self._track_operation("archive_imports", elapsed)
        return count

    async def export_archive(self, path: str, vfs_paths: Optional[List[str]] = None) -> bool:
        self._check_init()
        t0 = time.perf_counter()
        result = self.vfs.export_archive(path, vfs_paths)
        elapsed = (time.perf_counter() - t0) * 1000
        if result:
            self._track_operation("archive_exports", elapsed)
        return result

    # ── Path Validation ────────────────────────────────────────────────

    async def validate_path(self, path: str, allow_absolute: bool = False) -> bool:
        self._check_init()
        return self.vfs.validate_path(path, allow_absolute)

    # ── Health / Stats ─────────────────────────────────────────────

    async def get_stats(self) -> Dict[str, Any]:
        self._check_init()
        files = [v for v in self.vfs._files.values() if v.file_type == "file"]
        dirs = [v for v in self.vfs._files.values() if v.file_type == "directory"]
        return {
            "total_files": len(files),
            "total_directories": len(dirs),
            "total_size_bytes": sum(f.size_bytes for f in files),
            "trash_count": len(self.trash_manager._trash) if self.trash_manager else 0,
        }

    async def health(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        stats = await self.get_stats() if self._initialized else {}
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "service_name": getattr(self.config, "service_name", "jarvis_file_manager"),
            "initialized": self._initialized,
            "uptime_seconds": round(uptime, 1),
            "total_files": stats.get("total_files", 0),
            "total_directories": stats.get("total_directories", 0),
        }

    async def stats(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        fs_stats = await self.get_stats() if self._initialized else {}
        search_stats = self.search_engine.get_index_stats() if self.search_engine else {}
        return {
            "service": getattr(self.config, "service_name", "jarvis_file_manager"),
            "uptime_seconds": round(uptime, 1),
            "filesystem": fs_stats,
            "search_index": search_stats,
            "counters": dict(self._counters),
        }
