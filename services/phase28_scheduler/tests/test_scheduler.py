"""
Tests for Phase 28 — Scheduler.
"""

import pytest
from datetime import datetime, timezone, timedelta
from services.phase28_scheduler import (
    TimeParser,
    SchedulerEngine,
    ReminderManager,
    SchedulerService,
    SchedulerConfig,
    ScheduledItem,
    TimeExpression,
    ConflictInfo,
)


class TestTimeParser:
    """Verify natural language time parsing."""

    def test_parse_in_minutes(self):
        parser = TimeParser()
        result = parser.parse("in 5 minutes")
        assert result is not None
        assert result.parsed_time > datetime.now(timezone.utc)
        assert 0.8 <= result.confidence <= 1.0

    def test_parse_in_hours(self):
        parser = TimeParser()
        result = parser.parse("in 2 hours")
        assert result is not None
        assert result.parsed_time > datetime.now(timezone.utc)

    def test_parse_tomorrow(self):
        parser = TimeParser()
        result = parser.parse("tomorrow at 3pm")
        assert result is not None
        assert result.parsed_time.hour == 15

    def test_parse_recurring_weekday(self):
        parser = TimeParser()
        result = parser.parse("every weekday at 9am")
        assert result is not None
        assert result.is_recurring is True
        assert result.recurrence_pattern == "weekdays"

    def test_parse_recurring_daily(self):
        parser = TimeParser()
        result = parser.parse("every day at 8am")
        assert result is not None
        assert result.is_recurring is True

    def test_parse_next_monday(self):
        parser = TimeParser()
        result = parser.parse("next monday at 10am")
        assert result is not None
        assert result.parsed_time.weekday() == 0  # Monday

    def test_parse_absolute_time(self):
        parser = TimeParser()
        result = parser.parse("14:30")
        assert result is not None
        assert result.parsed_time.hour == 14
        assert result.parsed_time.minute == 30

    def test_parse_invalid_expression(self):
        parser = TimeParser()
        result = parser.parse("this is not a time")
        assert result is None


class TestSchedulerEngine:
    """Verify core scheduling operations."""

    def test_schedule(self):
        engine = SchedulerEngine()
        item = ScheduledItem(
            id="1", type="reminder", title="Test",
            trigger_time=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        item_id = engine.schedule(item)
        assert item_id == "1"
        assert engine.get_item_count() == 1

    def test_cancel(self):
        engine = SchedulerEngine()
        item = ScheduledItem(
            id="1", type="reminder", title="Test",
            trigger_time=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        engine.schedule(item)
        assert engine.cancel("1") is True
        assert not engine.get_scheduled("1").is_active

    def test_cancel_nonexistent(self):
        engine = SchedulerEngine()
        assert engine.cancel("x") is False

    def test_get_upcoming(self):
        engine = SchedulerEngine()
        now = datetime.now(timezone.utc)
        item1 = ScheduledItem(id="1", type="reminder", title="A", trigger_time=now + timedelta(hours=2))
        item2 = ScheduledItem(id="2", type="reminder", title="B", trigger_time=now + timedelta(hours=1))
        engine.schedule(item1)
        engine.schedule(item2)
        upcoming = engine.get_upcoming()
        assert len(upcoming) == 2
        assert upcoming[0].title == "B"  # Earlier first

    def test_get_overdue(self):
        engine = SchedulerEngine()
        now = datetime.now(timezone.utc)
        item = ScheduledItem(id="1", type="reminder", title="Overdue", trigger_time=now - timedelta(minutes=5))
        engine.schedule(item)
        overdue = engine.get_overdue()
        assert len(overdue) >= 1

    def test_detect_conflicts(self):
        engine = SchedulerEngine()
        now = datetime.now(timezone.utc)
        item1 = ScheduledItem(id="1", type="reminder", title="A", trigger_time=now + timedelta(hours=1))
        item2 = ScheduledItem(id="2", type="reminder", title="B", trigger_time=now + timedelta(hours=1))
        engine.schedule(item1)
        engine.schedule(item2)
        conflict = engine.detect_conflicts(item1)
        assert conflict.has_conflict is True

    def test_no_conflict(self):
        engine = SchedulerEngine()
        now = datetime.now(timezone.utc)
        item1 = ScheduledItem(id="1", type="reminder", title="A", trigger_time=now + timedelta(hours=1))
        item2 = ScheduledItem(id="2", type="reminder", title="B", trigger_time=now + timedelta(hours=3))
        engine.schedule(item1)
        conflict = engine.detect_conflicts(item2)
        assert conflict.has_conflict is False

    def test_get_by_tag(self):
        engine = SchedulerEngine()
        now = datetime.now(timezone.utc)
        item = ScheduledItem(id="1", type="reminder", title="Test", trigger_time=now + timedelta(hours=1), tags=["work"])
        engine.schedule(item)
        tagged = engine.get_by_tag("work")
        assert len(tagged) == 1

    def test_mark_triggered(self):
        engine = SchedulerEngine()
        now = datetime.now(timezone.utc)
        item = ScheduledItem(id="1", type="reminder", title="Test", trigger_time=now + timedelta(hours=1))
        engine.schedule(item)
        assert engine.mark_triggered("1") is True
        assert engine.get_scheduled("1").last_triggered is not None

    def test_clear(self):
        engine = SchedulerEngine()
        now = datetime.now(timezone.utc)
        item = ScheduledItem(id="1", type="reminder", title="Test", trigger_time=now + timedelta(hours=1))
        engine.schedule(item)
        engine.clear()
        assert engine.get_item_count() == 0


class TestReminderManager:
    """Verify reminder lifecycle."""

    def test_create_reminder(self):
        engine = SchedulerEngine()
        parser = TimeParser()
        mgr = ReminderManager(engine, parser)
        rid = mgr.create_reminder("Test", datetime.now(timezone.utc) + timedelta(minutes=10))
        assert rid is not None
        assert mgr.get_active_reminders()

    def test_snooze(self):
        engine = SchedulerEngine()
        parser = TimeParser()
        mgr = ReminderManager(engine, parser)
        now = datetime.now(timezone.utc)
        rid = mgr.create_reminder("Test", now + timedelta(minutes=5))
        assert mgr.snooze(rid, 10) is True

    def test_snooze_nonexistent(self):
        engine = SchedulerEngine()
        parser = TimeParser()
        mgr = ReminderManager(engine, parser)
        assert mgr.snooze("x", 5) is False

    def test_dismiss(self):
        engine = SchedulerEngine()
        parser = TimeParser()
        mgr = ReminderManager(engine, parser)
        rid = mgr.create_reminder("Test", datetime.now(timezone.utc) + timedelta(minutes=5))
        assert mgr.dismiss(rid) is True
        assert len(mgr.get_active_reminders()) == 0


class TestSchedulerService:
    """Verify service wrapper."""

    @pytest.mark.asyncio
    async def test_initialize(self):
        svc = SchedulerService()
        assert await svc.initialize() is True

    @pytest.mark.asyncio
    async def test_schedule_and_get(self):
        svc = SchedulerService()
        await svc.initialize()
        now = datetime.now(timezone.utc)
        item = ScheduledItem(id="1", type="reminder", title="Test", trigger_time=now + timedelta(hours=1))
        item_id = await svc.schedule(item)
        assert item_id == "1"
        retrieved = await svc.get_scheduled("1")
        assert retrieved is not None

    @pytest.mark.asyncio
    async def test_cancel(self):
        svc = SchedulerService()
        await svc.initialize()
        now = datetime.now(timezone.utc)
        item = ScheduledItem(id="1", type="reminder", title="Test", trigger_time=now + timedelta(hours=1))
        await svc.schedule(item)
        assert await svc.cancel("1") is True

    @pytest.mark.asyncio
    async def test_create_reminder(self):
        svc = SchedulerService()
        await svc.initialize()
        rid = await svc.create_reminder("Test", datetime.now(timezone.utc) + timedelta(minutes=10))
        assert rid is not None

    @pytest.mark.asyncio
    async def test_snooze_dismiss(self):
        svc = SchedulerService()
        await svc.initialize()
        rid = await svc.create_reminder("Test", datetime.now(timezone.utc) + timedelta(minutes=5))
        assert await svc.snooze(rid, 10) is True
        assert await svc.dismiss(rid) is True

    @pytest.mark.asyncio
    async def test_get_upcoming(self):
        svc = SchedulerService()
        await svc.initialize()
        now = datetime.now(timezone.utc)
        item = ScheduledItem(id="1", type="reminder", title="A", trigger_time=now + timedelta(hours=1))
        await svc.schedule(item)
        upcoming = await svc.get_upcoming()
        assert len(upcoming) >= 1

    @pytest.mark.asyncio
    async def test_detect_conflicts(self):
        svc = SchedulerService()
        await svc.initialize()
        now = datetime.now(timezone.utc)
        item1 = ScheduledItem(id="1", type="reminder", title="A", trigger_time=now + timedelta(hours=1))
        item2 = ScheduledItem(id="2", type="reminder", title="B", trigger_time=now + timedelta(hours=1))
        await svc.schedule(item1)
        await svc.schedule(item2)
        # Check for conflict on item1 (existed first)
        conflict = await svc.detect_conflicts(item1)
        assert conflict.has_conflict is True

    @pytest.mark.asyncio
    async def test_parse_time(self):
        svc = SchedulerService()
        await svc.initialize()
        result = await svc.parse_time("in 5 minutes")
        assert result is not None

    @pytest.mark.asyncio
    async def test_health(self):
        svc = SchedulerService()
        await svc.initialize()
        health = await svc.health()
        assert health["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_stats(self):
        svc = SchedulerService()
        await svc.initialize()
        stats = await svc.stats()
        assert stats["service"] == "jarvis_scheduler"

    @pytest.mark.asyncio
    async def test_shutdown(self):
        svc = SchedulerService()
        await svc.initialize()
        await svc.shutdown()
        assert not svc.is_initialized()
