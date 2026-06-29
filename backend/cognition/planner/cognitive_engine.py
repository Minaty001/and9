"""
╔══════════════════════════════════════════════════════════════╗
║           COGNITIVE ENGINE — Unified Brain Orchestrator      ║
║   Integrates Reflex, Habit, Neural, Memory, Learning         ║
╚══════════════════════════════════════════════════════════════╝

Every input — user command, notification, screen change, environmental
observation — flows through this engine. Processing order:

    1. REFLEX BRAIN     (< 300ms) — Instant actions, no LLM
    2. HABIT BRAIN      (~200ms)  — Pattern matching, habit prediction
    3. NEURAL BRAIN     (< 50ms)  — Dataset-trained TinyNeuralNetwork
    4. MEMORY           (~100ms)  — Record, consolidate, learn
    5. REFLECTION       (async)   — Evaluate, improve, plan

No external API calls — all processing is on-device.
"""

import logging
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Optional, Callable, Tuple
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class ProcessingLevel(Enum):
    """Which cognitive layer processed the input."""
    REFLEX = "reflex"           # Instant, no thought
    HABIT = "habit"             # Pattern-based prediction
    NEURAL = "neural"           # Dataset-trained neural network (<50ms)
    LEARNING = "learning"       # Background learning task
    REFLECTION = "reflection"   # Self-evaluation


@dataclass
class CognitiveContext:
    """Full context passed through the cognitive pipeline.

    Each brain layer can read and modify this context.
    The final result is built from the accumulated context.
    """
    raw_input: str
    normalized_input: str = ""
    detected_intent: str = ""
    detected_action: str = ""
    parameters: dict = field(default_factory=dict)
    confidence: float = 0.0
    processing_level: ProcessingLevel = ProcessingLevel.REFLEX
    response: str = ""
    payload: Any = None
    execution_time_ms: float = 0.0
    success: bool = True
    user_id: str = "default"
    session_id: int = 0
    emotion: str = "neutral"
    topic: str = "general"
    metadata: dict = field(default_factory=dict)
    _start_time: float = field(default_factory=time.perf_counter)

    def elapsed_ms(self) -> float:
        return (time.perf_counter() - self._start_time) * 1000

    def to_dict(self) -> dict:
        return {
            "response": self.response,
            "intent": self.detected_intent,
            "action": self.detected_action,
            "parameters": self.parameters,
            "confidence": self.confidence,
            "brain": self.processing_level.value,
            "time_ms": self.execution_time_ms,
            "success": self.success,
            "emotion": self.emotion,
            "topic": self.topic,
            "payload": self.payload,
            "metadata": self.metadata,
        }


class ReflexProcessor:
    """Brain 1: Instant reflex actions. <300ms target. No LLM. No memory."""

    def __init__(self):
        self._handlers: Dict[str, Callable] = {}
        self._intent_map: Dict[str, str] = {}  # keyword → intent
        self._match_cache: Dict[str, Tuple[Optional[str], float]] = {}  # query → (intent, score)
        self._load_defaults()

    def _load_defaults(self):
        """Register default reflex patterns - app launches, device controls."""
        # App launch patterns
        apps = {
            "whatsapp": "com.whatsapp",
            "youtube": "com.google.android.youtube",
            "chrome": "com.android.chrome",
            "telegram": "org.telegram.messenger",
            "instagram": "com.instagram.android",
            "gmail": "com.google.android.gm",
            "maps": "com.google.android.apps.maps",
            "camera": "com.android.camera2",
            "phone": "com.android.dialer",
            "settings": "com.android.settings",
            "calculator": "com.android.calculator2",
            "calendar": "com.android.calendar",
            "clock": "com.android.deskclock",
            "spotify": "com.spotify.music",
            "playstore": "com.android.vending",
        }
        for name, pkg in apps.items():
            keywords = [
                f"open {name}", f"launch {name}", f"start {name}",
                f"{name} kholo", f"{name} open karo", f"{name} chalao",
            ]
            for kw in keywords:
                self._intent_map[kw] = "open_app"
            self._handlers[f"open_{name}"] = lambda q, p=pkg: {
                "action": "LAUNCH_APP",
                "payload": {"package": p, "action": "android.intent.action.VIEW"},
                "response": f"{pkg.split('.')[-1]} khol raha hoon! 📱",
            }

        # Media controls
        media_actions = {
            "play music": ("PLAY_MUSIC", "Music chala raha hoon! 🎵"),
            "play song": ("PLAY_MUSIC", "Song chala raha hoon! 🎵"),
            "gaana chalao": ("PLAY_MUSIC", "Gaana chala raha hoon! 🎵"),
            "bajao kuch": ("PLAY_MUSIC", "Baja raha hoon! 🎵"),
            "pause music": ("PAUSE_MUSIC", "Music rok diya! ⏸️"),
            "stop music": ("PAUSE_MUSIC", "Music band kar diya! ⏹️"),
            "music rok do": ("PAUSE_MUSIC", "Rok diya! ⏸️"),
            "next song": ("NEXT_TRACK", "Agla song! ⏭️"),
            "previous song": ("PREV_TRACK", "Pichla song! ⏮️"),
            "volume up": ("VOLUME_UP", "Volume badha diya! 🔊"),
            "volume down": ("VOLUME_DOWN", "Volume kam kar diya! 🔉"),
            "volume increase": ("VOLUME_UP", "Volume badha diya! 🔊"),
            "volume decrease": ("VOLUME_DOWN", "Volume kam kar diya! 🔉"),
            "aawaz badhao": ("VOLUME_UP", "Aawaz badha di! 🔊"),
            "aawaz kam karo": ("VOLUME_DOWN", "Aawaz kam kar di! 🔉"),
            "silent mode": ("VOLUME_MUTE", "Silent kar diya! 🔇"),
            "mute karo": ("VOLUME_MUTE", "Mute kar diya! 🔇"),
        }
        for phrase, (action, resp) in media_actions.items():
            self._intent_map[phrase] = action.lower()
            self._handlers[action.lower()] = lambda q, a=action, r=resp: {
                "action": a, "payload": {}, "response": r,
            }

        # Device controls
        device_actions = {
            "flashlight on": ("FLASHLIGHT_ON", "Flashlight on kar diya! 💡"),
            "flashlight off": ("FLASHLIGHT_OFF", "Flashlight off kar diya! 💡"),
            "torch on": ("FLASHLIGHT_ON", "Torch on kar diya! 💡"),
            "torch off": ("FLASHLIGHT_OFF", "Torch off kar diya! 💡"),
            "flashlight chalu karo": ("FLASHLIGHT_ON", "Flashlight chalu! 💡"),
            "flashlight band karo": ("FLASHLIGHT_OFF", "Flashlight band! 💡"),
            "go home": ("GO_HOME", "Home screen! 🏠"),
            "home screen": ("GO_HOME", "Home screen! 🏠"),
            "go back": ("GO_BACK", "Back! ↩️"),
            "wifi on": ("WIFI_ON", "WiFi on! 🌐"),
            "wifi off": ("WIFI_OFF", "WiFi off! 🌐"),
            "bluetooth on": ("BLUETOOTH_ON", "Bluetooth on! 🔵"),
            "bluetooth off": ("BLUETOOTH_OFF", "Bluetooth off! 🔵"),
            "screenshot lo": ("SCREENSHOT", "Screenshot! 📸"),
            "take screenshot": ("SCREENSHOT", "Screenshot! 📸"),
            "open camera": ("OPEN_CAMERA", "Camera khol raha hoon! 📸"),
            "camera kholo": ("OPEN_CAMERA", "Camera khol raha hoon! 📸"),
        }
        for phrase, (action, resp) in device_actions.items():
            self._intent_map[phrase] = action.lower()
            self._handlers[action.lower()] = lambda q, a=action, r=resp: {
                "action": a, "payload": {}, "response": r,
            }

    def process(self, ctx: CognitiveContext) -> bool:
        """Try to handle input as a reflex action.

        Returns True if handled (reflex succeeded).
        Returns False if no reflex matched — pass to next brain.
        """
        q = ctx.raw_input.lower().strip()

        # Direct keyword match (fastest path)
        if q in self._intent_map:
            intent = self._intent_map[q]
            handler = self._handlers.get(intent)
            if handler:
                result = handler(q)
                ctx.detected_intent = intent
                ctx.detected_action = result.get("action", intent.upper())
                ctx.response = result.get("response", "Done! ✅")
                ctx.payload = result.get("payload", {})
                ctx.processing_level = ProcessingLevel.REFLEX
                ctx.confidence = 1.0
                ctx.execution_time_ms = ctx.elapsed_ms()
                logger.info(f"Reflex: Direct match '{q}' → {intent} in {ctx.execution_time_ms:.1f}ms")
                return True

        # Substring matching (slightly slower but catches variations)
        # Check cache first — avoids O(n) scan for repeated queries
        cached = self._match_cache.get(q)
        if cached is not None:
            best_match, best_score = cached
        else:
            best_match = None
            best_score = 0.0
            for phrase, intent in self._intent_map.items():
                if phrase in q:
                    score = len(phrase) / len(q) if len(q) > 0 else 0
                    if score > best_score:
                        best_score = score
                        best_match = intent
            # Cache result (cache is bounded by number of unique queries seen)
            if len(self._match_cache) < 256:
                self._match_cache[q] = (best_match, best_score)

        if best_match and best_score > 0.3:
            handler = self._handlers.get(best_match)
            if handler:
                result = handler(q)
                ctx.detected_intent = best_match
                ctx.detected_action = result.get("action", best_match.upper())
                ctx.response = result.get("response", "Done! ✅")
                ctx.payload = result.get("payload", {})
                ctx.processing_level = ProcessingLevel.REFLEX
                ctx.confidence = best_score
                ctx.execution_time_ms = ctx.elapsed_ms()
                logger.info(f"Reflex: Substring match '{q}' → {best_match} ({best_score:.2f})")
                return True

        return False


class HabitProcessor:
    """Brain 2: Habit and pattern-based prediction.

    Equivalent to the human subconscious. Learns routines and
    predicts likely next actions based on time, day, and history.
    """

    def __init__(self):
        self._patterns: Dict[str, Dict] = {}  # pattern_key → pattern_data
        self._lock = threading.Lock()

    def record_action(self, ctx: CognitiveContext, now=None):
        """Record an action for habit learning."""
        from datetime import datetime
        if now is None:
            now = datetime.now()
        key = f"{now.hour}:{now.weekday()}"
        action_key = ctx.detected_intent or ctx.detected_action or "unknown"

        with self._lock:
            if key not in self._patterns:
                self._patterns[key] = {
                    "actions": {},
                    "total": 0,
                    "hour": now.hour,
                    "day": now.weekday(),
                }
            pattern = self._patterns[key]
            pattern["actions"][action_key] = pattern["actions"].get(action_key, 0) + 1
            pattern["total"] += 1

    def predict(self, ctx: CognitiveContext, now=None) -> Optional[Dict]:
        """Predict likely action based on current time context.

        Returns None if no confident prediction exists.
        """
        from datetime import datetime
        if now is None:
            now = datetime.now()
        key = f"{now.hour}:{now.weekday()}"

        with self._lock:
            pattern = self._patterns.get(key)
            if not pattern or pattern["total"] < 2:
                return None

            # Find most frequent action at this time
            best_action = max(pattern["actions"], key=pattern["actions"].get)
            best_count = pattern["actions"][best_action]
            confidence = best_count / pattern["total"]

            # Minimum confidence threshold
            if confidence < 0.3 or best_count < 2:
                return None

            return {
                "predicted_action": best_action,
                "confidence": confidence,
                "occurrences": best_count,
                "total_at_time": pattern["total"],
                "hour": pattern["hour"],
                "day": pattern["day"],
            }

    def process(self, ctx: CognitiveContext) -> bool:
        """Check if habit brain has a prediction for this context.

        Returns True if habit prediction is relevant and confident.
        The habit brain doesn't "handle" the current input — it
        predicts what should happen next based on patterns.
        """
        prediction = self.predict(ctx)
        if prediction:
            ctx.metadata["habit_prediction"] = prediction
            ctx.processing_level = ProcessingLevel.HABIT
            logger.info(
                f"Habit: Predicted '{prediction['predicted_action']}' "
                f"at conf={prediction['confidence']:.2f} "
                f"(hour={prediction['hour']}, occ={prediction['occurrences']})"
            )
            return True
        return False

    def get_stats(self) -> dict:
        with self._lock:
            return {
                "patterns_learned": len(self._patterns),
                "total_actions_recorded": sum(p["total"] for p in self._patterns.values()),
            }


from backend.cognition.planner.self_reflection import SelfReflection


class CognitiveEngine:
    """THE unified cognitive architecture.

    Processes every input through ALL brain layers in order:

    Input (user command / notification / event)
      │
      ├── 1. REFLEX BRAIN (<300ms) ─── Handled? → Return
      │     Instant actions. No LLM. No memory.
      │     Opens apps, controls volume, toggles flashlight, etc.
      │
      ├── 2. HABIT BRAIN (~200ms) ──── Prediction? → Note + Continue
      │     Pattern matching. Time/day-based prediction.
      │     "You usually open WhatsApp at this time..."
      │
      ├── 3. NEURAL BRAIN (<50ms) ──── Dataset-trained intent classification
      │     TinyNeuralNetwork. No external API calls.
      │     Only invoked when reflex fails.
      │
      ├── 4. MEMORY (async) ────────── Record and consolidate
      │     Save episode, update patterns, learn from outcome.
      │
      ├── 5. MongoDB (async) ──────── Persist to MongoDB Atlas
      │     Every chat turn + system output logged to durable storage.
      │
      └── 6. REFLECTION (async) ────── Evaluate and improve
            Daily review, improvement suggestions, learning.
    """

    def __init__(
        self,
        reflex_processor: Optional[ReflexProcessor] = None,
        habit_processor: Optional[HabitProcessor] = None,
        conscious_brain=None,
        memory_system=None,
        learning_system=None,
        enable_learning: bool = True,
        memory_consolidation=None,
    ):
        self.reflex = reflex_processor or ReflexProcessor()
        self.habit = habit_processor or HabitProcessor()
        self.conscious = conscious_brain  # Reasoning/LLM brain
        self.memory = memory_system       # Memory system
        self.learning = learning_system    # Learning system
        self.reflection = SelfReflection()
        self.enable_learning = enable_learning
        self.memory_consolidation = memory_consolidation
        self._mongodb = None  # lazy MongoDB logger

        # Shared thread pool for background tasks (reuses threads, avoids threading.Thread overhead)
        self._bg_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="cog_bg")

        # Stats
        self._stats = {
            "total_processed": 0,
            "reflex_handled": 0,
            "habit_predicted": 0,
            "reasoning_used": 0,
            "failures": 0,
            "avg_time_ms": 0.0,
        }

    def process(self, raw_input: str, **context_kwargs) -> CognitiveContext:
        """Process any input through the full cognitive pipeline.

        Args:
            raw_input: The user's command, notification text, etc.
            **context_kwargs: Additional context (user_id, emotion, topic, etc.)

        Returns:
            CognitiveContext with the processing result.
        """
        ctx = CognitiveContext(
            raw_input=raw_input,
            **{k: v for k, v in context_kwargs.items() if hasattr(CognitiveContext, k)},
        )

        # ═══════════════════════════════════════════════════════════
        # BRAIN 1: REFLEX — Instant action (<300ms)
        # ═══════════════════════════════════════════════════════════
        handled = self.reflex.process(ctx)
        if handled:
            self._update_stats(ctx)
            logger.info(f"CognitiveEngine: Reflex handled '{raw_input[:50]}' in {ctx.execution_time_ms:.0f}ms")
            self._post_process(ctx)
            return ctx

        # ═══════════════════════════════════════════════════════════
        # BRAIN 2: HABIT — Check for pattern-based prediction
        # ═══════════════════════════════════════════════════════════
        has_habit = self.habit.process(ctx)
        if has_habit:
            self._stats["habit_predicted"] += 1

        # ═══════════════════════════════════════════════════════════
        # BRAIN 3: NEURAL — Dataset-trained intent classification
        # ═══════════════════════════════════════════════════════════
        if self.conscious:
            try:
                ctx.processing_level = ProcessingLevel.NEURAL
                result = self._dispatch_to_conscious(ctx)
                ctx.response = result.get("response", "")
                ctx.detected_intent = result.get("intent", ctx.detected_intent)
                ctx.detected_action = result.get("action", ctx.detected_action)
                ctx.payload = result.get("payload")
                ctx.success = result.get("success", True)
                ctx.execution_time_ms = ctx.elapsed_ms()
                self._stats["reasoning_used"] += 1
                logger.info(f"CognitiveEngine: Neural handled '{raw_input[:50]}' in {ctx.execution_time_ms:.0f}ms")
            except Exception as e:
                ctx.response = f"Samajhne mein problem hui: {str(e)}. Please try again! 😅"
                ctx.success = False
                ctx.execution_time_ms = ctx.elapsed_ms()
                logger.error(f"CognitiveEngine: Reasoning failed: {e}", exc_info=True)
        else:
            # No reasoning brain available
            ctx.response = "Mujhe samajh nahi aaya. Kya kar sakta hoon aapke liye? 😊"
            ctx.success = False
            ctx.execution_time_ms = ctx.elapsed_ms()

        self._update_stats(ctx)
        self._post_process(ctx)
        return ctx

    def _dispatch_to_conscious(self, ctx: CognitiveContext) -> dict:
        """Route to the conscious/reasoning brain."""
        if hasattr(self.conscious, 'execute'):
            result = self.conscious.execute(ctx.raw_input)
            if hasattr(result, 'to_dict'):
                return result.to_dict()
            return result if isinstance(result, dict) else {"response": str(result)}
        elif hasattr(self.conscious, 'run'):
            result = self.conscious.run(ctx.raw_input)
            return result if isinstance(result, dict) else {"response": str(result)}
        return {"response": str(self.conscious), "success": True}

    def _post_process(self, ctx: CognitiveContext):
        """Async post-processing: memory, learning, reflection, MongoDB log."""
        def _background():
            try:
                from datetime import datetime
                now = datetime.now()  # Single call, shared across background tasks
                # Record in habit brain
                self.habit.record_action(ctx, now=now)

                # Record in memory
                if self.memory:
                    self._record_to_memory(ctx)

                # Record to working memory in memory consolidation
                if self.memory_consolidation:
                    self.memory_consolidation.add_to_working(
                        content=ctx.raw_input[:500],
                        importance=0.8 if ctx.processing_level.value == "neural" else 0.4,
                        topics=[ctx.topic or ctx.detected_intent or "general"],
                        entities=ctx.parameters or {},
                        source="user" if ctx.processing_level.value != "reasoning" else "assistant"
                    )

                # Learn from outcome
                if self.enable_learning and self.learning:
                    self.learning.observe(ctx)

                # Reflect
                self.reflection.reflect(ctx)

                # Log to MongoDB (fire-and-forget, never crashes the pipeline)
                self._log_to_mongodb(ctx)

            except Exception as e:
                logger.warning(f"CognitiveEngine: Post-process error: {e}")

        self._bg_pool.submit(_background)

    def _get_mongodb(self):
        """Lazy-load the MongoDB logger on first use."""
        if self._mongodb is None:
            try:
                from backend.core.mongodb import log_chat, log_output
                self._mongodb = (log_chat, log_output)
            except Exception as e:
                logger.debug("CognitiveEngine: MongoDB logger not available: %s", e)
                self._mongodb = (None, None)
        return self._mongodb

    def _log_to_mongodb(self, ctx: CognitiveContext):
        """Persist the current processing turn to MongoDB (fire-and-forget)."""
        try:
            log_chat_fn, log_output_fn = self._get_mongodb()
            if log_chat_fn is None:
                return

            log_chat_fn(
                user_input=ctx.raw_input[:1000],
                response=ctx.response[:2000],
                intent=ctx.detected_intent,
                action=ctx.detected_action,
                brain_type=ctx.processing_level.value,
                confidence=ctx.confidence,
                emotion=ctx.emotion,
                topic=ctx.topic,
                time_ms=ctx.execution_time_ms,
                success=ctx.success,
                metadata=ctx.metadata,
            )

            if log_output_fn:
                log_output_fn(
                    source=f"brain/{ctx.processing_level.value}",
                    content=ctx.response[:2000],
                    output_type=ctx.detected_intent or "unknown",
                    metadata={
                        "intent": ctx.detected_intent,
                        "action": ctx.detected_action,
                        "time_ms": ctx.execution_time_ms,
                    },
                )
        except Exception as e:
            logger.debug("CognitiveEngine: MongoDB log skipped: %s", e)

    def _record_to_memory(self, ctx: CognitiveContext):
        """Record the action in memory systems."""
        try:
            if hasattr(self.memory, 'add_episode'):
                self.memory.add_episode(
                    role="user" if ctx.processing_level != ProcessingLevel.NEURAL else "assistant",
                    content=ctx.raw_input[:500],
                    topic=ctx.topic or ctx.detected_intent or "general",
                    emotion=ctx.emotion or "neutral",
                    importance=3 if ctx.processing_level == ProcessingLevel.NEURAL else 1,
                )
        except Exception as e:
            logger.debug(f"Memory recording skipped: {e}")

    def _update_stats(self, ctx: CognitiveContext):
        s = self._stats
        s["total_processed"] += 1
        if ctx.processing_level == ProcessingLevel.REFLEX:
            s["reflex_handled"] += 1
        elif ctx.processing_level == ProcessingLevel.NEURAL:
            s["reasoning_used"] += 1
        if not ctx.success:
            s["failures"] += 1

        # Running average
        n = s["total_processed"]
        s["avg_time_ms"] = s["avg_time_ms"] * (n - 1) / n + ctx.execution_time_ms / n

    def get_stats(self) -> dict:
        return {
            **self._stats,
            "reflex_actions": len(self.reflex._handlers),
            "reflex_patterns": len(self.reflex._intent_map),
            "habit_patterns": self.habit.get_stats(),
            "reflection": self.reflection.get_stats(),
        }

    def get_daily_reflection(self) -> Dict:
        """Get end-of-day reflection."""
        return self.reflection.get_daily_reflection()
