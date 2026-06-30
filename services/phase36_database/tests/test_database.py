"""
Tests for Phase 36 — Database Design.
"""

import pytest
from services.phase36_database import (
    DatabaseConfig,
    SchemaField,
    CollectionSchema,
    QueryFilter,
    QueryResult,
    DocumentStore,
    IndexManager,
    MigrationManager,
    DatabaseService,
)


class TestDocumentStore:
    """Verify document CRUD, schema validation, and query filtering."""

    def test_create_collection(self):
        store = DocumentStore()
        schema = CollectionSchema(name="users", fields={})
        assert store.create_collection(schema) is True
        assert store.create_collection(schema) is False  # duplicate

    def test_insert_and_find(self):
        store = DocumentStore()
        store.create_collection(CollectionSchema(name="items", fields={}))
        doc_id = store.insert("items", {"name": "test", "value": 42})
        assert doc_id is not None
        result = store.find("items")
        assert result.total_found == 1
        assert result.documents[0]["name"] == "test"

    def test_insert_schema_validation_strict(self):
        schema = CollectionSchema(
            name="users",
            fields={
                "name": SchemaField(name="name", field_type="str", required=True),
                "age": SchemaField(name="age", field_type="int"),
            },
            strict=True,
        )
        store = DocumentStore()
        store.create_collection(schema)
        # Missing required field
        doc_id = store.insert("users", {"age": 30})
        assert doc_id is None
        # Valid doc
        doc_id = store.insert("users", {"name": "Alice", "age": 30})
        assert doc_id is not None

    def test_find_with_filters(self):
        store = DocumentStore()
        store.create_collection(CollectionSchema(name="items", fields={}))
        store.insert("items", {"name": "a", "value": 10})
        store.insert("items", {"name": "b", "value": 20})
        store.insert("items", {"name": "c", "value": 30})
        filters = [QueryFilter(field="value", operator="gt", value=15)]
        result = store.find("items", filters)
        assert result.total_found == 2

    def test_find_one(self):
        store = DocumentStore()
        store.create_collection(CollectionSchema(name="items", fields={}))
        store.insert("items", {"name": "target"})
        doc = store.find_one("items")
        assert doc is not None
        assert doc["name"] == "target"

    def test_update(self):
        store = DocumentStore()
        store.create_collection(CollectionSchema(name="items", fields={}))
        doc_id = store.insert("items", {"name": "old"})
        assert store.update("items", doc_id, {"name": "new"}) is True
        doc = store.find_one("items", [QueryFilter(field="_id", operator="eq", value=doc_id)])
        assert doc is not None
        assert doc["name"] == "new"

    def test_delete(self):
        store = DocumentStore()
        store.create_collection(CollectionSchema(name="items", fields={}))
        doc_id = store.insert("items", {"name": "test"})
        assert store.delete("items", doc_id) is True
        assert store.find("items").total_found == 0

    def test_delete_nonexistent(self):
        store = DocumentStore()
        assert store.delete("nonexistent", "x") is False

    def test_list_collections(self):
        store = DocumentStore()
        store.create_collection(CollectionSchema(name="a", fields={}))
        store.create_collection(CollectionSchema(name="b", fields={}))
        cols = store.list_collections()
        assert len(cols) == 2

    def test_get_stats(self):
        store = DocumentStore()
        store.create_collection(CollectionSchema(name="items", fields={}))
        store.insert("items", {"x": 1})
        stats = store.get_stats()
        assert stats["collections"] == 1
        assert stats["total_documents"] == 1

    def test_max_collections(self):
        cfg = DatabaseConfig(max_collections=2)
        store = DocumentStore(cfg)
        assert store.create_collection(CollectionSchema(name="a", fields={})) is True
        assert store.create_collection(CollectionSchema(name="b", fields={})) is True
        assert store.create_collection(CollectionSchema(name="c", fields={})) is False

    def test_regex_filter(self):
        store = DocumentStore()
        store.create_collection(CollectionSchema(name="items", fields={}))
        store.insert("items", {"name": "hello world"})
        store.insert("items", {"name": "goodbye world"})
        filters = [QueryFilter(field="name", operator="regex", value="hello")]
        result = store.find("items", filters)
        assert result.total_found == 1


class TestIndexManager:
    """Verify index creation, drop, listing, and optimization."""

    def test_create_and_list_indexes(self):
        mgr = IndexManager()
        docs = {"1": {"name": "a", "age": 10}, "2": {"name": "b", "age": 20}}
        assert mgr.create_index("users", "age", docs) is True
        indexes = mgr.list_indexes("users")
        assert len(indexes) == 1
        assert indexes[0]["field"] == "age"

    def test_drop_index(self):
        mgr = IndexManager()
        mgr.create_index("users", "age", {"1": {"age": 10}})
        assert mgr.drop_index("users", "age") is True
        assert mgr.list_indexes("users") == []

    def test_drop_nonexistent(self):
        mgr = IndexManager()
        assert mgr.drop_index("users", "nonexistent") is False

    def test_lookup(self):
        mgr = IndexManager()
        docs = {"1": {"name": "a", "age": 10}, "2": {"name": "b", "age": 20}}
        mgr.create_index("users", "age", docs)
        ids = mgr.lookup("users", "age", 10)
        assert ids == ["1"]

    def test_optimize(self):
        mgr = IndexManager()
        mgr.create_index("users", "age", {"1": {"age": 10}})
        result = mgr.optimize("users")
        assert result["indexes_optimized"] >= 0


class TestMigrationManager:
    """Verify migration lifecycle."""

    def test_create_migration(self):
        mgr = MigrationManager()
        mid = mgr.create_migration("add_field")
        assert mid is not None
        assert mgr.get_migration_status(mid) == "pending"

    def test_apply_migration(self):
        mgr = MigrationManager()
        mid = mgr.create_migration("test")
        assert mgr.apply_migration(mid) is True
        assert mgr.get_migration_status(mid) == "applied"

    def test_rollback_migration(self):
        mgr = MigrationManager()
        mid = mgr.create_migration("test")
        mgr.apply_migration(mid)
        assert mgr.rollback_migration(mid) is True
        assert mgr.get_migration_status(mid) == "rolled_back"

    def test_rollback_pending_fails(self):
        mgr = MigrationManager()
        mid = mgr.create_migration("test")
        assert mgr.rollback_migration(mid) is False

    def test_list_migrations(self):
        mgr = MigrationManager()
        mgr.create_migration("a")
        mgr.create_migration("b")
        assert len(mgr.list_migrations()) == 2

    def test_get_status_not_found(self):
        mgr = MigrationManager()
        assert mgr.get_migration_status("nonexistent") == "not_found"


class TestDatabaseService:
    """Verify service wrapper."""

    @pytest.mark.asyncio
    async def test_initialize(self):
        svc = DatabaseService()
        assert await svc.initialize() is True

    @pytest.mark.asyncio
    async def test_create_collection_and_insert(self):
        svc = DatabaseService()
        await svc.initialize()
        schema = CollectionSchema(name="tests", fields={})
        assert svc.create_collection(schema) is True
        doc_id = svc.insert("tests", {"data": "hello"})
        assert doc_id is not None
        result = svc.find("tests")
        assert result.total_found == 1

    @pytest.mark.asyncio
    async def test_index_operations(self):
        svc = DatabaseService()
        await svc.initialize()
        schema = CollectionSchema(name="indexed", fields={})
        svc.create_collection(schema)
        svc.insert("indexed", {"key": "a", "val": 1})
        svc.insert("indexed", {"key": "b", "val": 2})
        assert svc.create_index("indexed", "key") is True
        assert len(svc.list_indexes("indexed")) == 1

    @pytest.mark.asyncio
    async def test_migration_operations(self):
        svc = DatabaseService()
        await svc.initialize()
        mid = svc.create_migration("test_migration")
        assert mid is not None
        assert svc.apply_migration(mid) is True
        assert svc.get_migration_status(mid) == "applied"
        assert svc.rollback_migration(mid) is True

    @pytest.mark.asyncio
    async def test_health(self):
        svc = DatabaseService()
        await svc.initialize()
        health = await svc.health()
        assert health["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_stats(self):
        svc = DatabaseService()
        await svc.initialize()
        stats = await svc.stats()
        assert stats["service"] == "jarvis_database"

    @pytest.mark.asyncio
    async def test_shutdown(self):
        svc = DatabaseService()
        await svc.initialize()
        await svc.shutdown()
        assert not svc.is_initialized()
