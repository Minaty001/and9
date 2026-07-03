"""
AND9 — Dialogue Manager (Main Orchestrator).

The primary entry point for multi-turn dialogue processing. Wraps the
existing AND9 engine with conversation memory, slot filling, reference
resolution, and task management.

Processing Pipeline:
  1. Reference Resolution — resolve pronouns, "it", "continue", etc.
  2. Cancel/Resume Detection — handle meta-commands
  3. Interruption Check — detect topic switches
  4. Intent Detection — use existing AND9 intent_router
  5. DST Update — create or update task state
  6. Slot Check — determine which slots are missing
  7. Slot Filling — try to fill slots from user message
  8. Action Planning — validate, plan execution
  9. Execute or Ask — run action or generate next question
  10. Memory Update — update all memory layers
  11. Return Response

Usage:
    dm = DialogueManager()
    result = dm.process("Play a song")
    print(result["response"])
    # → "Kaunsa gaana bajau?"

    result = dm.process("Tum Hi Ho")
    print(result["response"])
    # → "Baja raha hoon 'Tum Hi Ho'! 🎶"
    print(result["executed"])
    # → True
"""

import logging
import re
import time
import threading
from typing import Any, Optional

from app.dialogue_manager.intent_definitions import (
    get_intent_definition,
    get_required_slot_names,
    get_optional_slot_names,
    get_all_slot_names,
)
from app.dialogue_manager.slot_filler import SlotFiller
from app.dialogue_manager.state_manager import (
    DialogueStateTracker,
    TaskState,
    TaskStatus,
)
from app.dialogue_manager.task_manager import TaskManager
from app.dialogue_manager.working_memory import (
    WorkingMemory,
    ShortTermMemory,
    ActiveTaskMemory,
    DialogueConfig,
)
from app.dialogue_manager.context_manager import ContextManager
from app.dialogue_manager.reference_resolver import ReferenceResolver
from app.dialogue_manager.action_planner import ActionPlanner, ExecutionPlan

logger = logging.getLogger(__name__)


class DialogueManager:
    """Main entry point for multi-turn dialogue processing.

    Integrates all sub-components (state tracking, slot filling,
    reference resolution, context management, action planning)
    into a single process() method.

    Thread-safe: Each public method acquires a lock.
    """

    def __init__(self, config: Optional[DialogueConfig] = None,
                 and9_orchestrator=None, events_sys=None):
        """Initialize the Dialogue Manager.

        Args:
            config: Optional DialogueConfig. Uses defaults if not provided.
            and9_orchestrator: Optional AND9 Orchestrator instance for action
                               execution. If None, the planner builds payloads
                               but execution is left to the caller.
            events_sys: Optional EventSystem for reminder persistence.
        """
        self.config = config or DialogueConfig()

        # ── Thread safety lock ────────────────────────────────────
        self._lock = threading.Lock()

        # ── External systems ──────────────────────────────────────
        self._executor = and9_orchestrator
        self.events_sys = events_sys
        self.short_term_memory = ShortTermMemory(default_ttl=self.config.entity_ttl)
        self.working_memory = WorkingMemory(max_history=self.config.max_history)
        self.active_task_memory = ActiveTaskMemory()

        self.state_tracker = DialogueStateTracker(
            persist_path=self.config.persist_path
        )
        self.task_manager = TaskManager(self.state_tracker)
        self.slot_filler = SlotFiller()
        self.context_manager = ContextManager(
            self.working_memory, self.short_term_memory
        )
        self.reference_resolver = ReferenceResolver(
            self.working_memory, self.short_term_memory
        )
        self.action_planner = ActionPlanner()

        # External action executor (AND9 orchestrator)
        self._executor = and9_orchestrator

        # Last cleanup timestamp
        self._last_cleanup = time.time()

        logger.info("DialogueManager initialized (max_history=%d, max_tasks=%d)",
                     self.config.max_history, self.config.max_active_tasks)

    def process(self, user_message: str) -> dict[str, Any]:
        """Process a user message through the full dialogue pipeline.

        Args:
            user_message: The user's input text.

        Returns:
            Dict with:
              - response: str — Natural language reply
              - task_id: str or None
              - intent: str — Detected intent
              - status: str — Task status
              - waiting_for: str or None
              - filled_slots: dict
              - missing_slots: list
              - all_slots_filled: bool
              - can_execute: bool
              - executed: bool
              - action_result: dict or None
              - time_ms: float
              - error: str or None
        """
        start = time.perf_counter()
        result = self._build_empty_result()

        if not user_message or not user_message.strip():
            result["response"] = "Kya karna hai? Kuch batao na!"
            result["time_ms"] = (time.perf_counter() - start) * 1000
            return result

        try:
            # Periodic cleanup
            self._auto_cleanup()

            # ── Step 1: Reference Resolution ──────────────────────────
            resolved_message, ref_meta = self.reference_resolver.resolve(user_message)

            # ── Step 2: Cancel Detection ──────────────────────────
            if ref_meta.get("cancel_requested"):
                with self._lock:
                    return self._handle_cancel(resolved_message, result, start)

            # ── Step 3: Resume Detection ──────────────────────────
            if ref_meta.get("resume_requested"):
                with self._lock:
                    resumed = self.task_manager.resume_most_recent_paused()
                if resumed:
                    with self._lock:
                        return self._continue_task(resumed, result, start, user_message)
                # No paused tasks — maybe the current task is already
                # active but the user said "continue" to proceed with it.
                # Don't fall through to slot-filling with "continue" as value.
                current_active = self.state_tracker.get_active_task()
                if (current_active and current_active.is_active
                        and current_active.intent not in ("chat", None)):
                    with self._lock:
                        return self._continue_task(current_active, result, start, user_message)

            # ── Steps 4-10: Full processing pipeline (thread-safe) ──
            with self._lock:
                intent_name, params = self._detect_intent(resolved_message)

                if not intent_name:
                    result["response"] = "Mujhe samajh nahi aaya. Zara aur clearly batao! 🤔"
                    result["time_ms"] = (time.perf_counter() - start) * 1000
                    self._update_memory(user_message, result["response"], "unknown", None)
                    return result

                result["intent"] = intent_name

                required_slots = get_required_slot_names(intent_name)
                optional_slots = get_optional_slot_names(intent_name)
                active_task = self.state_tracker.get_active_task()

                # Continuation check for active task
                if (active_task and active_task.is_active
                    and active_task.status in (TaskStatus.PENDING, TaskStatus.WAITING_FOR_INFO)
                    and intent_name in ("chat", None)
                    and active_task.intent != "chat"
                    and not self._is_new_topic_request(resolved_message)):
                    task = active_task
                    logger.debug("Assuming continuation of task %s (msg='%s')",
                                 task.task_id, resolved_message[:40])
                    self._fill_from_message(task, resolved_message, params)
                    self._update_entity_memory(task, resolved_message)
                    self._fill_from_completed_task(task, ref_meta)
                    return self._handle_task_state(task, user_message, result, start)

                # Interruption check
                if active_task and active_task.is_active and active_task.status not in (
                    TaskStatus.COMPLETED, TaskStatus.CANCELLED, TaskStatus.FAILED
                ):
                    is_interruption = self.context_manager.detect_interruption(
                        intent_name, active_task.intent
                    )
                    if is_interruption:
                        return self._handle_interruption(
                            user_message, resolved_message, intent_name,
                            required_slots, optional_slots, active_task,
                            result, start, params
                        )

                # Create or reuse task
                task = None
                if active_task and active_task.intent == intent_name and active_task.is_active:
                    task = active_task
                    logger.debug("Continuing existing task %s (intent=%s)",
                                 task.task_id, intent_name)
                else:
                    if active_task and active_task.is_active:
                        self.state_tracker.pause_task(active_task.task_id)
                        logger.debug("Paused task %s while switching to intent '%s'",
                                     active_task.task_id, intent_name)
                    task = self.task_manager.create_and_activate(
                        intent=intent_name,
                        required_slots=required_slots,
                        optional_slots=optional_slots,
                    )

                self._fill_from_message(task, resolved_message, params)
                self._update_entity_memory(task, resolved_message)
                self._fill_from_completed_task(task, ref_meta)

                return self._handle_task_state(task, user_message, result, start)

        except Exception as e:
            logger.exception("DialogueManager.process() error")
            elapsed = (time.perf_counter() - start) * 1000
            result["response"] = f"Kuch gadbad ho gayi: {e}. Phir se try karo! 😅"
            result["error"] = str(e)
            result["time_ms"] = elapsed
            return result

    # ── Handle Task State ──────────────────────────────────────────

    def _handle_task_state(self, task: TaskState, user_message: str,
                           result: dict, start: float) -> dict:
        """Determine next action based on task state.

        If all slots filled → plan and execute.
        If slots missing → ask next question.
        """
        # Set task and intent in result
        result["task_id"] = task.task_id
        result["intent"] = task.intent
        result["filled_slots"] = dict(task.filled_slots)
        result["missing_slots"] = list(self.slot_filler.get_missing_required_slots(task))

        # Update last messages
        self.state_tracker.update_task(
            task.task_id,
            last_user_message=user_message,
        )

        # Check if all required slots are filled
        if self.slot_filler.all_required_filled(task):
            self.state_tracker.mark_ready(task.task_id)

            # Plan execution
            plan = self.action_planner.plan(task)

            if plan.can_execute:
                # Execute
                return self._execute_and_respond(task, plan, result, start, user_message)
            else:
                # Validation failed
                self.state_tracker.mark_failed(task.task_id, "; ".join(plan.errors))
                result["response"] = f"Execution plan nahi ban paaya: {'; '.join(plan.errors)} 😅"
                result["status"] = "failed"
                result["can_execute"] = False
                result["time_ms"] = (time.perf_counter() - start) * 1000
                self._update_memory(user_message, result["response"],
                                     task.intent, task.task_id)
                return result
        else:
            # Determine what to ask next
            self.state_tracker.mark_waiting(
                task.task_id,
                waiting_for=self.slot_filler.determine_waiting_for(task) or ""
            )

            # Get the next question for the missing slot
            question = self.slot_filler.get_next_question(task)

            if question:
                # Ask for the next slot
                task.last_assistant_message = question
                self.state_tracker.update_task(task.task_id,
                                                last_assistant_message=question)

                result["response"] = question
                result["status"] = "waiting_for_info"
                result["waiting_for"] = task.waiting_for
                result["can_execute"] = False
                result["all_slots_filled"] = False
                result["time_ms"] = (time.perf_counter() - start) * 1000

                self._update_memory(user_message, question, task.intent, task.task_id)
                return result
            else:
                # No question but not all filled — edge case
                # List the missing slots to guide the user
                missing = self.slot_filler.get_missing_required_slots(task)
                if missing:
                    result["response"] = f"Mujhe {', '.join(missing[:3])} ki zaroorat hai. Kya bata sakte hain? 😊"
                else:
                    result["response"] = "Kuch aur batao? Main ready hoon! 😊"
                result["status"] = "waiting_for_info"
                result["missing_slots"] = missing
                result["time_ms"] = (time.perf_counter() - start) * 1000
                self._update_memory(user_message, result["response"],
                                     task.intent, task.task_id)
                return result

    def _execute_and_respond(self, task: TaskState, plan: ExecutionPlan,
                              result: dict, start: float,
                              user_message: str = "") -> dict:
        """Execute the planned action and return the response."""
        self.state_tracker.mark_executing(task.task_id)

        execution_result = None
        executed = False

        if self._executor:
            try:
                # Execute via AND9 orchestrator
                # The executor expects (action_type, params, events_sys) signature
                and9_result = self._executor(
                    action_type=plan.action_type or "",
                    params=plan.params,
                    events_sys=self.events_sys,
                )
                execution_result = and9_result
                executed = True

                # Extract response from AND9 result
                if isinstance(and9_result, dict):
                    response = and9_result.get("response", plan.success_message)
                else:
                    response = str(and9_result)

            except Exception as e:
                logger.error("Execution failed: %s", e)
                self.state_tracker.mark_failed(task.task_id, str(e))
                result["response"] = plan.failure_message
                result["status"] = "failed"
                result["executed"] = False
                result["error"] = str(e)
                result["time_ms"] = (time.perf_counter() - start) * 1000
                self._update_memory(user_message, result["response"], task.intent, task.task_id)
                return result
        else:
            # No executor — just return the plan
            response = plan.success_message
            execution_result = plan.to_dict()

        # Mark completed
        self.state_tracker.mark_completed(task.task_id)

        # Check if there are paused tasks to resume
        resumed = self.task_manager.complete_and_continue(task.task_id)
        resume_note = ""
        if resumed:
            resume_note = f" Aapka {resumed.intent} task bhi pending hai — karna chahenge?"

        task.last_assistant_message = response
        self.state_tracker.update_task(task.task_id,
                                        last_assistant_message=response)

        result["task_id"] = task.task_id
        result["intent"] = task.intent
        result["response"] = response + resume_note
        result["status"] = "completed"
        result["all_slots_filled"] = True
        result["can_execute"] = True
        result["executed"] = executed
        result["action_result"] = execution_result
        result["waiting_for"] = None
        result["time_ms"] = (time.perf_counter() - start) * 1000

        self._update_memory(user_message, response, task.intent, task.task_id)
        return result

    # ── Handle Interruption ───────────────────────────────────────

    def _handle_interruption(self, user_message: str, resolved_message: str,
                              new_intent: str,
                              required_slots: list[str],
                              optional_slots: list[str],
                              interrupted_task: TaskState,
                              result: dict, start: float,
                              detected_params: Optional[dict] = None) -> dict:
        """Handle a user interrupting the current task with a new request."""
        detected_params = detected_params or {}
        # Pause the current task
        self.state_tracker.pause_task(interrupted_task.task_id)
        logger.info("Interrupted task %s for new intent '%s'",
                     interrupted_task.task_id, new_intent)

        # If the new intent is chat, handle it gracefully — no action mapping
        if new_intent == "chat":
            task = self.task_manager.create_and_activate(
                intent="chat",
                required_slots=required_slots,
                optional_slots=optional_slots,
                parent_task_id=interrupted_task.task_id,
            )
            self._fill_from_message(task, resolved_message, detected_params)
            self._update_entity_memory(task, resolved_message)
            self.state_tracker.mark_completed(task.task_id)
            result["response"] = f"OK, main sun raha hoon! Aapne kaha: \"{resolved_message}\""
            result["intent"] = "chat"
            result["status"] = "completed"
            result["task_id"] = task.task_id
            result["all_slots_filled"] = True
            result["time_ms"] = (time.perf_counter() - start) * 1000
            result["paused_task_id"] = interrupted_task.task_id
            self._update_memory(user_message, result["response"], "chat", task.task_id)
            return result

        # If the new intent is instant (flashlight, etc.), execute directly
        if new_intent in ("flashlight", "wifi", "bluetooth", "volume", "camera", "home"):
            # Create and execute directly
            task = self.task_manager.create_and_activate(
                intent=new_intent,
                required_slots=required_slots,
                optional_slots=optional_slots,
                parent_task_id=interrupted_task.task_id,
            )
            self._fill_from_message(task, resolved_message, detected_params)

            # Check if we can execute immediately
            if self.slot_filler.all_required_filled(task):
                self.state_tracker.mark_ready(task.task_id)
                plan = self.action_planner.plan(task)
                if plan.can_execute:
                    exec_result = self._execute_and_respond(task, plan, result, start, user_message)
                    # Add note about paused task
                    exec_result["response"] += (
                        f" Aapka {interrupted_task.intent} ka task ruk gaya hai — "
                        f"'continue' bolo to wahan se jaari rakhein!"
                    )
                    exec_result["paused_task_id"] = interrupted_task.task_id
                    return exec_result

        # Create a new task for the interruption
        task = self.task_manager.create_and_activate(
            intent=new_intent,
            required_slots=required_slots,
            optional_slots=optional_slots,
            parent_task_id=interrupted_task.task_id,
        )

        # Link the tasks
        if interrupted_task.parent_task_id is None:
            linked = interrupted_task.linked_tasks
            if task.task_id not in linked:
                linked.append(task.task_id)
            self.state_tracker.update_task(
                interrupted_task.task_id,
                linked_tasks=linked,
            )

        # Fill slots from the resolved message
        self._fill_from_message(task, resolved_message, detected_params)
        self._update_entity_memory(task, resolved_message)

        return self._handle_task_state(task, user_message, result, start)

    # ── Handle Cancel ────────────────────────────────────────────

    def _handle_cancel(self, message: str, result: dict, start: float) -> dict:
        """Handle a cancel/stop request."""
        # Try to extract which task to cancel
        cancel_target = self.reference_resolver.extract_cancel_target(message)
        active = self.state_tracker.get_active_task()

        # Map user-facing cancel targets to internal intent names
        _CANCEL_INTENT_MAP = {
            "music": "youtube",
            "song": "youtube",
            "gaana": "youtube",
            "video": "youtube",
            "alarm": "alarm",
            "timer": "timer",
            "reminder": "reminder",
            "call": "call",
            "message": "message",
        }
        mapped_target = _CANCEL_INTENT_MAP.get(cancel_target, cancel_target) if cancel_target else None

        if mapped_target and active and active.intent == mapped_target:
            self.state_tracker.mark_cancelled(active.task_id)
            response = f"OK, {active.intent} cancel kar diya! ❌"
            result["response"] = response
            result["status"] = "cancelled"
            result["intent"] = active.intent
            result["task_id"] = active.task_id
            result["time_ms"] = (time.perf_counter() - start) * 1000

            # Resume next paused task if any
            next_task = self.task_manager.resume_most_recent_paused()
            if next_task:
                result["response"] += (
                    f" Aapka {next_task.intent} ka task bhi pending hai — continue karein?"
                )
            return result

        if mapped_target and active and active.intent != mapped_target:
            # User asked to cancel a specific task that's not the active one
            msg = f"'{cancel_target}' ka task active nahi hai."
            if active:
                msg += f" Kya aap '{active.intent}' cancel karna chahte hain?"
            result["response"] = msg + " 😕"
            result["time_ms"] = (time.perf_counter() - start) * 1000
            return result

        # No specific cancel target mentioned — cancel active task
        cancelled = self.task_manager.cancel_current_task()
        if cancelled:
            result["response"] = f"OK, {cancelled.intent} band kar diya! ❌"
            result["status"] = "cancelled"
            result["task_id"] = cancelled.task_id
            result["time_ms"] = (time.perf_counter() - start) * 1000

            # Resume next paused task
            next_task = self.task_manager.resume_most_recent_paused()
            if next_task:
                result["response"] += (
                    f" Aapka {next_task.intent} ka task bhi pending hai!"
                )
            return result

        result["response"] = "Koi active task nahi hai cancel karne ke liye! 😊"
        result["time_ms"] = (time.perf_counter() - start) * 1000
        return result

    # ── Continue Task ─────────────────────────────────────────────

    def _continue_task(self, task: TaskState, result: dict,
                        start: float, user_message: str = "") -> dict:
        """Continue a previously paused task.

        Restores the task as active and generates the next question.
        """
        self.state_tracker.resume_task(task.task_id)

        if self.slot_filler.all_required_filled(task):
            # Ready to execute
            self.state_tracker.mark_ready(task.task_id)
            plan = self.action_planner.plan(task)
            if plan.can_execute:
                return self._execute_and_respond(task, plan, result, start)
            else:
                # Plan validation failed — report actual errors
                errors = "; ".join(plan.errors) if plan.errors else "Execution plan nahi ban paaya"
                result["response"] = f"Chaliye, {task.intent} jaari rakhte hain, lekin plan mein problem hai: {errors} 😅"
                result["status"] = "failed"
                result["can_execute"] = False
                result["time_ms"] = (time.perf_counter() - start) * 1000
                self.state_tracker.mark_failed(task.task_id, errors)
                return result
        else:
            # Ask next question
            question = self.slot_filler.get_next_question(task)
            if question:
                self.state_tracker.mark_waiting(
                    task.task_id,
                    waiting_for=self.slot_filler.determine_waiting_for(task) or ""
                )
                result["response"] = f"Chaliye, {task.intent} jaari rakhte hain! {question}"
                result["status"] = "waiting_for_info"
                result["waiting_for"] = task.waiting_for
            else:
                result["response"] = f"Chaliye, {task.intent} jaari rakhte hain! Aage kya karna hai?"
                result["status"] = "resumed"

            result["task_id"] = task.task_id
            result["intent"] = task.intent
            result["time_ms"] = (time.perf_counter() - start) * 1000
            return result

    # ── Helpers ──────────────────────────────────────────────────

    def _fill_from_completed_task(self, task: TaskState,
                                    ref_meta: dict) -> None:
        """Copy unfilled slots from a recently completed task.

        When references are resolved (e.g. "Play that again" → "that"
        resolves to a previous entity), this copies the slot values from
        a recently completed task with the same intent, so the user
        doesn't have to re-supply information already given.

        Args:
            task: The current (new) task that may need slots copied.
            ref_meta: The metadata dict from reference_resolver.resolve().
        """
        if not ref_meta.get("resolved"):
            return
        if not task.required_slots:
            return

        # Find a recently completed task with the same intent
        completed = self.state_tracker.get_tasks_by_intent(task.intent)
        for past_task in completed:
            if (past_task.task_id != task.task_id
                    and past_task.status == TaskStatus.COMPLETED
                    and past_task.filled_slots):
                for slot_name, slot_value in past_task.filled_slots.items():
                    if (slot_name in task.required_slots
                            and slot_name not in task.filled_slots):
                        self.slot_filler.fill_slot(task, slot_name, slot_value)
                logger.debug("Copied slots from completed task %s to %s",
                             past_task.task_id, task.task_id)
                return

    def _detect_intent(self, message: str) -> tuple[Optional[str], dict]:
        """Detect intent using the AND9 intent router.

        Uses QueryNormalizer for Hindi→English normalization before
        passing to the intent router for consistent detection.

        Returns:
            Tuple of (intent_name, params_dict).
        """
        try:
            from app.router.intent_router import detect_intent
            from app.router.normalizer import QueryNormalizer
            normalizer = QueryNormalizer()
            normalized, _ = normalizer.normalize(message)
            intent_name, action_type, params = detect_intent(normalized)

            # If AND9 returns "chat", try fallback to catch
            # reconstructed references like "play" in "Play Tum Hi Ho again"
            # that the reference resolver built but AND9 did not recognize.
            if intent_name == "chat":
                fallback_name, fallback_params = self._fallback_intent_detect(message)
                if fallback_name and fallback_name != "chat":
                    logger.debug("Fallback override: AND9='chat', fallback='%s'",
                                 fallback_name)
                    return fallback_name, fallback_params

            return intent_name, params
        except ImportError:
            logger.warning("AND9 intent_router not available, using fallback")
            return self._fallback_intent_detect(message)
        except Exception as e:
            logger.error("Intent detection error: %s", e)
            return None, {}

    @staticmethod
    def _fallback_intent_detect(message: str) -> tuple[Optional[str], dict]:
        """Fallback intent detection if AND9 router is unavailable."""
        import re
        q = message.lower().strip()
        if not q:
            return None, {}

        # Simple keyword matching
        if re.search(r'\b(call|phone|dial)\b', q):
            return "call", {"contact_name": q}
        if re.search(r'\b(message|msg|text|sms)\b', q):
            return "message", {"contact_name": q}
        if re.search(r'\b(alarm)\b', q):
            return "alarm", {"query": q}
        if re.search(r'\b(timer)\b', q):
            return "timer", {"query": q}
        if re.search(r'\b(remind|reminder)\b', q):
            return "reminder", {"query": q}
        if re.search(r'\b(open|khol|launch)\b', q):
            return "open_app", {"query": q}
        if re.search(r'\b(youtube|video|song|gaana|music|play)\b', q):
            return "youtube", {"query": q}
        if re.search(r'\b(search|find|look up|google)\b', q):
            return "search", {"query": q}
        if re.search(r'\b(flash|torch)\b', q):
            state = "on" if re.search(r'\b(on|chaalu)\b', q) else "off"
            return "flashlight", {"state": state}
        if re.search(r'\b(wifi)\b', q):
            state = "on" if re.search(r'\b(on|chaalu)\b', q) else "off"
            return "wifi", {"state": state}
        if re.search(r'\b(volume)\b', q):
            return "volume", {"query": q}

        return "chat", {"query": q}

    @staticmethod
    def _is_new_topic_request(message: str) -> bool:
        """Check if a message looks like a new topic/question rather than an answer.

        Detects standalone questions and topic shifts that should be
        treated as interruptions, not slot-filling continuations.

        Args:
            message: The user's resolved message.

        Returns:
            True if the message starts a new topic or asks a question.
        """
        msg = message.lower().strip()
        if not msg:
            return False
        # Questions starting with wh-words (English + Hindi/Urdu)
        if re.search(r'^(what|where|when|why|how|who|which'
                     r'|kya|kaun|kahan|kab|kyun|kaise|kiske|kis|kaunsa'
                     r'|kyu|kyaa|konse)\b', msg, re.IGNORECASE):
            return True
        if msg.endswith('?'):
            return True
        # Topic shift markers (English + Hindi/Urdu)
        if re.search(r'^(actually|by the way|btw|anyway|hey|listen|wait|oh'
                     r'|sun|suno|are|arre|acha|achha|accha|dekho|dekhiye)\b', msg, re.IGNORECASE):
            return True
        return False

    def _fill_from_message(self, task: TaskState, message: str,
                            detected_params: dict):
        """Fill slots from both the user message and detected parameters.

        Args:
            task: The task to update slots on.
            message: The resolved user message.
            detected_params: Parameters already extracted by intent_router.
        """
        # First, try to fill from detected parameters (most reliable)
        # But validate through the slot classifiers to reject bogus values
        # like "an" extracted from "Open an app" as app_name.
        for slot_name in get_all_slot_names(task.intent):
            if slot_name not in task.filled_slots and slot_name in detected_params:
                value = detected_params[slot_name]
                if value is not None and value not in (None, "", "unknown"):
                    # Validate through slot classifier if one exists
                    validated = self.slot_filler.validate_slot_value(
                        slot_name, str(value), message
                    )
                    if validated is not None:
                        self.slot_filler.fill_slot(task, slot_name, validated)

        # Then, try to fill the currently waited-for slot from the message
        self.slot_filler.try_fill_from_message(task, message)

        # Auto-fill related slots: if hour was set with a time expression
        # like "7 AM" (no explicit minute), default minute to "0".
        if ("hour" in task.filled_slots and "minute" in task.required_slots
                and "minute" not in task.filled_slots):
            hour_val = str(task.filled_slots["hour"]).lower().strip()
            # Check if the hour value contains a parseable time without minute
            time_match = re.match(
                r'^(\d{1,2})\s*(?::(\d{2}))?\s*(am|pm)?\s*$',
                hour_val, re.IGNORECASE
            )
            if time_match:
                explicit_min = time_match.group(2)
                if explicit_min is not None:
                    self.slot_filler.fill_slot(task, "minute", explicit_min)
                else:
                    # "7 AM" without minutes → default to "0"
                    self.slot_filler.fill_slot(task, "minute", "0")

        # If content type was detected but slot wasn't explicitly filled,
        # try one more time with the full message
        if "content_type" in task.required_slots and "content_type" not in task.filled_slots:
            self.slot_filler.try_fill_from_message(task, message)

    def _update_entity_memory(self, task: TaskState, message: str):
        """Update short-term memory with entities from the task."""
        # Remember the task intent for context
        self.short_term_memory.remember("last_intent", task.intent, ttl=120)

        # Remember the last action target for reference resolution
        for key in ["search_query", "song_name", "app_name",
                      "contact_name", "query"]:
            if key in task.filled_slots:
                self.short_term_memory.remember(
                    "last_action_target", task.filled_slots[key], ttl=120
                )
                break

        # Remember the current entity for "this" resolution
        if task.filled_slots:
            last_key = list(task.filled_slots.keys())[-1]
            self.short_term_memory.remember(
                "current_entity", task.filled_slots[last_key], ttl=60
            )

    def _update_memory(self, user_message: str, assistant_message: str,
                        intent: str, task_id: Optional[str]):
        """Update all memory layers after a turn."""
        self.working_memory.add_turn(
            user_message=user_message,
            assistant_message=assistant_message,
            intent=intent,
            task_id=task_id or "",
        )

    def _auto_cleanup(self):
        """Periodically clean up old completed tasks."""
        now = time.time()
        if now - self._last_cleanup > self.config.auto_cleanup_interval:
            count = self.state_tracker.cleanup_old_tasks()
            if count > 0:
                logger.info("Auto-cleanup removed %d old tasks", count)
            self._last_cleanup = now

    def _build_empty_result(self) -> dict:
        """Build a standard empty result dict."""
        return {
            "response": "",
            "task_id": None,
            "intent": None,
            "status": "pending",
            "waiting_for": None,
            "filled_slots": {},
            "missing_slots": [],
            "all_slots_filled": False,
            "can_execute": False,
            "executed": False,
            "action_result": None,
            "error": None,
            "time_ms": 0.0,
        }

    # ── Public API ─────────────────────────────────────────────────

    def get_state(self) -> dict:
        """Get the full state of the dialogue manager.

        Returns dict with active tasks, paused tasks, memory stats.
        """
        return {
            "active_task": self.state_tracker.get_active_task().to_dict()
            if self.state_tracker.get_active_task() else None,
            "active_tasks": [t.to_dict() for t in self.state_tracker.get_active_tasks()],
            "paused_tasks": [t.to_dict() for t in self.state_tracker.get_paused_tasks()],
            "stats": self.state_tracker.get_stats(),
            "memory": {
                "turn_count": self.working_memory.get_turn_count(),
                "recent_intents": self.working_memory.get_active_intents(),
                "short_term_entities": self.short_term_memory.get_all(),
            },
        }

    def get_task(self, task_id: str) -> Optional[dict]:
        """Get a specific task's state as a dict."""
        task = self.state_tracker.get_task(task_id)
        return task.to_dict() if task else None

    def get_tasks(self, active_only: bool = True) -> list[dict]:
        """Get all tasks as dicts.

        Args:
            active_only: If True, only return non-terminal tasks.

        Returns:
            List of task state dicts.
        """
        if active_only:
            return [t.to_dict() for t in self.state_tracker.get_active_tasks()]
        return [t.to_dict() for t in self.state_tracker.get_all_tasks().values()]

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a specific task by ID."""
        task = self.state_tracker.get_task(task_id)
        if task:
            self.state_tracker.mark_cancelled(task_id)
            logger.info("Cancelled task %s via API", task_id)
            return True
        return False

    def get_conversation_history(self, n: int = 20) -> list:
        """Get recent conversation history."""
        return self.working_memory.to_dict_list(n)

    def reset(self):
        """Reset all dialogue state (clear everything)."""
        self.short_term_memory.clear()
        self.working_memory.clear()
        # Re-create tracker without persistence
        self.state_tracker = DialogueStateTracker()
        self.task_manager = TaskManager(self.state_tracker)
        logger.info("DialogueManager reset complete")
