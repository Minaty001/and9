"""
AND9 — Self-Reflection Engine.

Evaluates execution outcomes, latency, and success rates, persisting reflections
to Supabase and local cache backup files.
"""

import logging
import time
import os
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

_MAX_LOG_SIZE = 1000

class SelfReflection:
    """Post-task reflection engine with dual-persistence (Supabase + local fallback)."""

    def __init__(self):
        """Initialise the self-reflection engine with dual-persistence (Supabase + local file)."""
        self._reflection_log: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self._bg_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="reflection")
        self._supabase_client = None
        self._local_file = "/tmp/.jarvis_data/reflection_log.json"

        # Initialize Supabase client if configured
        try:
            from app.core.config import SUPABASE_KEY
            if SUPABASE_KEY:
                from app.memory.episodic.memory import _get_client
                self._supabase_client = _get_client()
        except Exception as e:
            logger.warning(f"SelfReflection Supabase init skipped: {e}")

        self._load_reflections()

    def _load_reflections(self):
        """Loads historical reflections from Supabase or local cache backup."""
        # 1. Try Supabase
        if self._supabase_client:
            try:
                res = self._supabase_client.table("reflection_log").select("*").order("timestamp", desc=True).limit(_MAX_LOG_SIZE).execute()
                if res.data:
                    with self._lock:
                        self._reflection_log = list(reversed(res.data))
                    logger.info(f"Loaded {len(self._reflection_log)} reflections from Supabase.")
                    return
            except Exception as e:
                err_msg = str(e)
                if "PGRST205" in err_msg or "reflection_log" in err_msg:
                    logger.info("Supabase 'reflection_log' table not found in schema cache. Using local file fallback.")
                else:
                    logger.warning(f"Supabase reflection load failed, trying local file fallback: {e}")

        # 2. Try Local File
        if os.path.exists(self._local_file):
            try:
                with open(self._local_file, "r") as f:
                    data = json.load(f)
                    with self._lock:
                        self._reflection_log = data[-_MAX_LOG_SIZE:]
                logger.info(f"Loaded {len(self._reflection_log)} reflections from local file.")
            except Exception as e:
                logger.warning(f"Local reflection load failed: {e}")

    def reflect(self, ctx) -> Dict[str, Any]:
        """Evaluate action execution and generate reflection.

        Saves reflection record with dual persistence.
        """
        # Ensure we can read properties from either CognitiveContext or normal dict
        raw_input = getattr(ctx, "raw_input", "")
        detected_intent = getattr(ctx, "detected_intent", "")
        detected_action = getattr(ctx, "detected_action", "")
        processing_level = getattr(ctx, "processing_level", None)
        brain_used = processing_level.value if processing_level else "reflex"
        execution_time_ms = getattr(ctx, "execution_time_ms", 0.0)
        success = getattr(ctx, "success", True)
        confidence = getattr(ctx, "confidence", 1.0)

        reflection = {
            "timestamp": time.time(),
            "input": raw_input[:200],
            "intent": detected_intent,
            "action": detected_action,
            "brain_used": brain_used,
            "execution_time_ms": execution_time_ms,
            "success": success,
            "confidence": confidence,
            "improvement_suggestion": "",
            "learning_opportunity": "",
        }

        # Generate suggestions
        if not success:
            reflection["improvement_suggestion"] = self._analyze_failure(ctx)
        elif execution_time_ms > 2000 and brain_used == "reflex":
            reflection["improvement_suggestion"] = (
                "Reflex action took too long. Consider optimizing pattern matching."
            )
        elif brain_used == "reasoning":
            reflection["learning_opportunity"] = (
                "This could be converted to a reflex action if it repeats."
            )

        with self._lock:
            self._reflection_log.append(reflection)
            if len(self._reflection_log) > _MAX_LOG_SIZE:
                self._reflection_log = self._reflection_log[-int(_MAX_LOG_SIZE/2):]
            
            # Save reflections asynchronously to not block execution
            self._bg_pool.submit(self._save_reflection, reflection)

        return reflection

    def _save_reflection(self, reflection: Dict[str, Any]):
        """Persist a reflection record to Supabase and a local JSON backup file.

        Args:
            reflection: The reflection dict to save.
        """
        # 1. Try Supabase write
        if self._supabase_client:
            try:
                # Table might not exist, ignore if it errors
                self._supabase_client.table("reflection_log").insert(reflection).execute()
            except Exception as e:
                logger.debug(f"Supabase reflection insert failed: {e}")

        # 2. Local File backup
        try:
            os.makedirs(os.path.dirname(self._local_file), exist_ok=True)
            
            # Read current local list to merge/sync
            local_list = []
            if os.path.exists(self._local_file):
                try:
                    with open(self._local_file, "r") as f:
                        local_list = json.load(f)
                except Exception as e:
                    logger.debug("Failed to read local reflections file: %s", e)
            
            local_list.append(reflection)
            if len(local_list) > _MAX_LOG_SIZE:
                local_list = local_list[-_MAX_LOG_SIZE:]
                
            with open(self._local_file, "w") as f:
                json.dump(local_list, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to backup reflection locally: {e}")

    def _analyze_failure(self, ctx) -> str:
        """Generate a targeted improvement suggestion for a failed execution.

        Analyzes the context to determine the likely cause of failure.

        Args:
            ctx: The context object with detected_intent and execution_time_ms attributes.

        Returns:
            A human-readable improvement suggestion string.
        """
        detected_intent = getattr(ctx, "detected_intent", "")
        execution_time_ms = getattr(ctx, "execution_time_ms", 0.0)
        
        if not detected_intent:
            return "Intent not recognized. Consider adding keywords or patterns."
        if execution_time_ms > 5000:
            return "Slow response. Check LLM latency or network connectivity."
        return "Generic failure. Consider adding fallback behavior."

    def get_daily_reflection(self) -> Dict[str, Any]:
        """Generate end-of-day reflection summary."""
        today = datetime.now().strftime("%Y-%m-%d")

        with self._lock:
            today_log = [
                r for r in self._reflection_log
                if datetime.fromtimestamp(r["timestamp"]).strftime("%Y-%m-%d") == today
            ]

        if not today_log:
            return {"summary": "No activity recorded today.", "suggestions": []}

        total = len(today_log)
        successes = sum(1 for r in today_log if r.get("success", True))
        failures = total - successes
        avg_time = sum(r.get("execution_time_ms", 0.0) for r in today_log) / total if total > 0 else 0
        reflex_count = sum(1 for r in today_log if r.get("brain_used") == "reflex")
        reasoning_count = sum(1 for r in today_log if r.get("brain_used") == "reasoning")

        suggestions = [
            r["improvement_suggestion"] for r in today_log
            if r.get("improvement_suggestion")
        ]

        return {
            "summary": (
                f"Today: {total} actions ({successes} success, {failures} fail). "
                f"Reflex: {reflex_count}, Reasoning: {reasoning_count}. "
                f"Avg response: {avg_time:.0f}ms."
            ),
            "total_actions": total,
            "success_rate": successes / total if total > 0 else 1.0,
            "avg_response_time_ms": round(avg_time, 1),
            "reflex_vs_reasoning": {"reflex": reflex_count, "reasoning": reasoning_count},
            "suggestions": list(set(suggestions))[:5],
            "improvements": self._generate_improvements(today_log),
        }

    def _generate_improvements(self, today_log: list) -> list:
        """Generate actionable improvement suggestions from today's reflection log.

        Identifies reasoning actions that could be converted to reflexes and
        repeated failures that need attention.

        Args:
            today_log: List of reflection dicts from today.

        Returns:
            Up to 5 improvement suggestion strings.
        """
        improvements = []

        # Check for patterns that could be converted to reflexes
        action_counts = {}
        for r in today_log:
            if r.get("brain_used") == "reasoning":
                intent = r.get("intent") or "unknown"
                action_counts[intent] = action_counts.get(intent, 0) + 1

        for intent, count in action_counts.items():
            if count >= 3:
                improvements.append(
                    f"'{intent}' was handled by reasoning {count} times today. "
                    "Consider adding as a reflex action."
                )

        # Check for repeated failures
        failure_intents = {}
        for r in today_log:
            if not r.get("success", True):
                intent = r.get("intent") or "unknown"
                failure_intents[intent] = failure_intents.get(intent, 0) + 1

        for intent, count in failure_intents.items():
            if count >= 2:
                improvements.append(
                    f"'{intent}' failed {count} times. Check the handler implementation."
                )

        return improvements[:5]

    def get_stats(self) -> Dict[str, Any]:
        """Return summary statistics about stored reflections.

        Returns:
            Dict with total_reflections count and recent_reflections (last hour).
        """
        with self._lock:
            return {
                "total_reflections": len(self._reflection_log),
                "recent_reflections": len([r for r in self._reflection_log if r["timestamp"] > time.time() - 3600]),
            }
