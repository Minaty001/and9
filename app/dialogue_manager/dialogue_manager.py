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
from app.dialogue_manager.working_memory import (
    WorkingMemory,
    ShortTermMemory,
    ActiveTaskMemory,
    DialogueConfig,
)
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
        if new_intent in ("flashlight", "wifi", "bluetooth", "bluetooth_scan", "bluetooth_paired", "volume", "camera", "home"):
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


class ReferenceResolver:
    """Resolves references in user messages using conversation context.

    Uses working memory to find antecedents for pronouns and other
    referring expressions. Returns a resolved message string that
    replaces references with their concrete antecedents.
    """

    # ── Pattern Groups ─────────────────────────────────────────────

    # Patterns that signal a resume/continue request
    RESUME_PATTERNS = [
        re.compile(r'^\s*(continue|resume|go on|jari rakho|jaari rakho|phir se)\s*$', re.IGNORECASE),
        re.compile(r'^\s*(continue|resume|jari rakho)\s+(that|the|us|with)\s', re.IGNORECASE),
        re.compile(r'\b(?:now\s+)?(?:continue|resume)\s+(?:that|the|this|it)\b', re.IGNORECASE),
        re.compile(r'\bnow\s+(?:continue|resume)\b', re.IGNORECASE),
        re.compile(r'\b(same as before|same thing|wahi|wahi kaam)\b', re.IGNORECASE),
        re.compile(r'\b(resume|continue)\s+(?:karo|karein|kar do|kardo)\b', re.IGNORECASE),
    ]

    # Patterns that signal cancellation
    CANCEL_PATTERNS = [
        re.compile(r'\b(?:cancel|stop|abort|halt|cancel karo|band karo|cancel kar do|'
                   r'nahi (?:karna|kar|chahiye)|mat karo|rok do|hua|hoga)\b', re.IGNORECASE),
        re.compile(r"\b(?:don't|dont|do not|dont't)\s+(?:play|want|need|like|karna|karo)\b", re.IGNORECASE),
    ]

    # Pronoun patterns
    IT_PATTERN = re.compile(r'\bit\b', re.IGNORECASE)
    THAT_PATTERN = re.compile(r'\bthat\b', re.IGNORECASE)
    THIS_PATTERN = re.compile(r'\bthis\b', re.IGNORECASE)
    THEM_PATTERN = re.compile(r'\bthem\b', re.IGNORECASE)
    THOSE_PATTERN = re.compile(r'\bthose\b', re.IGNORECASE)
    THESE_PATTERN = re.compile(r'\bthese\b', re.IGNORECASE)

    # Action + reference patterns: "play it", "open it", "call them", etc.
    ACTION_REF_PATTERNS = [
        re.compile(r'\b(play|play karo|bajao|chalao|sunao)\s+(?:that|it|this)\b', re.IGNORECASE),
        re.compile(r'\b(open|kholo|khol)\s+(?:that|it|this|them)\b', re.IGNORECASE),
        re.compile(r'\b(call|phone|dial)\s+(?:them|that person|him|her|us)\b', re.IGNORECASE),
        re.compile(r'\b(message|msg|text|sms)\s+(?:them|him|her|that person)\b', re.IGNORECASE),
        re.compile(r'\b(search|find|dhundh|dhundo|search karo)\s+(?:that|it|this)\b', re.IGNORECASE),
        re.compile(r'\b(set|lagao|daal do)\s+(?:that|it|this)\b', re.IGNORECASE),
    ]

    def __init__(self, working_memory: WorkingMemory,
                 short_term_memory: ShortTermMemory):
        self.wm = working_memory
        self.stm = short_term_memory

    def resolve(self, message: str) -> tuple[str, dict]:
        """Resolve all references in a user message.

        Args:
            message: The raw user message.

        Returns:
            Tuple of (resolved_message, resolution_metadata).
            resolution_metadata contains:
              - resolved: bool — whether any resolution was applied
              - resume_requested: bool
              - cancel_requested: bool
              - resolved_references: list of (reference, antecedent) pairs
              - original_message: str
        """
        original = message.strip()
        if not original:
            return original, {
                "resolved": False,
                "resume_requested": False,
                "cancel_requested": False,
                "resolved_references": [],
                "original_message": original,
            }

        resolved = original
        resolved_refs = []
        resume_requested = self._is_resume_request(original)
        cancel_requested = self._is_cancel_request(original)

        # 1. Resolve "it" → last action target
        if self.IT_PATTERN.search(resolved):
            antecedent = self._resolve_it()
            if antecedent:
                resolved = self.IT_PATTERN.sub(antecedent, resolved, count=1)
                resolved_refs.append(("it", antecedent))

        # 2. Resolve "that" → last mentioned entity
        if self.THAT_PATTERN.search(resolved):
            antecedent = self._resolve_that()
            if antecedent:
                resolved = self.THAT_PATTERN.sub(antecedent, resolved, count=1)
                resolved_refs.append(("that", antecedent))

        # 3. Resolve "this" → current context item
        if self.THIS_PATTERN.search(resolved):
            antecedent = self._resolve_this()
            if antecedent:
                resolved = self.THIS_PATTERN.sub(antecedent, resolved, count=1)
                resolved_refs.append(("this", antecedent))

        # 4. Resolve "them"/"those"/"these"
        if self.THEM_PATTERN.search(resolved):
            antecedent = self._resolve_them()
            if antecedent:
                resolved = self.THEM_PATTERN.sub(antecedent, resolved, count=1)
                resolved_refs.append(("them", antecedent))

        if self.THOSE_PATTERN.search(resolved):
            antecedent = self._resolve_them()  # same logic
            if antecedent:
                resolved = self.THOSE_PATTERN.sub(antecedent, resolved, count=1)
                resolved_refs.append(("those", antecedent))

        if self.THESE_PATTERN.search(resolved):
            antecedent = self._resolve_this()
            if antecedent:
                resolved = self.THESE_PATTERN.sub(antecedent, resolved, count=1)
                resolved_refs.append(("these", antecedent))

        # 5. Resolve action + reference patterns (e.g., "play it")
        resolved, action_refs = self._resolve_action_references(resolved)
        resolved_refs.extend(action_refs)

        logger.debug("Reference resolution: '%s' → '%s' (refs=%s)",
                     original, resolved, resolved_refs)

        return resolved, {
            "resolved": len(resolved_refs) > 0,
            "resume_requested": resume_requested,
            "cancel_requested": cancel_requested,
            "resolved_references": resolved_refs,
            "original_message": original,
        }

    def _is_resume_request(self, message: str) -> bool:
        """Check if the message is a resume/continue request."""
        return any(p.match(message) for p in self.RESUME_PATTERNS)

    def _is_cancel_request(self, message: str) -> bool:
        """Check if the message is a cancel/stop request."""
        return any(p.search(message) for p in self.CANCEL_PATTERNS)

    def _resolve_it(self) -> Optional[str]:
        """Resolve 'it' — the last action's target entity.

        Priority:
          1. ShortTermMemory: last_action_target
          2. WorkingMemory: last turn's entity
          3. WorkingMemory: last mentioned content
        """
        # Check STM first
        target = self.stm.recall("last_action_target")
        if target:
            return str(target)

        # Check working memory for last entity
        entities = self.wm.get_all_entities()
        for key in ["search_query", "song_name", "app_name", "contact_name",
                     "message_text", "query"]:
            if key in entities:
                return str(entities[key])

        # Check last turn for any meaningful content
        last_msg = self.wm.get_last_user_message()
        if last_msg:
            # Extract the last noun phrase (simple heuristic)
            words = last_msg.split()
            if words:
                return words[-1]  # Last word as fallback

        return None

    def _resolve_that(self) -> Optional[str]:
        """Resolve 'that' — previously mentioned entity.

        Similar to 'it' but prefers the entity before the most recent one.
        """
        # Check STM for last_mentioned
        target = self.stm.recall("last_referenced")
        if target:
            return str(target)

        # Fall back to 'it' resolution
        return self._resolve_it()

    def _resolve_this(self) -> Optional[str]:
        """Resolve 'this' — current context item.

        Returns the current task's primary entity if available.
        """
        target = self.stm.recall("current_entity")
        if target:
            return str(target)
        return self._resolve_it()

    def _resolve_them(self) -> Optional[str]:
        """Resolve 'them' — last plural reference.

        Returns the last mentioned contact or group.
        """
        target = self.stm.recall("last_contact")
        if target:
            return str(target)

        # Check for contact in entities
        entities = self.wm.get_all_entities()
        for key in ["contact_name"]:
            if key in entities:
                return str(entities[key])
        return None

    def _resolve_action_references(self, message: str) -> tuple[str, list]:
        """Resolve action-reference combos like 'play it', 'open it'.

        These are replaced with explicit action + entity descriptions.

        Returns:
            Tuple of (modified_message, list_of_(reference, antecedent)).
        """
        resolved_refs = []
        for pattern in self.ACTION_REF_PATTERNS:
            if pattern.search(message):
                antecedent = self._resolve_it()
                if antecedent:
                    # Replace the reference with the concrete entity
                    # e.g., "play it" → "play <song_name>"
                    # Simple: replace full pattern match with just the antecedent
                    message = pattern.sub(antecedent, message)
                    resolved_refs.append((pattern.pattern[:20], antecedent))
        return message, resolved_refs

    # ── Convenience Methods ────────────────────────────────────────

    def is_resume(self, message: str) -> bool:
        """Quick check if message is a resume request."""
        return self._is_resume_request(message)

    def is_cancel(self, message: str) -> bool:
        """Quick check if message is a cancel request."""
        return self._is_cancel_request(message)

    def extract_cancel_target(self, message: str) -> Optional[str]:
        """Try to extract what the user wants to cancel.

        E.g., "cancel music" → "music", "stop the alarm" → "alarm",
        "don't play music" → "music".
        """
        cancel_patterns = [
            re.compile(r'(?:cancel|stop|band karo|nahi)\s+(?:the\s+)?(\w+)', re.IGNORECASE),
            re.compile(r'(\w+)\s+(?:cancel|stop|band karo|mat karo)', re.IGNORECASE),
            re.compile(r"(?:don't|dont|do not)\s+(?:\w+\s+)?(\w+)", re.IGNORECASE),
        ]
        for pattern in cancel_patterns:
            m = pattern.search(message)
            if m:
                target = m.group(1).lower().strip()
                # Map to known intents
                intent_map = {
                    "song": "music",
                    "music": "music",
                    "gaana": "music",
                    "youtube": "youtube",
                    "video": "youtube",
                    "alarm": "alarm",
                    "timer": "timer",
                    "reminder": "reminder",
                    "remind": "reminder",
                    "call": "call",
                    "message": "message",
                    "search": "search",
                    "app": "open_app",
                }
                return intent_map.get(target, target)
        return None


_INSTANT_INTENTS = {
    "flashlight", "volume", "wifi", "bluetooth",
    "camera", "home", "go_home",
}

# Intents that are long-running and more likely to be interrupted
_LONG_RUNNING_INTENTS = {
    "youtube", "music", "call", "message",
    "alarm", "timer", "reminder", "search",
    "open_app",
}


class ContextManager:
    """Manages conversation context across turns.

    Detects interruptions, assembles context for the planner,
    and maintains conversation coherence.
    """

    def __init__(self, working_memory: WorkingMemory,
                 short_term_memory: ShortTermMemory):
        self.wm = working_memory
        self.stm = short_term_memory
        self._consecutive_same_intent = 0

    def detect_interruption(self, new_intent: str,
                            active_task_intent: Optional[str]) -> bool:
        """Detect if the user is switching topics (interrupting).

        An interruption is when:
          - There's an active task waiting for info, AND
          - The new intent is different from the active task intent, AND
          - The new intent is not an instant action (flashlight, etc.)

        Args:
            new_intent: The intent of the new message.
            active_task_intent: The intent of the currently active task.

        Returns:
            True if this is an interruption.
        """
        if not active_task_intent:
            return False

        if new_intent == active_task_intent:
            self._consecutive_same_intent += 1
            return False

        # Reset counter on intent change
        self._consecutive_same_intent = 0

        # If active task is still pending/waiting and new intent is different
        if new_intent != active_task_intent:
            # Don't flag interruptions for instant actions
            if new_intent in _INSTANT_INTENTS:
                return False
            # Chat is not an interruption — it's the default
            if new_intent == "chat" and active_task_intent != "chat":
                # User asking a casual question mid-task
                return True
            return True

        return False

    def detect_resume(self, message: str) -> bool:
        """Detect if the user is asking to resume a paused task.

        Checks for explicit resume keywords.
        """
        resume_keywords = [
            r'\b(continue|resume|go on|jari rakho|jaari rakho)\b',
            r'\b(phir se|again|same as before|same thing)\b',
            r'\b(wahi|wahi kaam|waisa hi)\b',
            r'\b(ab continue|ab resume|ab jari)\b',
        ]
        msg_lower = message.lower().strip()
        for pattern in resume_keywords:
            if re.search(pattern, msg_lower):
                return True

        # Very short affirmative messages after context switch signal resume
        if msg_lower in ("yes", "haan", "ha", "hmm", "ok", "okay", "theek hai"):
            # Check if there are paused tasks
            return True

        return False

    def update_context(self, user_message: str, assistant_response: str,
                       intent: str, task_id: str,
                       entities: Optional[dict[str, str]] = None):
        """Update all context stores after a turn.

        Args:
            user_message: The user's input.
            assistant_response: The assistant's reply.
            intent: Detected intent.
            task_id: Active task ID.
            entities: Optional entities extracted.
        """
        # Add to working memory
        self.wm.add_turn(
            user_message=user_message,
            assistant_message=assistant_response,
            intent=intent,
            task_id=task_id,
            entities=entities or {},
        )

        # Update short-term memory with entities
        if entities:
            for key, value in entities.items():
                self.stm.remember(key, value)

        # Always remember last intent for context
        self.stm.remember("last_intent", intent, ttl=60)

        # Store the last action target for reference resolution
        if entities:
            for target_key in ("search_query", "song_name", "app_name",
                                "contact_name", "query"):
                if target_key in entities:
                    self.stm.remember("last_action_target",
                                      entities[target_key], ttl=120)
                    break

        logger.debug("Context updated: intent=%s task=%s entities=%s",
                     intent, task_id, entities)

    def build_context_summary(self, active_task=None,
                              paused_tasks: Optional[list] = None) -> str:
        """Build a natural-language summary of the current context.

        Used for logging and for the conscious brain to understand
        the current dialogue state.

        Args:
            active_task: The currently active task.
            paused_tasks: List of paused tasks.

        Returns:
            A formatted context summary string.
        """
        parts = []

        if active_task:
            task_info = (
                f"Current Task: {active_task.intent} (ID: {active_task.task_id})\n"
                f"Status: {active_task.status.value}\n"
                f"Filled: {active_task.filled_slots}\n"
                f"Missing: {active_task.missing_slots}\n"
            )
            if active_task.waiting_for:
                task_info += f"Waiting for: {active_task.waiting_for}\n"
            parts.append(task_info)

        if paused_tasks:
            paused_info = "Paused Tasks:\n"
            for task in paused_tasks[-3:]:  # Show last 3
                paused_info += (
                    f"  - {task.intent} (ID: {task.task_id}, "
                    f"filled: {len(task.filled_slots)}/{len(task.required_slots)})\n"
                )
            parts.append(paused_info)

        recent_turns = self.wm.get_last_n(5)
        if recent_turns:
            turns_info = "Recent Conversation:\n"
            for t in recent_turns:
                turns_info += f"  User: {t.user_message[:80]}\n"
                turns_info += f"  Assistant: {t.assistant_message[:80]}\n"
            parts.append(turns_info)

        return "\n".join(parts)

    def should_execute(self, active_task) -> bool:
        """Determine if the active task should be executed now.

        Rules:
          1. All required slots must be filled
          2. Status must be READY_TO_EXECUTE
          3. Task must not be paused or cancelled

        Args:
            active_task: The task to check.

        Returns:
            True if execution should proceed.
        """
        from app.dialogue_manager.state_manager import TaskStatus
        if not active_task:
            return False
        if active_task.status == TaskStatus.CANCELLED:
            return False
        if active_task.status == TaskStatus.PAUSED:
            return False
        return len(active_task.missing_slots) == 0

    def get_conversation_summary(self, max_turns: int = 10) -> str:
        """Get a concise summary of the recent conversation.

        Args:
            max_turns: Maximum turns to include.

        Returns:
            A formatted summary string.
        """
        turns = self.wm.get_last_n(max_turns)
        if not turns:
            return "No conversation history."

        lines = []
        for t in turns:
            lines.append(f"User: {t.user_message}")
            lines.append(f"Assistant: {t.assistant_message}")
        return "\n".join(lines)


_INTENT_PRIORITY = {
    "emergency": 1,
    "call": 2,
    "message": 3,
    "alarm": 4,
    "timer": 5,
    "reminder": 6,
    "open_app": 7,
    "youtube": 8,
    "music": 9,
    "flashlight": 10,
    "volume": 11,
    "wifi": 12,
    "bluetooth": 13,
    "search": 14,
    "chat": 15,
}


class TaskManager:
    """High-level task orchestration.

    Manages the lifecycle and coordination of all active dialogue tasks.
    """

    def __init__(self, state_tracker: DialogueStateTracker):
        self.tracker = state_tracker

    def create_and_activate(self, intent: str,
                            required_slots: list[str],
                            optional_slots: list[str] | None = None,
                            parent_task_id: str | None = None) -> TaskState:
        """Create a new task and make it active.

        Args:
            intent: Intent name.
            required_slots: Required slot names.
            optional_slots: Optional slot names.
            parent_task_id: Optional parent task for interruption linking.

        Returns:
            The newly created TaskState.
        """
        return self.tracker.create_task(
            intent=intent,
            required_slots=required_slots,
            optional_slots=optional_slots or [],
            parent_task_id=parent_task_id,
        )

    def switch_to_task(self, task_id: str) -> bool:
        """Switch the active task to a different one.

        Args:
            task_id: Task to make active.

        Returns:
            True if the switch succeeded.
        """
        task = self.tracker.get_task(task_id)
        if not task:
            return False

        # Pause the current active task if it's still in progress
        current_active = self.tracker.get_active_task()
        if current_active and current_active.task_id != task_id:
            if current_active.is_active and current_active.status not in (
                TaskStatus.COMPLETED, TaskStatus.CANCELLED, TaskStatus.FAILED
            ):
                self.tracker.pause_task(current_active.task_id)
                logger.info("Paused task %s while switching to %s",
                            current_active.task_id, task_id)

        return self.tracker.set_active_task(task_id)

    def get_next_actionable_task(self) -> Optional[TaskState]:
        """Get the highest-priority task that is ready to execute.

        Scans all active tasks for one that is READY_TO_EXECUTE.
        Returns the one with highest priority (lowest priority number).

        Returns:
            TaskState that is ready, or None.
        """
        active = self.tracker.get_active_tasks()
        ready = [t for t in active if t.status == TaskStatus.READY_TO_EXECUTE]
        if not ready:
            return None

        # Sort by intent priority, then by creation time (oldest first)
        ready.sort(key=lambda t: (_INTENT_PRIORITY.get(t.intent, 99), t.created_at))
        return ready[0]

    def handle_interruption(self, current_message: str,
                            new_intent: str) -> tuple[Optional[TaskState], Optional[TaskState]]:
        """Handle an interruption where the user switches to a new task.

        Args:
            current_message: The user's message.
            new_intent: The newly detected intent.

        Returns:
            Tuple of (paused_task, new_task).
            paused_task is the task that was interrupted (or None).
            new_task is the newly created task for the interruption (or None).
        """
        active_task = self.tracker.get_active_task()

        # If there's an active task that's in-progress, pause it
        paused_task = None
        if active_task and active_task.is_active and active_task.status not in (
            TaskStatus.COMPLETED, TaskStatus.CANCELLED, TaskStatus.FAILED
        ):
            self.tracker.pause_task(active_task.task_id)
            paused_task = active_task
            logger.info("Interruption: paused task %s for new intent '%s'",
                        active_task.task_id, new_intent)

        return paused_task, None

    def handle_resume(self, message: str) -> Optional[TaskState]:
        """Handle a resume request from the user.

        Args:
            message: The user's message (checked for resume keywords).

        Returns:
            The resumed TaskState, or None if no resume occurred.
        """
        task = self.tracker.find_task_for_resume(message)
        if task:
            self.tracker.resume_task(task.task_id)
            logger.info("Resumed task %s (intent=%s)", task.task_id, task.intent)
            return task
        return None

    def cancel_current_task(self) -> Optional[TaskState]:
        """Cancel the currently active task.

        Returns:
            The cancelled task, or None if no active task.
        """
        active = self.tracker.get_active_task()
        if active and active.is_active:
            self.tracker.mark_cancelled(active.task_id)
            # Switch to the next paused task if any
            paused = self.tracker.get_paused_tasks()
            if paused:
                self.tracker.resume_task(paused[-1].task_id)
            return active
        return None

    def complete_and_continue(self, task_id: str,
                              completion_status: str = "success") -> Optional[TaskState]:
        """Complete a task and resume the next paused task if any.

        Args:
            task_id: Task to mark as completed.
            completion_status: Status string (default "success").

        Returns:
            The next task that was resumed, or None.
        """
        self.tracker.mark_completed(task_id, completion_status)

        # Check if this task has linked interrupted tasks or parent
        task = self.tracker.get_task(task_id)
        next_task = None
        if task:
            # Try to resume the parent task (the one that was interrupted)
            if task.parent_task_id:
                parent = self.tracker.get_task(task.parent_task_id)
                if parent and parent.status == TaskStatus.PAUSED:
                    self.tracker.resume_task(parent.task_id)
                    next_task = parent

        if not next_task:
            # Resume any other paused task
            paused = self.tracker.get_paused_tasks()
            if paused:
                self.tracker.resume_task(paused[-1].task_id)
                next_task = paused[-1]

        return next_task

    def pause_all_active(self) -> int:
        """Pause all active (non-terminal) tasks.

        Returns:
            Number of tasks paused.
        """
        count = 0
        active = self.tracker.get_active_tasks()
        for task in active:
            if task.status not in (TaskStatus.PAUSED, TaskStatus.COMPLETED,
                                    TaskStatus.CANCELLED, TaskStatus.FAILED):
                self.tracker.pause_task(task.task_id)
                count += 1
        return count

    def resume_most_recent_paused(self) -> Optional[TaskState]:
        """Resume the most recently paused task.

        Returns:
            The resumed task, or None.
        """
        paused = self.tracker.get_paused_tasks()
        if paused:
            task = paused[-1]
            self.tracker.resume_task(task.task_id)
            return task
        return None

    def get_active_count(self) -> int:
        """Get the number of currently active tasks."""
        return len(self.tracker.get_active_tasks())

    def get_summary(self) -> dict:
        """Get a human-readable summary of all tasks."""
        stats = self.tracker.get_stats()
        active_task = self.tracker.get_active_task()
        return {
            "stats": stats,
            "current_task": active_task.to_dict() if active_task else None,
            "paused_tasks": [
                {
                    "task_id": t.task_id,
                    "intent": t.intent,
                    "missing_slots": t.missing_slots,
                    "waiting_for": t.waiting_for,
                }
                for t in self.tracker.get_paused_tasks()
            ],
        }
