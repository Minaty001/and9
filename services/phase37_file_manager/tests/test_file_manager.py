"""
Tests for Phase 37 — File Manager.
"""

import pytest
from services.phase37_file_manager import (
    FileManagerConfig,
    FileItem,
    FileOperationResult,
    DirectoryEntry,
    VirtualFileSystem,
    FileSearchEngine,
    TrashManager,
    FileManagerService,
)


class TestVirtualFileSystem:
    """Verify VFS file/directory CRUD."""

    def test_create_file(self):
        vfs = VirtualFileSystem()
        item = vfs.create_file("/test.txt", "hello")
        assert item is not None
        assert item.name == "test.txt"
        assert item.file_type == "file"

    def test_read_file(self):
        vfs = VirtualFileSystem()
        vfs.create_file("/test.txt", "hello world")
        content = vfs.read_file("/test.txt")
        assert content == "hello world"

    def test_read_nonexistent(self):
        vfs = VirtualFileSystem()
        assert vfs.read_file("/nonexistent.txt") is None

    def test_write_file(self):
        vfs = VirtualFileSystem()
        vfs.create_file("/test.txt", "old")
        assert vfs.write_file("/test.txt", "new content") is True
        assert vfs.read_file("/test.txt") == "new content"

    def test_delete_file(self):
        vfs = VirtualFileSystem()
        vfs.create_file("/test.txt", "data")
        assert vfs.delete("/test.txt") is True
        assert vfs.exists("/test.txt") is False

    def test_delete_nonexistent(self):
        vfs = VirtualFileSystem()
        assert vfs.delete("/nonexistent") is False

    def test_copy_file(self):
        vfs = VirtualFileSystem()
        vfs.create_file("/src.txt", "data")
        assert vfs.copy("/src.txt", "/dst.txt") is True
        assert vfs.exists("/dst.txt") is True
        assert vfs.read_file("/dst.txt") == "data"

    def test_move_file(self):
        vfs = VirtualFileSystem()
        vfs.create_file("/src.txt", "data")
        assert vfs.move("/src.txt", "/dst.txt") is True
        assert vfs.exists("/src.txt") is False
        assert vfs.read_file("/dst.txt") == "data"

    def test_list_directory(self):
        vfs = VirtualFileSystem()
        vfs.create_file("/a.txt", "1")
        vfs.create_file("/b.txt", "2")
        entry = vfs.list_directory(vfs.config.base_path)
        assert entry is not None
        assert entry.entry_count == 2

    def test_exists(self):
        vfs = VirtualFileSystem()
        vfs.create_file("/test.txt", "x")
        assert vfs.exists("/test.txt") is True
        assert vfs.exists("/nonexistent") is False

    def test_get_info(self):
        vfs = VirtualFileSystem()
        vfs.create_file("/test.txt", "data")
        info = vfs.get_info("/test.txt")
        assert info is not None
        assert info.name == "test.txt"

    def test_blocked_extension(self):
        cfg = FileManagerConfig(blocked_extensions=[".exe"])
        vfs = VirtualFileSystem(cfg)
        item = vfs.create_file("/test.exe", "bad")
        assert item is None


class TestFileSearchEngine:
    """Verify search indexing and querying."""

    def test_index_and_search(self):
        engine = FileSearchEngine()
        item = FileItem(id="1", name="document.txt", path="/doc.txt", file_type="file",
                        extension=".txt", size_bytes=10, mime_type="text/plain")
        engine.index_file("/doc.txt", item, "hello world")
        results = engine.search("hello")
        assert len(results) >= 1
        assert results[0]["name"] == "document.txt"

    def test_search_no_results(self):
        engine = FileSearchEngine()
        results = engine.search("nonexistent")
        assert len(results) == 0

    def test_reindex(self):
        engine = FileSearchEngine()
        item = FileItem(id="1", name="a.txt", path="/a.txt", file_type="file",
                        extension=".txt", size_bytes=5, mime_type="text/plain")
        engine.index_file("/a.txt", item, "data")
        assert engine.reindex() == 1
        assert engine.get_index_stats()["indexed_files"] == 0

    def test_search_with_filters(self):
        engine = FileSearchEngine()
        item = FileItem(id="1", name="doc.txt", path="/doc.txt", file_type="file",
                        extension=".txt", size_bytes=10, mime_type="text/plain")
        engine.index_file("/doc.txt", item, "data")
        results = engine.search("data", filters={"file_type": "file"})
        assert len(results) == 1
        results = engine.search("data", filters={"file_type": "directory"})
        assert len(results) == 0


class TestTrashManager:
    """Verify trash/recovery operations."""

    def test_move_to_trash(self):
        mgr = TrashManager()
        item = FileItem(id="1", name="test.txt", path="/test.txt",
                        file_type="file", extension=".txt", size_bytes=10,
                        mime_type="text/plain")
        assert mgr.move_to_trash("/test.txt", item) is True

    def test_restore(self):
        mgr = TrashManager()
        item = FileItem(id="1", name="test.txt", path="/test.txt",
                        file_type="file", extension=".txt", size_bytes=10,
                        mime_type="text/plain")
        mgr.move_to_trash("/test.txt", item)
        assert mgr.restore("/test.txt") is True

    def test_empty_trash(self):
        mgr = TrashManager()
        item = FileItem(id="1", name="a.txt", path="/a.txt",
                        file_type="file", extension=".txt", size_bytes=10,
                        mime_type="text/plain")
        mgr.move_to_trash("/a.txt", item)
        assert mgr.empty_trash() == 1
        assert len(mgr.list_trash()) == 0

    def test_list_trash(self):
        mgr = TrashManager()
        item = FileItem(id="1", name="t.txt", path="/t.txt",
                        file_type="file", extension=".txt", size_bytes=10,
                        mime_type="text/plain")
        mgr.move_to_trash("/t.txt", item)
        trash_list = mgr.list_trash()
        assert len(trash_list) == 1
        assert trash_list[0]["original_path"] == "/t.txt"

    def test_recover_file(self):
        mgr = TrashManager()
        item = FileItem(id="1", name="r.txt", path="/r.txt",
                        file_type="file", extension=".txt", size_bytes=10,
                        mime_type="text/plain")
        mgr.move_to_trash("/r.txt", item)
        trash_list = mgr.list_trash()
        tid = trash_list[0]["trash_id"]
        recovered = mgr.recover_file(tid)
        assert recovered is not None
        assert recovered.name == "r.txt"

    def test_cleanup_expired(self):
        mgr = TrashManager()
        item = FileItem(id="1", name="e.txt", path="/e.txt",
                        file_type="file", extension=".txt", size_bytes=10,
                        mime_type="text/plain")
        mgr.move_to_trash("/e.txt", item)
        # With default retention of 7 days, nothing should expire
        assert mgr.cleanup_expired() == 0


class TestFileManagerService:
    """Verify service wrapper."""

    @pytest.mark.asyncio
    async def test_initialize(self):
        svc = FileManagerService()
        assert await svc.initialize() is True

    @pytest.mark.asyncio
    async def test_create_and_read(self):
        svc = FileManagerService()
        await svc.initialize()
        result = svc.create_file("/hello.txt", "world")
        assert result.success is True
        read_result = svc.read_file("/hello.txt")
        assert read_result.success is True

    @pytest.mark.asyncio
    async def test_delete(self):
        svc = FileManagerService()
        await svc.initialize()
        svc.create_file("/delete_me.txt", "data")
        result = svc.delete_file("/delete_me.txt")
        assert result.success is True

    @pytest.mark.asyncio
    async def test_list_directory(self):
        svc = FileManagerService()
        await svc.initialize()
        svc.create_file("/f1.txt", "1")
        svc.create_file("/f2.txt", "2")
        entry = svc.list_directory(svc.config.base_path)
        assert entry is not None
        assert entry.entry_count == 2

    @pytest.mark.asyncio
    async def test_search(self):
        svc = FileManagerService()
        await svc.initialize()
        svc.create_file("/search_test.txt", "findable content")
        results = svc.search("findable")
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_trash_operations(self):
        svc = FileManagerService()
        await svc.initialize()
        svc.create_file("/trash_test.txt", "data")
        result = svc.delete_file("/trash_test.txt")
        assert result.success is True
        trash = svc.list_trash()
        assert len(trash) >= 1

    @pytest.mark.asyncio
    async def test_health(self):
        svc = FileManagerService()
        await svc.initialize()
        health = await svc.health()
        assert health["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_stats(self):
        svc = FileManagerService()
        await svc.initialize()
        stats = await svc.stats()
        assert stats["service"] == "jarvis_file_manager"

    @pytest.mark.asyncio
    async def test_shutdown(self):
        svc = FileManagerService()
        await svc.initialize()
        await svc.shutdown()
        assert not svc.is_initialized()
