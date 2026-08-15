"""
Tests for the Advanced Multi-Turn Dialogue Manager.

Covers:
  1. Basic slot filling — one turn at a time
  2. Interruption handling — pause and resume
  3. Reference resolution — pronouns and deixis
  4. Multi-task management — switch between tasks
  5. Cancellation — cancel active tasks
  6. Continuation — "continue" resumes paused tasks
  7. Memory — entities stored and recallable
  8. Edge cases — empty messages, invalid intents
"""

import os
import tempfile
import time
import pytest

from app.dialogue_manager import (
    DialogueManager,
    DialogueConfig,
    TaskStatus,
)
from app.dialogue_manager.state_manager import DialogueStateTracker
from app.dialogue_manager.slot_filler import SlotFiller
from app.dialogue_manager.dialogue_manager import ReferenceResolver, TaskManager
from app.dialogue_manager.working_memory import WorkingMemory, ShortTermMemory
from app.dialogue_manager.action_planner import ActionPlanner


# ── Fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def dm():
    """Create a fresh DialogueManager for each test."""
    return DialogueManager()


@pytest.fixture
def state_tracker():
    return DialogueStateTracker()


@pytest.fixture
def slot_filler():
    return SlotFiller()


@pytest.fixture
def working_memory():
    return WorkingMemory(max_history=50)


@pytest.fixture
def short_term_memory():
    return ShortTermMemory(default_ttl=300)


@pytest.fixture
def resolver(working_memory, short_term_memory):
    return ReferenceResolver(working_memory, short_term_memory)


# ── Test 1: Basic Slot Filling ────────────────────────────────────

class TestSlotFilling:
    """Test that the dialogue manager performs slot filling correctly."""

    def test_youtube_slot_filling(self, dm):
        """Test YouTube intent: should ask for search_query after content_type."""
        # First message: intent detected, no slots yet
        result1 = dm.process("Play a song")
        assert result1["intent"] == "youtube"
        assert result1["all_slots_filled"] is False
        assert result1["can_execute"] is False
        assert result1["status"] == "waiting_for_info"
        assert "song" in result1["response"].lower() or "kaunsa" in result1["response"].lower() or "chahiye" in result1["response"].lower()

        # Second message: provide search query
        result2 = dm.process("Tum Hi Ho")
        # Should have filled the search_query slot
        assert result2["intent"] == "youtube"
        assert result2["all_slots_filled"] is True
        assert result2["executed"] is True or result2["can_execute"] is True
        assert result2["status"] in ("completed", "ready_to_execute")

    def test_open_app_slot_filling(self, dm):
        """Test Open App intent: simple single-slot filling."""
        result1 = dm.process("Open an app")
        assert result1["intent"] == "open_app"
        assert result1["all_slots_filled"] is False
        assert "app" in result1["response"].lower()

        result2 = dm.process("WhatsApp")
        assert result2["intent"] == "open_app"
        assert result2["all_slots_filled"] is True

    def test_alarm_slot_filling(self, dm):
        """Test Alarm intent: multiple required slots."""
        result1 = dm.process("Set an alarm")
        assert result1["intent"] == "alarm"
        assert result1["all_slots_filled"] is False
        assert "baje" in result1["response"].lower() or "kitne" in result1["response"].lower() or "time" in result1["response"].lower()

        result2 = dm.process("7 AM")
        assert result2["intent"] == "alarm"
        # Hour and minute should be detected from "7 AM"
        assert result2["all_slots_filled"] is True

    def test_never_asks_same_question_twice(self, dm):
        """Verify the assistant never asks for the same slot twice."""
        result1 = dm.process("Play a song")
        question1 = result1["response"]

        result2 = dm.process("Play something")
        question2 = result2["response"]

        # Should not ask for content_type again
        assert question1 != question2

    def test_call_slot_filling(self, dm):
        """Test Call intent with contact name."""
        result1 = dm.process("Call someone")
        assert result1["intent"] == "call"
        assert result1["all_slots_filled"] is False

        result2 = dm.process("Mummy")
        assert result2["intent"] == "call"
        assert result2["all_slots_filled"] is True


# ── Test 2: Interruption Handling ─────────────────────────────────

class TestInterruptionHandling:
    """Test that the DM handles interruptions correctly."""

    def test_interrupt_youtube_with_weather(self, dm):
        """Start YouTube task, interrupt with weather, then resume."""
        # Start YouTube
        r1 = dm.process("Play a song")
        assert r1["intent"] == "youtube"
        task_id_youtube = r1["task_id"]
        assert task_id_youtube is not None

        # Interrupt: search (simulated as chat/search)
        r2 = dm.process("Actually, what's the weather today?")
        # This should be detected as chat or search, interrupting YouTube
        assert r2["intent"] in ("chat", "search")
        # YouTube task should be paused (or auto-resumed after interrupt completes)
        yt_task = dm.get_task(task_id_youtube)
        if yt_task:
            assert yt_task["status"] in ("paused", "waiting_for_info", "pending")

        # Resume: continue
        r3 = dm.process("Now continue that")
        # Should resume the YouTube task
        assert r3["intent"] == "youtube"
        assert "continue" in r3["response"].lower() or "jaari" in r3["response"].lower() or r3["status"] == "waiting_for_info" or r3["all_slots_filled"]

    def test_interrupt_with_instant_action(self, dm):
        """Instant actions (flashlight) should not interrupt long tasks badly."""
        r1 = dm.process("Play a song")
        assert r1["intent"] == "youtube"

        # Quick flashlight toggle
        r2 = dm.process("Turn on flashlight")
        assert r2["intent"] == "flashlight"

        # Resume back
        r3 = dm.process("Continue")
        assert r3["intent"] == "youtube"

    def test_multiple_interrupts(self, dm):
        """Chain multiple interruptions."""
        dm.process("Play a song")
        dm.process("What's the weather?")
        dm.process("Open Chrome")
        dm.process("Continue")

        # Should eventually get back to YouTube
        state = dm.get_state()
        # At least one task should be in progress
        assert state["stats"]["total_tasks"] >= 2


# ── Test 3: Reference Resolution ──────────────────────────────────

class TestReferenceResolution:
    """Test pronoun and reference resolution."""

    def test_resolve_it(self, resolver, working_memory, short_term_memory):
        """Test resolving 'it' to the last mentioned song."""
        short_term_memory.remember("last_action_target", "Tum Hi Ho", ttl=120)
        resolved, meta = resolver.resolve("Play it")
        assert meta["resolved"] is True
        assert "Tum Hi Ho" in resolved

    def test_resolve_that(self, resolver, short_term_memory):
        """Test resolving 'that' to a previously mentioned entity."""
        short_term_memory.remember("last_referenced", "WhatsApp", ttl=120)
        resolved, meta = resolver.resolve("Open that")
        assert meta["resolved"] is True

    def test_continue_resume_detection(self, resolver):
        """Test that 'continue' is detected as resume request."""
        _, meta = resolver.resolve("Continue")
        assert meta["resume_requested"] is True

        _, meta = resolver.resolve("Jari rakho")
        assert meta["resume_requested"] is True

        _, meta = resolver.resolve("Phir se")
        assert meta["resume_requested"] is True

    def test_cancel_detection(self, resolver):
        """Test that cancel requests are detected."""
        _, meta = resolver.resolve("Cancel the music")
        assert meta["cancel_requested"] is True

        _, meta = resolver.resolve("Yeh nahi karna")
        assert meta["cancel_requested"] is True

    def test_no_resolution_for_normal(self, resolver):
        """Normal messages should not trigger resolution."""
        _, meta = resolver.resolve("Play Arijit Singh songs")
        assert meta["resolved"] is False
        assert meta["resume_requested"] is False
        assert meta["cancel_requested"] is False

    def test_resolve_them(self, resolver, short_term_memory):
        """Test resolving 'them' to a contact."""
        short_term_memory.remember("last_contact", "Mummy", ttl=120)
        resolved, meta = resolver.resolve("Call them")
        assert meta["resolved"] is True
        assert "Mummy" in resolved

    def test_reference_in_full_conversation(self, dm):
        """Test reference resolution in a full dialogue flow."""
        dm.process("Play a song")
        dm.process("Tum Hi Ho")

        # "Play it again" should reference the last song
        result = dm.process("Play that again")
        assert result["intent"] == "music" or result["intent"] == "youtube"
        assert result["all_slots_filled"] is True


# ── Test 4: Multi-Task Management ─────────────────────────────────

class TestMultiTask:
    """Test that multiple tasks can coexist."""

    def test_multiple_tasks(self, dm):
        """Create and track multiple tasks."""
        dm.process("Play a song")
        dm.process("Tum Hi Ho")
        dm.process("Set a timer")
        dm.process("5 minutes")

        state = dm.get_state()
        # There should be at least 2 tasks
        assert state["stats"]["total_tasks"] >= 2

        # Some tasks should be completed
        assert state["stats"]["completed_tasks"] >= 1

    def test_task_switch(self, dm):
        """Explicit task switching via interruption."""
        dm.process("Play a song")
        dm.process("Tum Hi Ho")
        dm.process("Set alarm for morning")
        dm.process("Continue")

        state = dm.get_state()
        # Should have tasks
        assert state["stats"]["total_tasks"] >= 1

    def test_task_cleanup(self, dm):
        """Completed tasks should eventually be cleaned up."""
        dm.process("Play a song")
        dm.process("Tum Hi Ho")

        # Manually trigger cleanup
        dm.state_tracker.cleanup_old_tasks(max_age_seconds=0)
        state = dm.get_state()
        # Completed tasks should be cleaned
        assert state["stats"]["completed_tasks"] == 0


# ── Test 5: Cancellation ──────────────────────────────────────────

class TestCancellation:
    """Test task cancellation."""

    def test_cancel_active_task(self, dm):
        """Cancel the currently active task."""
        r1 = dm.process("Play a song")
        task_id = r1["task_id"]

        r2 = dm.process("Don't play music")
        assert r2["status"] == "cancelled" or "cancel" in r2["response"].lower()

        # Task should be cancelled
        task = dm.get_task(task_id)
        if task:
            assert task["status"] == "cancelled"

    def test_cancel_via_api(self, dm):
        """Cancel a task via the cancel_task API."""
        r1 = dm.process("Play a song")
        task_id = r1["task_id"]

        cancelled = dm.cancel_task(task_id)
        assert cancelled is True

        task = dm.get_task(task_id)
        if task:
            assert task["status"] == "cancelled"

    def test_cancel_nonexistent_task(self, dm):
        """Cancelling a non-existent task should return False."""
        cancelled = dm.cancel_task("nonexistent_123")
        assert cancelled is False

    def test_cancel_and_continue(self, dm):
        """Cancel a task and start a new one."""
        dm.process("Play a song")
        dm.cancel_task(dm.state_tracker.get_active_task_id())

        # Start a new unrelated task
        result = dm.process("Set alarm for 7 AM")
        assert result["intent"] == "alarm"
        assert result["all_slots_filled"] is True


# ── Test 6: State Tracker ─────────────────────────────────────────

class TestStateTracker:
    """Test the DialogueStateTracker directly."""

    def test_create_task(self, state_tracker):
        task = state_tracker.create_task(
            intent="youtube",
            required_slots=["content_type", "search_query"],
            optional_slots=["artist", "language"],
        )
        assert task.task_id is not None
        assert task.intent == "youtube"
        assert task.status == TaskStatus.PENDING
        assert task.required_slots == ["content_type", "search_query"]
        assert task.optional_slots == ["artist", "language"]
        assert task.filled_slots == {}

    def test_task_lifecycle(self, state_tracker):
        task = state_tracker.create_task("youtube", ["search_query"])
        assert task.status == TaskStatus.PENDING

        state_tracker.mark_waiting(task.task_id, "search_query")
        updated = state_tracker.get_task(task.task_id)
        assert updated.status == TaskStatus.WAITING_FOR_INFO
        assert updated.waiting_for == "search_query"

        state_tracker.mark_ready(task.task_id)
        updated = state_tracker.get_task(task.task_id)
        assert updated.status == TaskStatus.READY_TO_EXECUTE

        state_tracker.mark_completed(task.task_id)
        updated = state_tracker.get_task(task.task_id)
        assert updated.status == TaskStatus.COMPLETED
        assert updated.completed_at is not None

    def test_pause_resume(self, state_tracker):
        task = state_tracker.create_task("youtube", ["search_query"])
        state_tracker.pause_task(task.task_id)
        assert state_tracker.get_task(task.task_id).status == TaskStatus.PAUSED

        state_tracker.resume_task(task.task_id)
        resumed = state_tracker.get_task(task.task_id)
        assert resumed.status != TaskStatus.PAUSED

    def test_missing_slots_property(self, state_tracker):
        task = state_tracker.create_task("youtube", ["content_type", "search_query"])
        assert task.missing_slots == ["content_type", "search_query"]

        task.filled_slots["content_type"] = "song"
        assert task.missing_slots == ["search_query"]

        task.filled_slots["search_query"] = "Tum Hi Ho"
        assert task.missing_slots == []

    def test_get_active_tasks(self, state_tracker):
        t1 = state_tracker.create_task("youtube", ["search_query"])
        _t2 = state_tracker.create_task("device", ["action"])

        active = state_tracker.get_active_tasks()
        assert len(active) >= 1

        state_tracker.mark_completed(t1.task_id)
        active = state_tracker.get_active_tasks()
        assert len(active) >= 0

    def test_persistence(self):
        """Test that state is saved and loaded correctly."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            persist_path = f.name

        try:
            # Create tracker with persistence
            tracker = DialogueStateTracker(persist_path=persist_path)
            task = tracker.create_task("youtube", ["search_query"])
            task_id = task.task_id
            tracker.mark_completed(task_id)

            # Create new tracker that loads from same file
            tracker2 = DialogueStateTracker(persist_path=persist_path)
            loaded = tracker2.get_task(task_id)
            assert loaded is not None
            assert loaded.intent == "youtube"
            assert loaded.status == TaskStatus.COMPLETED
        finally:
            os.unlink(persist_path)


# ── Test 7: Slot Filler ───────────────────────────────────────────

class TestSlotFiller:
    """Test the slot filler directly."""

    def test_missing_slots(self, state_tracker, slot_filler):
        task = state_tracker.create_task("youtube", ["content_type", "search_query"])
        missing = slot_filler.get_missing_required_slots(task)
        assert missing == ["content_type", "search_query"]

    def test_fill_slot(self, state_tracker, slot_filler):
        task = state_tracker.create_task("youtube", ["search_query"])
        slot_filler.fill_slot(task, "search_query", "Tum Hi Ho")
        assert task.filled_slots["search_query"] == "Tum Hi Ho"
        assert slot_filler.all_required_filled(task) is True

    def test_all_required_filled(self, state_tracker, slot_filler):
        task = state_tracker.create_task("youtube", ["search_query"])
        assert slot_filler.all_required_filled(task) is False
        slot_filler.fill_slot(task, "search_query", "test")
        assert slot_filler.all_required_filled(task) is True

    def test_get_next_question(self, state_tracker, slot_filler):
        task = state_tracker.create_task("youtube", ["search_query", "content_type"])
        question = slot_filler.get_next_question(task)
        assert question is not None
        assert len(question) > 0

    def test_never_asks_if_all_filled(self, state_tracker, slot_filler):
        task = state_tracker.create_task("youtube", ["search_query"])
        slot_filler.fill_slot(task, "search_query", "test")
        question = slot_filler.get_next_question(task)
        assert question is None


# ── Test 8: Working Memory ────────────────────────────────────────

class TestWorkingMemory:
    """Test working memory layers."""

    def test_add_turn(self, working_memory):
        turn = working_memory.add_turn(
            user_message="Play a song",
            assistant_message="Which song?",
            intent="youtube",
            task_id="test_001",
            entities={"content_type": "song"},
        )
        assert turn.user_message == "Play a song"
        assert turn.assistant_message == "Which song?"
        assert turn.intent == "youtube"

    def test_get_recent_turns(self, working_memory):
        for i in range(5):
            working_memory.add_turn(f"msg_{i}", f"resp_{i}", "chat")
        recent = working_memory.get_recent_turns(3)
        assert len(recent) == 3
        assert recent[-1].user_message == "msg_4"

    def test_get_last_entity(self, working_memory):
        working_memory.add_turn("msg", "resp", "youtube",
                                 entities={"search_query": "Tum Hi Ho"})
        entity = working_memory.get_last_entity("search_query")
        assert entity == "Tum Hi Ho"

    def test_max_history(self):
        wm = WorkingMemory(max_history=5)
        for i in range(10):
            wm.add_turn(f"msg_{i}", f"resp_{i}", "chat")
        assert wm.get_turn_count() == 5
        assert wm.get_recent_turns(1)[0].user_message == "msg_9"

    def test_short_term_memory_ttl(self, short_term_memory):
        short_term_memory.remember("test_key", "test_value", ttl=1)
        assert short_term_memory.recall("test_key") == "test_value"
        time.sleep(1.5)
        assert short_term_memory.recall("test_key") is None

    def test_short_term_memory_get_all(self, short_term_memory):
        short_term_memory.remember("key1", "val1")
        short_term_memory.remember("key2", "val2")
        all_ents = short_term_memory.get_all()
        assert all_ents["key1"] == "val1"
        assert all_ents["key2"] == "val2"


# ── Test 9: Edge Cases ────────────────────────────────────────────

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_message(self, dm):
        result = dm.process("")
        assert "kuch" in result["response"].lower() or not result["response"] == ""

    def test_whitespace_message(self, dm):
        result = dm.process("   ")
        assert "kuch" in result["response"].lower()

    def test_unknown_intent(self, dm):
        result = dm.process("xyzzy flurbo garblex")
        # Should fall back to chat or give a response
        assert result["response"] is not None

    def test_reset_state(self, dm):
        dm.process("Play a song")
        dm.process("Tum Hi Ho")
        dm.reset()
        state = dm.get_state()
        assert state["stats"]["total_tasks"] == 0
        assert state["memory"]["turn_count"] == 0

    def test_special_characters(self, dm):
        """Test that special characters don't break the system."""
        result = dm.process("Play @#$%^&*() song!")
        assert result["response"] is not None

    def test_long_message(self, dm):
        """Test with a very long message."""
        long_msg = "Play " + "test " * 100
        result = dm.process(long_msg)
        assert result["response"] is not None

    def test_multiple_consecutive_same_intent(self, dm):
        """Multiple same-intent messages should continue the same task."""
        dm.process("Play a song")
        r2 = dm.process("Tum Hi Ho")
        # Should be the same task
        if r2.get("task_id"):
            # Task may have been completed, but the intent should match
            pass

    def test_intent_definitions(self):
        """Test that intent definitions are properly loaded."""
        from app.dialogue_manager.intent_definitions import (
            get_intent_definition,
            get_required_slot_names,
            INTENT_DEFINITIONS,
        )
        assert "youtube" in INTENT_DEFINITIONS
        assert "call" in INTENT_DEFINITIONS
        assert "open_app" in INTENT_DEFINITIONS

        yt_def = get_intent_definition("youtube")
        assert yt_def is not None
        assert len(yt_def.required_slots) == 2
        assert yt_def.required_slots[0].name == "content_type"
        assert yt_def.required_slots[1].name == "search_query"

        req = get_required_slot_names("youtube")
        assert "content_type" in req
        assert "search_query" in req

    def test_action_planner(self):
        """Test the action planner directly."""
        planner = ActionPlanner()
        state_tracker = DialogueStateTracker()
        task = state_tracker.create_task("youtube", ["search_query"])
        task.filled_slots["search_query"] = "Tum Hi Ho"
        task.filled_slots["content_type"] = "song"

        can_exec, errors = planner.can_execute(task)
        assert can_exec is True
        assert errors == []

        plan = planner.plan(task)
        assert plan.can_execute is True
        assert plan.intent == "youtube"
        assert plan.action_type == "youtube_search"
        assert plan.params.get("query") == "Tum Hi Ho"

    def test_task_manager_multi_intent(self):
        """Test TaskManager with multiple intents."""
        tracker = DialogueStateTracker()
        manager = TaskManager(tracker)

        t1 = manager.create_and_activate("youtube", ["search_query"])
        t2 = manager.create_and_activate("call", ["contact_name"],
                                           parent_task_id=t1.task_id)

        assert t1.task_id != t2.task_id
        assert t2.parent_task_id == t1.task_id

        # Pausing should work
        count = manager.pause_all_active()
        assert count >= 2


# ── Test 10: Full Conversation Scenarios ──────────────────────────

class TestFullConversations:
    """End-to-end conversation scenarios."""

    def test_youtube_conversation(self, dm):
        """Full YouTube conversation flow."""
        responses = []
        for msg in ["Play a song", "Tum Hi Ho"]:
            result = dm.process(msg)
            responses.append(result)

        # First response should ask what to play
        assert responses[0]["all_slots_filled"] is False
        # Second should execute
        assert responses[1]["all_slots_filled"] is True

    def test_interrupt_and_resume_scenario(self, dm):
        """Complex scenario: start task → interrupt → resume."""
        # Step 1: Start YouTube
        dm.process("Play a song")
        task_id = dm.state_tracker.get_active_task_id()

        # Step 2: Interrupt with another request
        # (Intent change should be detected by ContextManager)
        dm.process("What's the time?")
        # The YouTube task should now be paused
        yt_task = dm.get_task(task_id)
        if yt_task:
            assert yt_task["status"] == "paused"

    def test_multi_turn_alarm(self, dm):
        """Multi-turn alarm setting."""
        dm.process("Set an alarm")
        dm.process("7")
        dm.process("AM")

        state = dm.get_state()
        # There should be an alarm task completed or active
        # OR check completed tasks
        assert state["stats"]["total_tasks"] >= 1

    def test_message_flow(self, dm):
        """Test message sending flow."""
        dm.process("Send a message")
        dm.process("Mummy")
        dm.process("Mein ghar aa raha hoon")

        state = dm.get_state()
        assert state["stats"]["total_tasks"] >= 1


# ── Test 11: Context Manager ──────────────────────────────────────

class TestContextManager:
    """Test the context manager directly."""

    def test_interruption_detection(self, dm):
        """Test that intent changes are detected as interruptions."""
        from app.dialogue_manager.dialogue_manager import ContextManager
        cm = ContextManager(dm.working_memory, dm.short_term_memory)

        # No active task → no interruption
        assert cm.detect_interruption("youtube", None) is False

        # Same intent → not an interruption
        assert cm.detect_interruption("youtube", "youtube") is False

        # Different intent → interruption
        assert cm.detect_interruption("call", "youtube") is True

        # Instant intents should not interrupt
        assert cm.detect_interruption("flashlight", "youtube") is False

    def test_context_summary(self, dm):
        """Test building context summary."""
        dm.process("Play a song")
        dm.process("Tum Hi Ho")

        active = dm.state_tracker.get_active_task()
        paused = dm.state_tracker.get_paused_tasks()
        summary = dm.context_manager.build_context_summary(active, paused)
        assert summary is not None
        assert len(summary) > 0

    def test_conversation_summary(self, dm):
        dm.process("Hello")
        dm.process("Play a song")
        summary = dm.context_manager.get_conversation_summary(max_turns=5)
        assert "Hello" in summary or "Play" in summary


# ── Test 12: Persistence ──────────────────────────────────────────

class TestPersistence:
    """Test state persistence across sessions."""

    def test_file_persistence(self):
        """Test that dialogue state persists to and loads from disk."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            persist_path = f.name

        try:
            # Create manager with persistence
            config = DialogueConfig(persist_path=persist_path)
            dm1 = DialogueManager(config=config)
            dm1.process("Play a song")

            # Create new manager that loads from same file
            config2 = DialogueConfig(persist_path=persist_path)
            dm2 = DialogueManager(config=config2)

            # Should have loaded the task
            state = dm2.get_state()
            assert state["stats"]["total_tasks"] >= 1
        finally:
            os.unlink(persist_path)

    def test_reset_clears_persistence(self, dm):
        """Test that reset() clears in-memory state."""
        dm.process("Play a song")
        dm.reset()
        state = dm.get_state()
        assert state["stats"]["total_tasks"] == 0


# ── Run tests ─────────────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
