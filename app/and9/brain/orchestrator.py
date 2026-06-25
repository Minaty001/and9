"""
AND9 — Brain Orchestrator (Phase 15 Refactor).

The main processing pipeline for all AND9 queries.

Pipeline:
    1. Normalize via router/normalizer.py
    2. Detect intent via router/intent_router.py
    3. Execute action via android/android_executor.py
    4. Trace log via core/intent_trace.py (Phase 15)
    5. Return BrainResult-compatible dict

Cognitive Architecture:
    Reflex Brain  → instant device actions (<100ms)
    Subconscious  → pattern learning
    Conscious Brain → LLM reasoning (last resort)

Design rules:
    - Device actions ALWAYS beat search actions
    - SEARCH is the LAST intent checked (priority 17)
    - Chrome is NEVER used as fallback for device commands
    - All actions pass through the Android Executor
    - Every request is traced through intent_trace
"""
import logging
import time
from typing import Any, Dict, Optional
from urllib.parse import quote_plus

from app.and9.brain_types import BrainResult, BrainType, IntentType
from app.and9.router.normalizer import QueryNormalizer
from app.and9.router.intent_router import detect_intent_with_confidence
from app.and9.router.intent_validator import validate_intent
from app.and9.android.android_executor import execute as execute_action
from app.and9.core.logger import get_logger, is_debug_enabled
from app.and9.core.intent_trace import TraceContext, log_trace
from app.and9.subconscious_brain import SubconsciousBrain
from app.and9.utils.timezone_utils import format_city_time_response
from app.and9.core.pipeline_status import status_manager, PipelineStage

logger = logging.getLogger(__name__)


class Orchestrator:
    """Main AND9 processing pipeline.

    Processes user queries through the full pipeline:
    Normalize → Detect Intent → Execute Action → Log → Return

    Attributes:
        normalizer: QueryNormalizer instance.
        subconscious: SubconsciousBrain for pattern learning.
        events_sys: Optional EventSystem for reminder persistence.
    """

    def __init__(self, events_sys=None, enable_patterns: bool = True):
        self.normalizer = QueryNormalizer()
        self.subconscious = SubconsciousBrain(enable_learning=enable_patterns)
        from app.and9.habit_brain import HabitBrain
        self.habit_brain = HabitBrain(self.subconscious)
        self.events_sys = events_sys
        self.query_logger = get_logger()
        self.enable_patterns = enable_patterns
        
        try:
            from app.core.learning_system import LearningSystem
            self.learning_system = LearningSystem(enable_all=True)
        except Exception as e:
            logger.warning(f"AND9 Orchestrator LearningSystem init skipped: {e}")
            self.learning_system = None

        try:
            from app.core.memory_consolidation import MemoryConsolidation
            self.memory_consolidation = MemoryConsolidation()
            self.memory_consolidation.start()
        except Exception as e:
            logger.warning(f"AND9 Orchestrator MemoryConsolidation init skipped: {e}")
            self.memory_consolidation = None
            
        logger.info("AND9 Orchestrator initialized (patterns=%s, debug=%s)",
                     enable_patterns, is_debug_enabled())

    def process(self, query: str) -> Dict[str, Any]:
        """Process a user query through the full AND9 pipeline.

        Pipeline:
            1. Normalize (Hindi → English)
            2. Detect intent (router)
            3. Execute action (android_executor)
            4. Trace log (intent_trace)
            5. Return result dict

        Args:
            query: Raw user input string.

        Returns:
            Dict with response, action, payload, brain, intent,
            parameters, time_ms, success, metadata.
        """
        start = time.perf_counter()
        logger.info("AND9 processing: '%s'", query)
        
        status_manager.reset()

        if not query or not query.strip():
            result = BrainResult(
                response="Kya karu? Mujhe samajh nahi aaya. Kuch type karo! 😊",
                brain=BrainType.REFLEX,
            )
            self._log_result(query, "", "", {}, result)
            status_manager.set_stage(PipelineStage.COMPLETED, "Empty query handled")
            return result.to_dict()

        with TraceContext(query) as trace:
            try:
                # Step 1: Normalize
                normalized, was_modified = self.normalizer.normalize(query)
                trace.set_normalized(normalized)
                logger.debug("Normalized: '%s' → '%s' (modified=%s)",
                             query, normalized, was_modified)

                # Step 2: Detect intent with confidence
                status_manager.set_stage(PipelineStage.UNDERSTANDING, "Classifying intent & extracting entities")
                intent_name, action_type, params, confidence = detect_intent_with_confidence(normalized)
                trace.set_intent(intent_name or "", params)
                trace.set_action(action_type or "")

                if not intent_name:
                    result = BrainResult(
                        response="Kya karu? Mujhe samajh nahi aaya. Zara aur clearly boliye! 🤔",
                        brain=BrainType.REFLEX,
                        execution_time_ms=(time.perf_counter() - start) * 1000,
                    )
                    self._log_result(query, normalized, "", params, result)
                    trace.set_result("failure", "no_intent_detected")
                    status_manager.set_stage(PipelineStage.COMPLETED, "No intent classified")
                    return result.to_dict()

                # Priority 7: Validate Intent Parameters
                is_valid, validation_msg = validate_intent(intent_name, params)
                if not is_valid:
                    result = BrainResult(
                        response=validation_msg,
                        brain=BrainType.REFLEX,
                        execution_time_ms=(time.perf_counter() - start) * 1000,
                        success=False
                    )
                    self._log_result(query, normalized, intent_name, params, result)
                    trace.set_result("failure", "validation_failed")
                    status_manager.set_stage(PipelineStage.COMPLETED, "Validation failed")
                    return result.to_dict()

                logger.debug("Intent: %s | Action: %s | Params: %s | Confidence: %.2f",
                             intent_name, action_type, params, confidence)

                # Tiered execution / Action Verification
                status_manager.set_stage(PipelineStage.PLANNING, "Evaluating confidence & verification rules")
                from app.and9.actions.action_verifier import verify_action
                
                # Check if it is a simple greeting and we can suggest a habit
                if intent_name == "chat" and normalized in ("hello", "jarvis", "assistant", "hey jarvis", "hi", "hey"):
                    suggestion = self.habit_brain.get_routine_suggestion()
                    if suggestion:
                        confirm_prompt = suggestion["suggestion"]
                        action_summary = f"Suggest {suggestion['predicted_action']}"
                        
                        result = BrainResult(
                            response=confirm_prompt,
                            action="CONFIRM_ACTION",
                            payload={
                                "original_action": suggestion["predicted_action"],
                                "original_intent": suggestion["predicted_action"],
                                "original_params": {"app_name": suggestion["predicted_action"]} if "app" in suggestion["predicted_action"] else {},
                                "prompt": confirm_prompt,
                                "summary": action_summary
                            },
                            brain=BrainType.SUBCONSCIOUS,
                            intent=IntentType.CHAT,
                            execution_time_ms=(time.perf_counter() - start) * 1000,
                            success=True,
                            metadata={"confidence": suggestion["confidence"], "is_habit_suggestion": True}
                        )
                        self._log_result(query, normalized, intent_name, params, result)
                        trace.set_result("success", "habit_suggested")
                        status_manager.set_stage(PipelineStage.COMPLETED, "Habit routine suggestion sent")
                        return result.to_dict()

                # Check if it requires confirmation (either due to low confidence or dangerous action status)
                needs_confirm, confirm_prompt, action_summary = verify_action(action_type or intent_name, params)
                
                # Tier 3: Low confidence (< 0.70)
                if confidence < 0.70:
                    result = BrainResult(
                        response="Mujhe samajh nahi aaya. Kya aap phir se bol sakte hain? 🤔",
                        action="CLARIFICATION_REQUIRED",
                        brain=BrainType.REFLEX,
                        execution_time_ms=(time.perf_counter() - start) * 1000,
                        success=False,
                        metadata={"confidence": confidence}
                    )
                    self._log_result(query, normalized, intent_name, params, result)
                    trace.set_result("failure", "low_confidence")
                    status_manager.set_stage(PipelineStage.COMPLETED, "Clarification requested due to low confidence")
                    return result.to_dict()
                
                # Tier 2: Medium confidence (0.70 <= confidence < 0.95) AND dangerous action
                elif confidence < 0.95 and needs_confirm:
                    if not confirm_prompt:
                        confirm_prompt = f"Kya aap chahte hain ki main {intent_name} action execute karoon?"
                        action_summary = f"Execute {intent_name}"
                        
                    result = BrainResult(
                        response=confirm_prompt,
                        action="CONFIRM_ACTION",
                        payload={
                            "original_action": action_type,
                            "original_intent": intent_name,
                            "original_params": params,
                            "prompt": confirm_prompt,
                            "summary": action_summary
                        },
                        brain=BrainType.REFLEX,
                        intent=self._intent_from_name(intent_name),
                        parameters=params,
                        execution_time_ms=(time.perf_counter() - start) * 1000,
                        success=True,
                        metadata={"confidence": confidence, "needs_confirmation": True}
                    )
                    self._log_result(query, normalized, intent_name, params, result)
                    trace.set_result("success", "confirmation_required")
                    status_manager.set_stage(PipelineStage.COMPLETED, "Confirmation requested from user")
                    return result.to_dict()

                # Tier 1: High confidence (>= 0.95) or not dangerous (non-confirmable)
                # Step 3: Execute action
                status_manager.set_stage(PipelineStage.EXECUTING, f"Executing: {intent_name}")
                result = self._execute(intent_name, action_type, params, start)

                # Step 4: Record in subconscious
                if result.success:
                    self.subconscious.record_action(result, query)
                    
                    if self.enable_patterns:
                        def run_bg_hooks():
                            try:
                                if self.learning_system:
                                    from app.and9.brain.cognitive_engine import CognitiveContext
                                    ctx = CognitiveContext(
                                        raw_input=query,
                                        detected_intent=intent_name,
                                        detected_action=action_type or "",
                                        parameters=params,
                                        success=result.success,
                                        execution_time_ms=result.execution_time_ms
                                    )
                                    self.learning_system.observe(ctx)
                                
                                if self.memory_consolidation:
                                    self.memory_consolidation.add_to_working(
                                        content=query,
                                        importance=0.4,
                                        topics=[intent_name],
                                        entities=params,
                                        source="user"
                                    )
                            except Exception as ex:
                                logger.debug(f"AND9 background hooks skipped: {ex}")
                                
                        import threading
                        threading.Thread(target=run_bg_hooks, daemon=True).start()

                self._log_result(query, normalized, intent_name, params, result)
                trace.set_result("success" if result.success else "failure")
                
                if result.success:
                    status_manager.set_stage(PipelineStage.COMPLETED, "Execution complete")
                else:
                    status_manager.set_stage(PipelineStage.DEGRADED, f"Execution failed: {result.response}")
                    
                return result.to_dict()

            except Exception as e:
                elapsed = (time.perf_counter() - start) * 1000
                logger.error("AND9 pipeline error: %s", e, exc_info=True)
                trace.set_result("failure", str(e))
                
                status_manager.set_stage(PipelineStage.ERROR_RECOVERY, "Executing diagnostics")
                
                # Priority 9: Run Self-Healing Diagnostics
                from app.and9.core.diagnostics import run_diagnostics
                i_name = locals().get("intent_name", "")
                a_type = locals().get("action_type", "")
                p_dict = locals().get("params", {})
                diag_report = run_diagnostics(e, i_name, a_type, p_dict)
                
                result = BrainResult(
                    response=f"Oops! Kuch gadbad ho gayi: {str(e)}. Phir se try karo! 😅\n\n[Diagnostic: {diag_report['recommendation']}]",
                    action="ERROR",
                    brain=BrainType.REFLEX,
                    execution_time_ms=elapsed,
                    success=False,
                    metadata={"diagnostics": diag_report}
                )
                status_manager.set_stage(PipelineStage.DEGRADED, "Pipeline recovered in degraded state")
                return result.to_dict()

    def _execute(self, intent_name: str, action_type: Optional[str],
                 params: dict, start: float) -> BrainResult:
        """Execute an action based on detected intent.

        This is where Chrome fallback is prevented — device actions
        never go to Chrome. Only explicit SEARCH intent goes to browser.
        """
        elapsed_ms = (time.perf_counter() - start) * 1000

        # ── Chat (no action needed) → conscious brain ──────────────
        if intent_name == "chat":
            return self._handle_chat(params, start)

        # ── Search → browser/Chrome ────────────────────────────────
        if intent_name == "search":
            return self._handle_search(params, start)

        # ── City Time → timezone-aware response ────────────────────
        if intent_name == "city_time":
            city = params.get("city", "")
            if city:
                response_text = format_city_time_response(city)
            else:
                from datetime import datetime
                response_text = f"Current time is {datetime.now().strftime('%I:%M:%S %p')}"

            return BrainResult(
                response=response_text,
                action="city_time",
                payload=params,
                brain=BrainType.REFLEX,
                intent=IntentType.TIME,
                parameters=params,
                execution_time_ms=(time.perf_counter() - start) * 1000,
            )

        # ── Emergency ──────────────────────────────────────────────
        if intent_name == "emergency":
            return BrainResult(
                response="🚨 EMERGENCY! Main help bhej raha hoon! Call kar raha hoon emergency services!",
                action="emergency",
                payload={"type": "emergency", "number": "112"},
                brain=BrainType.REFLEX,
                intent=IntentType.EMERGENCY,
                execution_time_ms=elapsed_ms,
            )

        # ── All device actions → Android Executor ──────────────────
        # This includes: call, message, open_app, camera, flashlight,
        # youtube, alarm, reminder, timer, wifi, bluetooth, volume,
        # airplane_mode, go_home
        if action_type:
            handler_result = execute_action(
                action_type=action_type,
                params=params,
                events_sys=self.events_sys,
            )
            handler_action = handler_result.get("action")
            action_val = (
                handler_action
                if handler_action in ["ERROR", "CHROME_FIREWALL_BLOCKED", "UNKNOWN_APP"]
                else action_type
            )
            return BrainResult(
                response=handler_result.get("response", "Done! ✅"),
                action=action_val,
                payload=handler_result.get("payload"),
                brain=BrainType.REFLEX,
                intent=self._intent_from_name(intent_name),
                parameters=params,
                execution_time_ms=(time.perf_counter() - start) * 1000,
                metadata=handler_result.get("metadata", {}),
            )

        # ── Fallback (shouldn't happen) ────────────────────────────
        return BrainResult(
            response="Main and9 hoon. Kya kar sakta hoon aapke liye? 😊",
            brain=BrainType.REFLEX,
            execution_time_ms=(time.perf_counter() - start) * 1000,
        )

    def _handle_chat(self, params: dict, start: float) -> BrainResult:
        """Route to Conscious Brain for LLM processing."""
        from app.and9.conscious_brain import ConsciousBrain
        conscious = ConsciousBrain()
        query = params.get("query", "")
        result = conscious.execute(query)
        result.execution_time_ms = (time.perf_counter() - start) * 1000
        return result

    def _handle_search(self, params: dict, start: float) -> BrainResult:
        """Handle web search — Chrome allowed ONLY here (priority 17 = last resort)."""
        query = params.get("query", "")
        search_url = f"https://www.google.com/search?q={quote_plus(query)}"
        return BrainResult(
            response=f"Web pe '{query}' search kar raha hoon 🔍",
            action="search",
            payload={
                "action": "android.intent.action.VIEW",
                "package": "com.android.chrome",
                "component": "com.android.chrome/com.google.android.apps.chrome.Main",
                "data": search_url,
            },
            brain=BrainType.REFLEX,
            intent=IntentType.SEARCH,
            parameters=params,
            execution_time_ms=(time.perf_counter() - start) * 1000,
        )

    def _intent_from_name(self, name: str) -> Optional[IntentType]:
        """Convert intent name string to IntentType enum."""
        mapping = {
            "emergency": IntentType.EMERGENCY,
            "call": IntentType.CALL,
            "message": IntentType.MESSAGE,
            "open_app": IntentType.OPEN_APP,
            "camera": IntentType.CAMERA,
            "flashlight": IntentType.FLASHLIGHT,
            "youtube": IntentType.YOUTUBE,
            "alarm": IntentType.SET_ALARM,
            "reminder": IntentType.SET_REMINDER,
            "timer": IntentType.SET_TIMER,
            "volume": IntentType.VOLUME,
            "wifi": IntentType.WIFI,
            "bluetooth": IntentType.BLUETOOTH,
            "airplane": IntentType.AIRPLANE_MODE,
            "home": IntentType.HOME,
            "search": IntentType.SEARCH,
            "chat": IntentType.CHAT,
        }
        return mapping.get(name)

    def _log_result(self, query: str, normalized: str,
                    intent: str, params: dict, result: BrainResult):
        """Log the query result to the QueryLogger."""
        effective_intent = intent or (result.intent.value if result.intent else "")
        self.query_logger.log(
            raw_query=query,
            normalized_query=normalized,
            intent=effective_intent,
            parameters=params or result.parameters,
            action=result.action or "",
            payload=result.payload,
            brain=result.brain.value,
            execution_time_ms=result.execution_time_ms,
            success=result.success,
        )

    def get_stats(self) -> dict:
        """Get system statistics."""
        return {
            "subconscious": self.subconscious.get_stats(),
            "history": self.subconscious.get_history(limit=10),
            "logs": self.query_logger.get_stats(),
        }
