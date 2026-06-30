"""
Tests for Phase 30 — Notification Manager.
"""

import pytest
from services.phase30_notification import (
    NotificationQueue,
    TemplateEngine,
    NotificationManagerService,
    NotificationConfig,
    Notification,
    NotificationTemplate,
    NotificationChannel,
)


class TestNotificationQueue:
    """Verify priority queue operations."""

    def test_enqueue_and_dequeue(self):
        queue = NotificationQueue()
        notif = Notification(id="1", type="info", title="Test", message="Hello")
        queue.enqueue(notif)
        assert queue.size() == 1
        dequeued = queue.dequeue()
        assert dequeued is not None
        assert dequeued.id == "1"

    def test_dequeue_priority_order(self):
        queue = NotificationQueue()
        low = Notification(id="1", type="info", title="Low", message="", priority="low")
        high = Notification(id="2", type="info", title="High", message="", priority="high")
        queue.enqueue(low)
        queue.enqueue(high)
        first = queue.dequeue()
        assert first.id == "2"  # High priority first
        second = queue.dequeue()
        assert second.id == "1"

    def test_peek(self):
        queue = NotificationQueue()
        notif = Notification(id="1", type="info", title="Test", message="")
        queue.enqueue(notif)
        peeked = queue.peek()
        assert peeked is not None
        assert peeked.id == "1"
        assert queue.size() == 1  # Still there

    def test_dequeue_empty(self):
        queue = NotificationQueue()
        assert queue.dequeue() is None

    def test_get_pending_count(self):
        queue = NotificationQueue()
        assert queue.get_pending_count() == 0
        notif = Notification(id="1", type="info", title="Test", message="")
        queue.enqueue(notif)
        assert queue.get_pending_count() == 1

    def test_clear(self):
        queue = NotificationQueue()
        queue.enqueue(Notification(id="1", type="info", title="T", message=""))
        queue.enqueue(Notification(id="2", type="info", title="T", message=""))
        count = queue.clear()
        assert count == 2
        assert queue.size() == 0

    def test_expired_removed(self):
        from datetime import datetime, timezone, timedelta
        queue = NotificationQueue()
        expired = Notification(
            id="1", type="info", title="Expired", message="",
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        queue.enqueue(expired)
        assert queue.size() == 0


class TestTemplateEngine:
    """Verify template registration and rendering."""

    def test_register_and_render(self):
        engine = TemplateEngine()
        template = NotificationTemplate(
            id="1", name="welcome",
            title_template="Hello {name}!",
            message_template="Welcome to {app}, {name}!",
            variables=["name", "app"],
        )
        engine.register_template(template)
        title, message = engine.render("welcome", {"name": "User", "app": "JARVIS"})
        assert title == "Hello User!"
        assert message == "Welcome to JARVIS, User!"

    def test_render_missing_variable(self):
        engine = TemplateEngine()
        template = NotificationTemplate(
            id="1", name="test",
            title_template="Hi {name}",
            message_template="Body",
            variables=["name"],
        )
        engine.register_template(template)
        title, message = engine.render("test", {})
        assert "{name}" in title  # Placeholder remains

    def test_render_nonexistent_template(self):
        engine = TemplateEngine()
        with pytest.raises(ValueError):
            engine.render("nonexistent", {})

    def test_list_templates(self):
        engine = TemplateEngine()
        template = NotificationTemplate(id="1", name="t1", title_template="T", message_template="M")
        engine.register_template(template)
        assert len(engine.list_templates()) == 1

    def test_get_template(self):
        engine = TemplateEngine()
        template = NotificationTemplate(id="1", name="t1", title_template="T", message_template="M")
        engine.register_template(template)
        assert engine.get_template("t1") is not None
        assert engine.get_template("x") is None

    def test_delete_template(self):
        engine = TemplateEngine()
        template = NotificationTemplate(id="1", name="t1", title_template="T", message_template="M")
        engine.register_template(template)
        assert engine.delete_template("t1") is True
        assert engine.delete_template("x") is False

    def test_clear(self):
        engine = TemplateEngine()
        template = NotificationTemplate(id="1", name="t1", title_template="T", message_template="M")
        engine.register_template(template)
        engine.clear()
        assert engine.get_template_count() == 0


class TestNotificationManagerService:
    """Verify service wrapper."""

    @pytest.mark.asyncio
    async def test_initialize(self):
        svc = NotificationManagerService()
        assert await svc.initialize() is True

    @pytest.mark.asyncio
    async def test_send_notification(self):
        svc = NotificationManagerService()
        await svc.initialize()
        nid = await svc.send_notification("Test", "Hello", notif_type="info")
        assert nid is not None

    @pytest.mark.asyncio
    async def test_create_notification(self):
        svc = NotificationManagerService()
        await svc.initialize()
        nid = await svc.create_notification("Test", "Hello", notif_type="info")
        assert nid is not None

    @pytest.mark.asyncio
    async def test_mark_read(self):
        svc = NotificationManagerService()
        await svc.initialize()
        nid = await svc.send_notification("Test", "Msg", notif_type="info")
        assert await svc.mark_read(nid) is True

    @pytest.mark.asyncio
    async def test_dismiss(self):
        svc = NotificationManagerService()
        await svc.initialize()
        nid = await svc.send_notification("Test", "Msg", notif_type="info")
        assert await svc.dismiss(nid) is True

    @pytest.mark.asyncio
    async def test_dismiss_all(self):
        svc = NotificationManagerService()
        await svc.initialize()
        await svc.send_notification("A", "Msg", notif_type="info")
        await svc.send_notification("B", "Msg", notif_type="info")
        count = await svc.dismiss_all()
        assert count >= 2

    @pytest.mark.asyncio
    async def test_register_channel(self):
        svc = NotificationManagerService()
        await svc.initialize()
        channel = NotificationChannel(id="alerts", name="Alerts", type="push", enabled=True)
        cid = await svc.register_channel(channel)
        assert cid == "alerts"

    @pytest.mark.asyncio
    async def test_get_notifications(self):
        svc = NotificationManagerService()
        await svc.initialize()
        await svc.send_notification("Test", "Msg", notif_type="info")
        notifs = await svc.get_notifications()
        assert len(notifs) >= 1

    @pytest.mark.asyncio
    async def test_get_notifications_filtered(self):
        svc = NotificationManagerService()
        await svc.initialize()
        await svc.send_notification("Test", "Msg", notif_type="info", priority="high")
        notifs = await svc.get_notifications(priority="high")
        assert len(notifs) >= 1
        notifs_low = await svc.get_notifications(priority="low")
        assert len(notifs_low) == 0

    @pytest.mark.asyncio
    async def test_register_and_render_template(self):
        svc = NotificationManagerService()
        await svc.initialize()
        template = NotificationTemplate(
            id="1", name="greeting",
            title_template="Hi {name}",
            message_template="Welcome!",
            variables=["name"],
        )
        await svc.register_template(template)
        title, message = await svc.render_template("greeting", {"name": "User"})
        assert title == "Hi User"

    @pytest.mark.asyncio
    async def test_health(self):
        svc = NotificationManagerService()
        await svc.initialize()
        health = await svc.health()
        assert health["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_stats(self):
        svc = NotificationManagerService()
        await svc.initialize()
        stats = await svc.stats()
        assert stats["service"] == "jarvis_notification"

    @pytest.mark.asyncio
    async def test_shutdown(self):
        svc = NotificationManagerService()
        await svc.initialize()
        await svc.shutdown()
        assert not svc.is_initialized()
