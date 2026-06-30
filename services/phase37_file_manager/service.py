"""
Phase 37 — File Manager Service.

ServiceBase wrapper for the File Manager service.
"""

from __future__ import annotations

import time
import logging
from typing import Any, Dict, List, Optional

from services.base.service_base import ServiceBase
from .config import FileManagerConfig
from .models import FileItem, FileOperationResult, DirectoryEntry
from .virtual_fs import VirtualFileSystem
from .file_search import FileSearchEngine
from .trash_manager import TrashManager

logger = logging.getLogger(__name__)


class FileManagerService(ServiceBase):
    """File manager service for virtual file operations.

    Usage:
        svc = FileManagerService()
        await svc.initialize()
        item = svc.create_file("/test.txt", "hello")
        content = svc.read_file("/test.txt")
    """

    def __init__(self, config: Optional[FileManagerConfig] = None):
        super().__init__(name="jarvis_file_manager", version="1.0.0")
        self.config = config or FileManagerConfig()
        self.vfs: Optional[VirtualFileSystem] = None
        self.search_engine: Optional[FileSearchEngine] = None
        self.trash_manager: Optional[TrashManager] = None
        self._start_time = 0.0

    async def initialize(self) -> bool:
        self._start_time = time.time()
        try:
            self.vfs = VirtualFileSystem(self.config)
            self.search_engine = FileSearchEngine(self.config)
            self.trash_manager = TrashManager(self.config)
            self._metrics.reset()
            self._initialized = True
            logger.info("FileManagerService initialized")
            return True
        except Exception as e:
            logger.error("FileManagerService init failed: %s", e)
            return False

    async def shutdown(self) -> None:
        logger.info("FileManagerService shutting down...")
        self._initialized = False

    # ── File Operations ────────────────────────────────────────────

    async def create_file(self, path: str, content: Any = "") -> Optional[FileItem]:
        if not self.vfs:
            raise RuntimeError("FileManagerService not initialized")
        t0 = time.perf_counter()
        item = self.vfs.create_file(path, content)
        elapsed = (time.perf_counter() - t0) * 1000
        if item:
            if self.search_engine:
                self.search_engine.index_file(path, item, str(content) if content else "")
            self._metrics.counter("files_created", 1)
        self._metrics.histogram("operation_time_ms", elapsed)
        return item

    async def read_file(self, path: str) -> Optional[Any]:
        if not self.vfs:
            raise RuntimeError("FileManagerService not initialized")
        t0 = time.perf_counter()
        content = self.vfs.read_file(path)
        elapsed = (time.perf_counter() - t0) * 1000
        if content is not None:
            self._metrics.counter("files_read", 1)
        self._metrics.histogram("operation_time_ms", elapsed)
        return content

    async def write_file(self, path: str, content: Any) -> bool:
        if not self.vfs:
            raise RuntimeError("FileManagerService not initialized")
        t0 = time.perf_counter()
        result = self.vfs.write_file(path, content)
        elapsed = (time.perf_counter() - t0) * 1000
        item = self.vfs.get_info(path)
        if result and self.search_engine and item:
            self.search_engine.index_file(path, item, str(content) if content else "")
            self._metrics.counter("files_written", 1)
        self._metrics.histogram("operation_time_ms", elapsed)
        return result

    async def delete_file(self, path: str) -> bool:
        if not self.vfs:
            raise RuntimeError("FileManagerService not initialized")
        t0 = time.perf_counter()
        item = self.vfs.get_info(path)
        if item and self.trash_manager:
            self.trash_manager.move_to_trash(path, item)
        result = self.vfs.delete(path)
        elapsed = (time.perf_counter() - t0) * 1000
        if result:
            self._metrics.counter("files_deleted", 1)
        self._metrics.histogram("operation_time_ms", elapsed)
        return result

    async def copy(self, src: str, dest: str) -> bool:
        if not self.vfs:
            raise RuntimeError("FileManagerService not initialized")
        t0 = time.perf_counter()
        result = self.vfs.copy(src, dest)
        elapsed = (time.perf_counter() - t0) * 1000
        if result:
            self._metrics.counter("files_copied", 1)
        self._metrics.histogram("operation_time_ms", elapsed)
        return result

    async def move(self, src: str, dest: str) -> bool:
        if not self.vfs:
            raise RuntimeError("FileManagerService not initialized")
        t0 = time.perf_counter()
        result = self.vfs.move(src, dest)
        elapsed = (time.perf_counter() - t0) * 1000
        if result:
            self._metrics.counter("files_moved", 1)
        self._metrics.histogram("operation_time_ms", elapsed)
        return result

    async def move_to_trash(self, path: str) -> bool:
        if not self.vfs or not self.trash_manager:
            raise RuntimeError("FileManagerService not initialized")
        item = self.vfs.get_info(path)
        if not item:
            return False
        result = self.trash_manager.move_to_trash(path, item)
        if result:
            self.vfs.delete(path)
        return result

    async def list_directory(self, path: str) -> Optional[DirectoryEntry]:
        if not self.vfs:
            raise RuntimeError("FileManagerService not initialized")
        return self.vfs.list_directory(path)

    # ── Search ──────────────────────────────────────────────────────

    async def search(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        if not self.search_engine:
            raise RuntimeError("FileManagerService not initialized")
        return self.search_engine.search(query, filters)

    async def index_document(self, path: str, content: str) -> bool:
        """Index a document with MIME-based metadata for targeted search.

        The path must correspond to an existing file in the VFS.
        """
        if not self.search_engine or not self.vfs:
            raise RuntimeError("FileManagerService not initialized")
        item = self.vfs.get_info(path)
        if not item:
            return False
        return self.search_engine.index_document(item, content)

    async def search_documents(self, query: str, document_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search indexed documents, optionally filtered by document type."""
        if not self.search_engine:
            raise RuntimeError("FileManagerService not initialized")
        return self.search_engine.search_documents(query, document_type)

    async def reindex_documents(self) -> int:
        """Clear and re-index all documents.

        Returns the count of previously indexed documents that were cleared.
        """
        if not self.search_engine:
            raise RuntimeError("FileManagerService not initialized")
        return self.search_engine.reindex_documents()

    # ── Trash Operations ────────────────────────────────────────────

    async def list_trash(self) -> List[Dict[str, Any]]:
        if not self.trash_manager:
            raise RuntimeError("FileManagerService not initialized")
        return self.trash_manager.list_trash()

    async def restore_from_trash(self, path: str) -> bool:
        if not self.trash_manager:
            raise RuntimeError("FileManagerService not initialized")
        return self.trash_manager.restore(path)

    async def empty_trash(self) -> int:
        if not self.trash_manager:
            raise RuntimeError("FileManagerService not initialized")
        return self.trash_manager.empty_trash()

    async def recover_file(self, trash_id: str) -> Optional[FileItem]:
        if not self.trash_manager:
            raise RuntimeError("FileManagerService not initialized")
        return self.trash_manager.recover_file(trash_id)

    async def cleanup_expired_trash(self) -> int:
        if not self.trash_manager:
            raise RuntimeError("FileManagerService not initialized")
        return self.trash_manager.cleanup_expired()

    # ── Info ────────────────────────────────────────────────────────

    async def get_info(self, path: str) -> Optional[FileItem]:
        if not self.vfs:
            raise RuntimeError("FileManagerService not initialized")
        return self.vfs.get_info(path)

    # ── Import / Export ────────────────────────────────────────────────

    async def import_file(self, source_path: str, dest_path: str) -> Optional[FileItem]:
        """Copy a real file from the filesystem into the VFS."""
        if not self.vfs:
            raise RuntimeError("FileManagerService not initialized")
        t0 = time.perf_counter()
        item = self.vfs.import_file(source_path, dest_path)
        elapsed = (time.perf_counter() - t0) * 1000
        if item:
            self._metrics.counter("files_imported", 1)
        self._metrics.histogram("operation_time_ms", elapsed)
        return item

    async def export_file(self, vfs_path: str, dest_path: str) -> bool:
        """Copy a VFS file to the real filesystem."""
        if not self.vfs:
            raise RuntimeError("FileManagerService not initialized")
        t0 = time.perf_counter()
        result = self.vfs.export_file(vfs_path, dest_path)
        elapsed = (time.perf_counter() - t0) * 1000
        if result:
            self._metrics.counter("files_exported", 1)
        self._metrics.histogram("operation_time_ms", elapsed)
        return result

    async def import_archive(self, path: str, vfs_dir: str = "") -> int:
        """Import files from a zip/tar archive into the VFS."""
        if not self.vfs:
            raise RuntimeError("FileManagerService not initialized")
        t0 = time.perf_counter()
        count = self.vfs.import_archive(path, vfs_dir)
        elapsed = (time.perf_counter() - t0) * 1000
        if count:
            self._metrics.counter("archive_imports", 1)
        self._metrics.histogram("operation_time_ms", elapsed)
        return count

    async def export_archive(self, path: str, vfs_paths: Optional[List[str]] = None) -> bool:
        """Export VFS files to a zip archive."""
        if not self.vfs:
            raise RuntimeError("FileManagerService not initialized")
        t0 = time.perf_counter()
        result = self.vfs.export_archive(path, vfs_paths)
        elapsed = (time.perf_counter() - t0) * 1000
        if result:
            self._metrics.counter("archive_exports", 1)
        self._metrics.histogram("operation_time_ms", elapsed)
        return result

    # ── Path Validation ────────────────────────────────────────────────

    async def validate_path(self, path: str, allow_absolute: bool = False) -> bool:
        """Validate a path for safety (traversal, blocked extensions, etc.)."""
        if not self.vfs:
            raise RuntimeError("FileManagerService not initialized")
        return self.vfs.validate_path(path, allow_absolute)

    async def get_stats(self) -> Dict[str, Any]:
        if not self.vfs:
            raise RuntimeError("FileManagerService not initialized")
        files = [v for v in self.vfs._files.values() if v.file_type == "file"]
        dirs = [v for v in self.vfs._files.values() if v.file_type == "directory"]
        return {
            "total_files": len(files),
            "total_directories": len(dirs),
            "total_size_bytes": sum(f.size_bytes for f in files),
            "trash_count": len(self.trash_manager._trash) if self.trash_manager else 0,
        }

    # ── Health / Stats ─────────────────────────────────────────────

    async def health(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        stats = await self.get_stats() if self.vfs else {}
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "service_name": self.name,
            "version": self.version,
            "initialized": self._initialized,
            "uptime_seconds": round(uptime, 1),
            "total_files": stats.get("total_files", 0),
            "total_directories": stats.get("total_directories", 0),
        }

    async def stats(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        fs_stats = await self.get_stats() if self.vfs else {}
        search_stats = self.search_engine.get_index_stats() if self.search_engine else {}
        return {
            "service": self.name,
            "version": self.version,
            "uptime_seconds": round(uptime, 1),
            "filesystem": fs_stats,
            "search_index": search_stats,
            "metrics": self._metrics.snapshot(),
        }
