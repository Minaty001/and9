"""
AND9 — Personal Android AI Operating System.

Main orchestrator implementing the multi-brain cognitive architecture.
Routes every user query through a three-layer processing pipeline:

  1. Normalize    → Convert Hindi/Hinglish to English
  2. Route        → Detect intent and dispatch to the correct brain
  3. Learn        → Record action in subconscious for pattern learning

The three brains work together:
  - Reflex Brain (<100ms):      Instant, deterministic actions
  - Subconscious Brain (~200ms): Pattern learning & habit detection
  - Conscious Brain (~1-5s):    LLM reasoning for complex tasks

Usage:
    from app.and9 import AND9

    and9 = AND9()
    result = and9.process("call mummy")
    # → { "response": "Call kar raha hoon Mummy ko... 📞",
    #     "action": "CALL",
    #     "brain": "reflex",
    #     "intent": "call", ... }
"""
import logging
import time
from typing import Optional, Dict, Any

from app.and9.brain_types import BrainType, BrainResult, IntentType
from app.and9.reflex_brain import ReflexBrain
from app.and9.subconscious_brain import SubconsciousBrain
from app.and9.conscious_brain import ConsciousBrain

logger = logging.getLogger(__name__)


class AND9:
    """Main AND9 orchestrator — routes queries through the multi-brain pipeline.

    The AND9 singleton manages the three brain instances and coordinates
    the execution pipeline. It is stateless from the caller's perspective
    — all state is encapsulated in the brain instances.

    Attributes:
        reflex: ReflexBrain instance for instant actions.
        subconscious: SubconsciousBrain instance for pattern learning.
        conscious: ConsciousBrain instance for LLM reasoning.
        events_sys: Optional EventSystem for reminder persistence.
    """

    def __init__(self, events_sys=None, enable_patterns: bool = True):
        """Initialize the AND9 system with all three brains.

        Args:
            events_sys: Optional EventSystem instance. If provided,
                        reminders and time-based events can be persisted.
            enable_patterns: If True (default), the subconscious brain
                            records actions for pattern learning. Set
                            False for testing or privacy-sensitive modes.
        """
        self.reflex = ReflexBrain()
        self.subconscious = SubconsciousBrain(enable_learning=enable_patterns)
        self.conscious = ConsciousBrain()
        self.events_sys = events_sys
        self.enable_patterns = enable_patterns
        logger.info("AND9 initialized (patterns=%s)", enable_patterns)

    def process(self, query: str) -> Dict[str, Any]:
        """Process a user query through the full AND9 pipeline.

        Pipeline steps:
        1. Normalize:      Convert Hindi/Hinglish to English commands
        2. Detect intent:  Classify intent via priority router
        3. Route to brain: Dispatch to Reflex/Subconscious/Conscious
        4. Execute:        Run the appropriate handler
        5. Record:         Log action in subconscious for pattern learning
        6. Return:         Serialize BrainResult to JSON-safe dict

        Args:
            query: Raw user input string in Hindi, Hinglish, or English.

        Returns:
            Dict with keys:
              - response: Human-readable reply text
              - action: Action constant (e.g., "LAUNCH_APP", "CALL")
              - payload: Android Intent data for device execution
              - brain: BrainType that handled the request
              - intent: IntentType that was detected
              - parameters: Structured parameters from the query
              - time_ms: Execution time in milliseconds
              - success: Whether processing completed successfully
              - metadata: Extra info for frontend rendering

        Examples:
            >>> and9 = AND9()
            >>> and9.process("youtube kholo")
            {'response': 'Youtube khol raha hoon... 📱',
             'action': 'LAUNCH_APP', 'brain': 'reflex', 'success': True, ...}

            >>> and9.process("hello kaise ho")
            {'response': '...', 'brain': 'conscious', 'success': True, ...}
        """
        start = time.perf_counter()
        logger.info("AND9 processing: '%s'", query)

        if not query or not query.strip():
            return BrainResult(
                response="Kya karu? Mujhe samajh nahi aaya. Kuch type karo! 😊",
                brain=BrainType.REFLEX,
                execution_time_ms=(time.perf_counter() - start) * 1000,
            ).to_dict()

        try:
            # Step 1-3: Normalize, detect intent, and determine brain
            # These are done together inside reflex_brain.execute()
            # for efficiency.

            # Step 4: Execute with the correct brain
            result = self._route_to_brain(query)

            # Step 5: Record in subconscious for pattern learning
            if self.enable_patterns and result.success:
                self.subconscious.record_action(result, query)

            # Check for learned patterns after recording
            pattern = self.subconscious.get_pattern()
            if pattern:
                logger.info("Pattern detected: %s", pattern["suggestion"])

            # Update execution time to reflect full pipeline
            result.execution_time_ms = (time.perf_counter() - start) * 1000

            return result.to_dict()

        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            logger.error("AND9 pipeline error: %s", e, exc_info=True)
            return BrainResult(
                response=(
                    f"Oops! Kuch gadbad ho gayi: {str(e)}. "
                    f"Phir se try karo! 😅"
                ),
                action="ERROR",
                brain=BrainType.REFLEX,
                execution_time_ms=elapsed,
                success=False,
            ).to_dict()

    def _route_to_brain(self, query: str) -> BrainResult:
        """Route a query to the appropriate brain.

        Determines which brain should handle the query based on
        intent classification and brain capabilities.

        Routing decision:
          - REFLEX intent (emergency, call, app launch, device
            control, alarm, timer, reminder, media):
            → ReflexBrain.execute()
          - SUBCONSCIOUS intent (automation/routines):
            → Handled by reflex brain + pattern detection
          - CONSCIOUS intent (chat, search, goal, complex tasks):
            → ConsciousBrain.execute()

        Args:
            query: Raw user query.

        Returns:
            BrainResult from the executing brain.
        """
        # First check if this is a simple intent the reflex brain can handle
        from app.and9.normalizer import normalize
        from app.and9.priority_router import detect_intent

        normalized, _ = normalize(query)
        intent, brain = detect_intent(normalized)

        # Route based on brain type
        if brain == BrainType.REFLEX:
            logger.debug("Routing to REFLEX brain (intent=%s)", intent)
            result = self.reflex.execute(query, self.events_sys, self.enable_patterns)
            return result

        elif brain == BrainType.SUBCONSCIOUS:
            # Subconscious automation: delegate to reflex for execution
            logger.debug("Routing to SUBCONSCIOUS brain (intent=%s)", intent)
            result = self.reflex.execute(query, self.events_sys, self.enable_patterns)

            # Enhance with pattern info if available
            pattern = self.subconscious.get_pattern()
            if pattern:
                result.response = f"{result.response}\n\n{pattern['suggestion']}"

            return result

        else:
            # Conscious brain for chat, search, complex tasks
            logger.debug("Routing to CONSCIOUS brain (intent=%s)", intent)
            result = self.conscious.execute(normalized)
            return result

    def get_stats(self) -> Dict[str, Any]:
        """Get system statistics from all three brains.

        Returns:
            Dict with stats from each brain component:
              - reflex: Count of reflex actions
              - subconscious: Pattern learning statistics
              - conscious: LLM invocation count
        """
        subconscious_stats = self.subconscious.get_stats()
        return {
            "subconscious": subconscious_stats,
            "history": self.subconscious.get_history(limit=10),
            "patterns": {
                "time_based": self.subconscious.get_pattern() is not None,
                "total_actions": subconscious_stats.get("total_actions", 0),
            },
        }
