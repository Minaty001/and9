"""
app/brain/manager.py — Brain routing and coordination for AND9

Receives processed intent -> decides routing:
  - Subconscious: instant device actions (< 300 ms)
  - Conscious:    LLM reasoning (1-10 s)

Routing logic:
  1. Extract intent from UnderstandingEngine
  2. If intent in SubconsciousBrain.SUBCONSCIOUS_INTENTS -> SubconsciousBrain
  3. Else if 'device' route from IntentRouter -> SubconsciousBrain
  4. Else -> ConsciousBrain
"""

import logging
import time
from app.core.understanding import UnderstandingEngine
from app.core.event_bus import EventBus, Event
from app.core.task_queue import TaskQueue, Priority
from app.brain.subconscious import SubconsciousBrain
from app.brain.conscious import ConsciousBrain

logger = logging.getLogger(__name__)


class BrainManager:
    def __init__(self, event_bus: EventBus, task_queue: TaskQueue):
        self._bus = event_bus
        self._queue = task_queue
        self._understanding = UnderstandingEngine()
        self._subconscious = SubconsciousBrain()
        self._conscious = ConsciousBrain()

        # Subscribe to input events
        self._bus.subscribe("input.text", self._on_input)
        self._bus.subscribe("input.voice", self._on_input)

    def process(self, text: str, request_id: str = "",
                session_id: int = 0) -> dict:
        """
        Main entry point called by the Kernel.
        Analyzes -> routes -> executes -> returns result.
        """
        # 1. Understand the input
        analysis = self._understanding.analyze(text)

        self._bus.publish("intent.detected", {
            "request_id": request_id,
            "intent": analysis.intent,
            "entities": analysis.entities,
        }, source="brain_manager")

        # 2. Route decision
        if self._subconscious.can_handle(analysis.intent):
            brain = "subconscious"
            priority = Priority.HIGH
        else:
            brain = "conscious"
            priority = Priority.MEDIUM

        self._bus.publish("intent.routed", {
            "request_id": request_id,
            "brain": brain,
        }, source="brain_manager")

        # 3. Execute through Task Queue
        if brain == "subconscious":
            def fn():
                return self._subconscious.execute(
                            analysis.intent, analysis.entities
                        )
        else:
            def fn():
                return self._conscious.think(
                            text, analysis, session_id=session_id
                        )

        task_id = self._queue.enqueue(
            fn=fn,
            name=f"{brain}.{analysis.intent}",
            priority=priority
        )

        # 4. Wait for result (synchronous for now — async in v6.0)
        deadline = time.time() + 15  # 15s max wait
        while time.time() < deadline:
            result = self._queue.get_result(task_id)
            if result is not None:
                return result
            time.sleep(0.05)

        return {
            "success": False,
            "response": "Request timed out. Please try again.",
            "brain": brain,
        }

    def _on_input(self, event: Event) -> None:
        """Event handler for input events (called by Event Bus)."""
        text = event.payload.get("text", "")
        if text:
            self.process(text, request_id=event.payload.get("request_id", ""))