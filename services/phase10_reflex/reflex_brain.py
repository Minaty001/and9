"""
Phase 10 — Reflex Brain.

Fast pattern-matching engine that maps input text to predefined actions
without requiring the full NLU pipeline.  Uses priority-ordered regex
matching.

Built-in actions cover greetings, farewells, confirmations, time/date
queries, help, and gratitude.
"""

from __future__ import annotations

import re
import time
import logging
from typing import Any, Callable, Dict, List, Optional, Pattern

from .config import ReflexConfig

logger = logging.getLogger(__name__)

HandlerFn = Callable[[str], Optional[str]]


class ReflexAction:
    """A registered reflex pattern-action pair.

    Attributes:
        action_id: Unique identifier.
        pattern: Regex string to match against input.
        intent: Intent label to assign on match.
        response: Static response text (or None if handler provides it).
        priority: Lower number = higher priority (0 = highest).
        handler: Optional callable fn(text) → response string or None.
        is_enabled: Whether this action is active.
        metadata: Arbitrary extra data.
    """

    def __init__(
        self,
        action_id: str,
        pattern: str,
        intent: str = "",
        response: Optional[str] = None,
        priority: int = 100,
        handler: Optional[HandlerFn] = None,
        is_enabled: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.action_id = action_id
        self.pattern = pattern
        self._compiled: Optional[Pattern] = None
        self.intent = intent
        self.response = response
        self.priority = priority
        self.handler = handler
        self.is_enabled = is_enabled
        self.metadata = metadata or {}

    def compile(self, case_sensitive: bool = False) -> Pattern:
        """Compile and cache the regex pattern."""
        if self._compiled is None:
            flags = 0 if case_sensitive else re.IGNORECASE
            self._compiled = re.compile(self.pattern, flags)
        return self._compiled

    def match(self, text: str, case_sensitive: bool = False) -> Optional[re.Match]:
        """Check if the input matches this action's pattern."""
        pattern = self.compile(case_sensitive)
        return pattern.search(text)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "pattern": self.pattern,
            "intent": self.intent,
            "response": self.response,
            "priority": self.priority,
            "is_enabled": self.is_enabled,
            "has_handler": self.handler is not None,
        }


class ReflexResult:
    """Result of processing input through the reflex brain."""

    def __init__(
        self,
        matched: bool = False,
        action: Optional[ReflexAction] = None,
        response: Optional[str] = None,
        intent: str = "",
        confidence: float = 0.0,
        processing_time_ms: float = 0.0,
        match_text: str = "",
    ):
        self.matched = matched
        self.action = action
        self.response = response
        self.intent = intent
        self.confidence = confidence
        self.processing_time_ms = processing_time_ms
        self.match_text = match_text

    def to_dict(self) -> Dict[str, Any]:
        return {
            "matched": self.matched,
            "action_id": self.action.action_id if self.action else None,
            "response": self.response,
            "intent": self.intent,
            "confidence": self.confidence,
            "processing_time_ms": round(self.processing_time_ms, 2),
        }


def _build_default_actions() -> List[ReflexAction]:
    """Create the built-in set of reflex actions."""
    actions = []

    # --- Greetings (priority 10) ---
    actions.append(ReflexAction(
        action_id="greeting_hello",
        pattern=r"\b(?:hello|hi|hey|hii|hlo|namaste|namaskar|good\s*(?:morning|afternoon|evening))\b",
        intent="greeting",
        response="Hello! How can I help you?",
        priority=10,
    ))

    # --- Farewells (priority 15) ---
    actions.append(ReflexAction(
        action_id="farewell_bye",
        pattern=r"\b(?:bye|goodbye|see\s*you|alvida|ta\s*ta|night|good\s*night|take\s*care)\b",
        intent="farewell",
        response="Goodbye! Have a great day!",
        priority=15,
    ))

    # --- Thanks (priority 20) ---
    actions.append(ReflexAction(
        action_id="gratitude",
        pattern=r"\b(?:thank\s*you|thanks|thx|thankful|grateful|dhanyavaad|shukriya)\b",
        intent="gratitude",
        response="You're welcome! Happy to help.",
        priority=20,
    ))

    # --- Help (priority 25) ---
    actions.append(ReflexAction(
        action_id="help",
        pattern=r"\b(?:help|what can you do|commands|capabilities|features)\b",
        intent="help",
        response="I can help with weather, alarms, calls, messages, music, navigation, and more. Try asking me something!",
        priority=25,
    ))

    # --- Affirmative (priority 30) ---
    actions.append(ReflexAction(
        action_id="confirm_yes",
        pattern=r"^\s*(?:yes|yeah|yep|sure|okay|ok|haan|haa|hmm|correct|right|done)\s*$",
        intent="affirmative",
        response="Okay, processing your request.",
        priority=30,
    ))

    # --- Negative (priority 35) ---
    actions.append(ReflexAction(
        action_id="confirm_no",
        pattern=r"^\s*(?:no|nope|nah|na|never|cancel|stop|nahi|mat karo|ruko)\s*$",
        intent="negative",
        response="Cancelled. Let me know if you need anything else.",
        priority=35,
    ))

    # --- Time query (priority 40) ---
    actions.append(ReflexAction(
        action_id="query_time",
        pattern=r"\b(?:what\s*(?:is|'s)\s*(?:the\s*)?time|current\s*time|time\s*(?:now|abhi)|kitna\s*baje|time\s*kya\s*hai)\b",
        intent="query_time",
        response=None,  # dynamic — handler provides it
        priority=40,
        handler=lambda text: f"The current time is {__import__('time').strftime('%I:%M %p')}.",
    ))

    # --- Date query (priority 45) ---
    actions.append(ReflexAction(
        action_id="query_date",
        pattern=r"\b(?:what\s*(?:is|'s)\s*(?:the\s*)?date|today\s*(?:date|what|kya)|current\s*date|aaj\s*kya\s*date)\b",
        intent="query_date",
        response=None,  # dynamic
        priority=45,
        handler=lambda text: f"Today's date is {__import__('datetime').datetime.now().strftime('%B %d, %Y')}.",
    ))

    # --- Capabilities (priority 50) ---
    actions.append(ReflexAction(
        action_id="capabilities_weather",
        pattern=r"\b(?:weather|temperature|mausam|barish|dhoop)\b",
        intent="weather_query",
        priority=50,
    ))

    actions.append(ReflexAction(
        action_id="capabilities_alarm",
        pattern=r"\b(?:alarm|alaram|set\s+alarm|wake\s+me|jaago)\b",
        intent="set_alarm",
        priority=50,
    ))

    actions.append(ReflexAction(
        action_id="capabilities_reminder",
        pattern=r"\b(?:remind|reminder|yaad|dilaao|notify)\b",
        intent="set_reminder",
        priority=50,
    ))

    return actions


class ReflexBrain:
    """Fast pattern-matching brain for well-known commands.

    Actions are matched in priority order.  The first matching enabled
    action determines the result.  Handlers can generate dynamic responses.

    Usage:
        brain = ReflexBrain()
        result = brain.process("hello")
        if result.matched:
            print(result.response)
    """

    def __init__(self, config: Optional[ReflexConfig] = None):
        self.config = config or ReflexConfig()
        self._actions: Dict[str, ReflexAction] = {}
        self._initialized = False

    def initialize(self) -> None:
        """Register default actions and mark ready."""
        if self.config.enable_default_actions:
            defaults = _build_default_actions()
            for action in defaults:
                self.add_action(action)
        self._initialized = True
        logger.info("ReflexBrain initialized with %d actions", len(self._actions))

    def add_action(self, action: ReflexAction) -> None:
        """Register a new reflex action."""
        if len(self._actions) >= self.config.max_actions:
            logger.warning("Reflex action limit reached (%d)", self.config.max_actions)
            return
        existing = self._actions.get(action.action_id)
        if existing:
            logger.debug("Replacing existing reflex action: %s", action.action_id)
        self._actions[action.action_id] = action

    def remove_action(self, action_id: str) -> bool:
        """Unregister a reflex action by ID."""
        if action_id in self._actions:
            del self._actions[action_id]
            return True
        return False

    def get_action(self, action_id: str) -> Optional[ReflexAction]:
        """Get a registered action by ID."""
        return self._actions.get(action_id)

    def list_actions(self) -> List[ReflexAction]:
        """List all registered actions, sorted by priority (ascending)."""
        return sorted(self._actions.values(), key=lambda a: (a.priority, a.action_id))

    def process(self, text: str) -> ReflexResult:
        """Match input against all registered actions in priority order.

        Args:
            text: Input text to match.

        Returns:
            ReflexResult indicating whether a match was found.
        """
        t0 = time.perf_counter()
        result = ReflexResult()

        if not text:
            elapsed = (time.perf_counter() - t0) * 1000
            result.processing_time_ms = elapsed
            return result

        # Sort actions by priority (ascending) for ordered matching
        sorted_actions = sorted(
            self._actions.values(),
            key=lambda a: (a.priority, a.action_id),
        )

        for action in sorted_actions:
            if not action.is_enabled:
                continue

            match = action.match(text, self.config.case_sensitive)
            if match:
                result.matched = True
                result.action = action
                result.intent = action.intent
                result.confidence = self.config.default_confidence
                result.match_text = match.group(0)

                # Determine response: handler first, then static, then pattern-based
                if action.handler and self.config.enable_handler_execution:
                    try:
                        handler_response = action.handler(text)
                        if handler_response:
                            result.response = handler_response
                    except Exception as e:
                        logger.error("Reflex handler '%s' failed: %s", action.action_id, e)
                        result.response = action.response
                else:
                    result.response = action.response

                elapsed = (time.perf_counter() - t0) * 1000
                result.processing_time_ms = elapsed

                logger.debug("Reflex matched: action=%s intent=%s in %.2fms",
                             action.action_id, action.intent, elapsed)
                return result  # first match wins

        elapsed = (time.perf_counter() - t0) * 1000
        result.processing_time_ms = elapsed
        return result

    def get_action_count(self) -> int:
        return len(self._actions)
