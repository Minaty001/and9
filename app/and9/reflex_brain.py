"""
AND9 — Reflex Brain: Instant Execution Module.

The Reflex Brain handles all deterministic, no-LLM-required commands.
It targets <100ms end-to-end execution for the full set of 15+ reflex
intents including app launches, device controls, calls, messages,
alarms, timers, and media playback.

Processing flow for each query:
  1. Normalize (Hindi → English)
  2. Detect intent via priority router
  3. Dispatch to the appropriate handler based on IntentType
  4. Return a BrainResult with response text, action, and payload

Each handler is a focused function that extracts parameters from the
normalized query and produces the appropriate Android Intent payload.
"""
import logging
import time
from typing import Optional

from app.and9.brain_types import BrainType, BrainResult, IntentType
from app.and9.normalizer import (
    normalize,
    extract_potential_app_name,
    extract_search_query,
)
from app.and9.priority_router import (
    detect_intent,
    extract_contact_name,
    extract_time_value,
    extract_reminder_text,
    extract_number,
)
from app.and9.reflex_apps import ReflexAppResolver
from app.and9.reflex_device import (
    handle_flashlight,
    handle_volume,
    handle_wifi,
    handle_bluetooth,
    handle_airplane_mode,
    handle_home,
    handle_camera,
)
from app.and9.reflex_media import handle_youtube_search, handle_youtube_play
from app.and9.reflex_calls import handle_call, handle_message
from app.and9.reflex_alarm import handle_set_alarm, handle_set_timer, handle_set_reminder

logger = logging.getLogger(__name__)


class ReflexBrain:
    """AND9's immediate-response cognitive layer.

    Processes user queries through a deterministic pipeline that
    normalizes input, classifies intent via priority rules, and
    dispatches to the appropriate action handler. No LLM calls
    involved — every path is a hardcoded handler function.

    Attributes:
        app_resolver: ReflexAppResolver instance for app name matching.
    """

    def __init__(self):
        self.app_resolver = ReflexAppResolver()

    def execute(self, query: str, events_sys=None,
                enable_patterns: bool = True) -> BrainResult:
        """Execute a user query through the reflex pipeline.

        Pipeline:
          1. Normalize query (Hindi → English conversion if needed)
          2. Detect intent via priority router
          3. Dispatch to the matching handler
          4. Wrap result in a BrainResult with timing info

        Args:
            query: Raw user input string.
            events_sys: Optional EventSystem for storing reminders
                        persistently.
            enable_patterns: If False, skip subconscious pattern
                             recording (useful for testing).

        Returns:
            BrainResult with response text, action, payload, and
            metadata. On error, returns an error BrainResult with
            success=False.
        """
        start = time.perf_counter()

        try:
            # Step 1: Normalize Hindi/Hinglish to English
            normalized, was_modified = normalize(query)
            logger.debug("Normalized: '%s' → '%s' (modified=%s)",
                         query, normalized, was_modified)

            # Step 2: Classify intent
            intent, brain = detect_intent(normalized)
            if intent is None:
                return BrainResult(
                    response="Kya karu? Mujhe samajh nahi aaya. Zara aur clearly boliye! 🤔",
                    brain=BrainType.REFLEX,
                    execution_time_ms=(time.perf_counter() - start) * 1000,
                )

            # Step 3: Dispatch to handler
            result = self._dispatch(intent, normalized, events_sys, start)
            return result

        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            logger.error("Reflex error: %s", e, exc_info=True)
            return BrainResult(
                response=f"Mujhe error aa gaya: {str(e)}. Phir se try karo! 😅",
                action="ERROR",
                brain=BrainType.REFLEX,
                execution_time_ms=elapsed,
                success=False,
            )

    def _dispatch(self, intent: IntentType, normalized: str,
                  events_sys=None, start: float = 0) -> BrainResult:
        """Route a classified intent to the appropriate handler.

        Args:
            intent: The detected IntentType.
            normalized: The normalized user query.
            events_sys: Optional EventSystem for reminder storage.
            start: Time.perf_counter() value for timing calculation.

        Returns:
            BrainResult from the matched handler.
        """
        elapsed_ms = (time.perf_counter() - start) * 1000

        # ── Emergency ────────────────────────────────────────────
        if intent == IntentType.EMERGENCY:
            return BrainResult(
                response="🚨 EMERGENCY! Main help bhej raha hoon! Call kar raha hoon emergency services!",
                action="EMERGENCY",
                payload={"type": "emergency", "number": "112"},
                brain=BrainType.REFLEX,
                intent=intent,
                execution_time_ms=elapsed_ms,
            )

        # ── Call ─────────────────────────────────────────────────
        if intent == IntentType.CALL:
            result = handle_call(normalized)
            return BrainResult(
                response=result["response"],
                action=result["action"],
                payload=result["payload"],
                brain=BrainType.REFLEX,
                intent=intent,
                execution_time_ms=(time.perf_counter() - start) * 1000,
            )

        # ── Message ──────────────────────────────────────────────
        if intent == IntentType.MESSAGE:
            result = handle_message(normalized)
            return BrainResult(
                response=result["response"],
                action=result["action"],
                payload=result["payload"],
                brain=BrainType.REFLEX,
                intent=intent,
                execution_time_ms=(time.perf_counter() - start) * 1000,
            )

        # ── Camera ───────────────────────────────────────────────
        if intent == IntentType.CAMERA:
            result = handle_camera()
            return BrainResult(
                response=result["response"],
                action=result["action"],
                payload=result["payload"],
                brain=BrainType.REFLEX,
                intent=intent,
                execution_time_ms=(time.perf_counter() - start) * 1000,
            )

        # ── Flashlight ───────────────────────────────────────────
        if intent == IntentType.FLASHLIGHT:
            result = handle_flashlight(normalized)
            return BrainResult(
                response=result["response"],
                action=result["action"],
                payload=result["payload"],
                brain=BrainType.REFLEX,
                intent=intent,
                execution_time_ms=(time.perf_counter() - start) * 1000,
            )

        # ── Bluetooth ────────────────────────────────────────────
        if intent == IntentType.BLUETOOTH:
            result = handle_bluetooth(normalized)
            return BrainResult(
                response=result["response"],
                action=result["action"],
                payload=result["payload"],
                brain=BrainType.REFLEX,
                intent=intent,
                execution_time_ms=(time.perf_counter() - start) * 1000,
            )

        # ── WiFi ─────────────────────────────────────────────────
        if intent == IntentType.WIFI:
            result = handle_wifi(normalized)
            return BrainResult(
                response=result["response"],
                action=result["action"],
                payload=result["payload"],
                brain=BrainType.REFLEX,
                intent=intent,
                execution_time_ms=(time.perf_counter() - start) * 1000,
            )

        # ── Airplane Mode ────────────────────────────────────────
        if intent == IntentType.AIRPLANE_MODE:
            result = handle_airplane_mode(normalized)
            return BrainResult(
                response=result["response"],
                action=result["action"],
                payload=result["payload"],
                brain=BrainType.REFLEX,
                intent=intent,
                execution_time_ms=(time.perf_counter() - start) * 1000,
            )

        # ── Volume ───────────────────────────────────────────────
        if intent == IntentType.VOLUME:
            result = handle_volume(normalized)
            return BrainResult(
                response=result["response"],
                action=result["action"],
                payload=result["payload"],
                brain=BrainType.REFLEX,
                intent=intent,
                execution_time_ms=(time.perf_counter() - start) * 1000,
            )

        # ── Open App ─────────────────────────────────────────────
        if intent == IntentType.OPEN_APP:
            app_name = extract_potential_app_name(normalized)
            resolved = self.app_resolver.resolve(app_name) if app_name else None

            if resolved:
                return BrainResult(
                    response=f"{app_name.title()} khol raha hoon... 📱",
                    action="LAUNCH_APP",
                    payload=resolved,
                    brain=BrainType.REFLEX,
                    intent=intent,
                    parameters={"app_name": app_name},
                    execution_time_ms=(time.perf_counter() - start) * 1000,
                    metadata={"app_name": app_name},
                )
            else:
                fuzzy = self.app_resolver.fuzzy_match(normalized)
                if fuzzy:
                    resolved = self.app_resolver.resolve(fuzzy)
                    return BrainResult(
                        response=f"Kya aap '{fuzzy.title()}' kholna chahte ho? 🎯",
                        action="LAUNCH_APP",
                        payload=resolved,
                        brain=BrainType.REFLEX,
                        intent=intent,
                        parameters={"app_name": fuzzy},
                        execution_time_ms=(time.perf_counter() - start) * 1000,
                        metadata={"app_name": fuzzy, "fuzzy": True},
                    )
                return BrainResult(
                    response=f"App nahi mila '{app_name}'. Kripya sahi naam boliye! 😕",
                    action="UNKNOWN_APP",
                    brain=BrainType.REFLEX,
                    intent=intent,
                    parameters={"app_name": app_name or normalized},
                    execution_time_ms=(time.perf_counter() - start) * 1000,
                )

        # ── YouTube ──────────────────────────────────────────────
        if intent == IntentType.YOUTUBE:
            search_term = extract_search_query(normalized)
            if search_term and search_term != "youtube":
                result = handle_youtube_search(search_term)
            else:
                result = handle_youtube_search("")
            return BrainResult(
                response=result.get("response", "YouTube search karta hoon... 🎬"),
                action=result.get("action"),
                payload=result.get("payload"),
                brain=BrainType.REFLEX,
                intent=intent,
                execution_time_ms=(time.perf_counter() - start) * 1000,
                metadata={"search_term": search_term},
            )

        # ── Music ────────────────────────────────────────────────
        if intent == IntentType.MUSIC:
            search_term = extract_search_query(normalized)
            result = handle_youtube_play(normalized)
            return BrainResult(
                response=result.get("response", "Music play karta hoon... 🎵"),
                action=result.get("action"),
                payload=result.get("payload"),
                brain=BrainType.REFLEX,
                intent=intent,
                execution_time_ms=(time.perf_counter() - start) * 1000,
                metadata={"query": normalized},
            )

        # ── Alarm ────────────────────────────────────────────────
        if intent == IntentType.SET_ALARM:
            result = handle_set_alarm(normalized)
            return BrainResult(
                response=result["response"],
                action=result["action"],
                payload=result["payload"],
                brain=BrainType.REFLEX,
                intent=intent,
                parameters={"time": normalized},
                execution_time_ms=(time.perf_counter() - start) * 1000,
            )

        # ── Timer ────────────────────────────────────────────────
        if intent == IntentType.SET_TIMER:
            result = handle_set_timer(normalized)
            return BrainResult(
                response=result["response"],
                action=result["action"],
                payload=result["payload"],
                brain=BrainType.REFLEX,
                intent=intent,
                parameters={"duration": normalized},
                execution_time_ms=(time.perf_counter() - start) * 1000,
            )

        # ── Reminder ─────────────────────────────────────────────
        if intent == IntentType.SET_REMINDER:
            result = handle_set_reminder(normalized, events_sys)
            return BrainResult(
                response=result["response"],
                action=result["action"],
                payload=result["payload"],
                brain=BrainType.REFLEX,
                intent=intent,
                execution_time_ms=(time.perf_counter() - start) * 1000,
            )

        # ── Home ─────────────────────────────────────────────────
        if intent == IntentType.HOME:
            result = handle_home()
            return BrainResult(
                response=result["response"],
                action=result["action"],
                payload=result["payload"],
                brain=BrainType.REFLEX,
                intent=intent,
                execution_time_ms=(time.perf_counter() - start) * 1000,
            )

        # ── Fallback ─────────────────────────────────────────────
        return BrainResult(
            response="Main and9 hoon. Kya kar sakta hoon aapke liye? 😊",
            brain=BrainType.REFLEX,
            intent=intent,
            execution_time_ms=(time.perf_counter() - start) * 1000,
        )
