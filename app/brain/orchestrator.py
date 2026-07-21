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

from app.brain.brain_types import BrainResult, BrainType, IntentType
from app.router.normalizer import QueryNormalizer
from app.router.intent_router import detect_intent
from app.router.intent_validator import validate_intent
from app.android.executor import execute as execute_action
from app.core.logger import get_logger, is_debug_enabled
from app.core.intent_trace import TraceContext
from app.brain.subconscious_brain import SubconsciousBrain

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
        self.events_sys = events_sys
        self.query_logger = get_logger()
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

        if not query or not query.strip():
            result = BrainResult(
                response="Kya karu? Mujhe samajh nahi aaya. Kuch type karo! 😊",
                brain=BrainType.REFLEX,
            )
            self._log_result(query, "", "", {}, result)
            return result.to_dict()

        with TraceContext(query) as trace:
            try:
                # Step 1: Normalize
                normalized, was_modified = self.normalizer.normalize(query)
                trace.set_normalized(normalized)
                logger.debug("Normalized: '%s' → '%s' (modified=%s)",
                             query, normalized, was_modified)

                # Step 2: Detect intent
                intent_name, action_type, params = detect_intent(normalized)
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
                    return result.to_dict()

                logger.debug("Intent: %s | Action: %s | Params: %s",
                             intent_name, action_type, params)

                # Step 3: Execute action
                result = self._execute(intent_name, action_type, params, start)

                # Step 4: Record in subconscious
                if result.success:
                    self.subconscious.record_action(result, query)

                self._log_result(query, normalized, intent_name, params, result)
                trace.set_result("success" if result.success else "failure")
                return result.to_dict()

            except Exception as e:
                elapsed = (time.perf_counter() - start) * 1000
                logger.error("AND9 pipeline error: %s", e, exc_info=True)
                trace.set_result("failure", str(e))
                
                # Priority 9: Run Self-Healing Diagnostics
                from app.core.diagnostics import run_diagnostics
                # Best effort to grab intent variables, fallback to empty string if unbound
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
                return result.to_dict()

    def _execute(self, intent_name: str, action_type: Optional[str],
                 params: dict, start: float) -> BrainResult:
        """Execute an action based on detected intent.

        This is where Chrome fallback is prevented — device actions
        never go to Chrome. Only explicit SEARCH intent goes to browser.
        """
        elapsed_ms = (time.perf_counter() - start) * 1000

        # ── Chat / Goal / Automation (natural language) → conscious brain ──
        # Goal and automation come through with intent_name="goal"/"automation"
        # and action_type="chat". They need LLM processing, not device execution.
        if intent_name in ("chat", "goal", "automation"):
            return self._handle_chat(params, start)

        # ── Search → browser/Chrome ────────────────────────────────
        if intent_name == "search":
            return self._handle_search(params, start)

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
        from app.brain.conscious_brain import ConsciousBrain
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
            "goal": IntentType.GOAL,
            "automation": IntentType.AUTOMATION,
            "search": IntentType.SEARCH,
            "chat": IntentType.CHAT,
        }
        return mapping.get(name)

    def _log_result(self, query: str, normalized: str,
                    intent: str, params: dict, result: BrainResult):
        """Log the query result to the QueryLogger."""
        self.query_logger.log(
            raw_query=query,
            normalized_query=normalized,
            intent=intent or result.intent.value if result.intent else "",
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
