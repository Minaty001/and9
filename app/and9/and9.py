"""
AND9 — Personal Android AI Operating System (Refactored).

Thin entry point that delegates all processing to the
brain/orchestrator.py pipeline. Maintains backward compatibility
with the existing POST /api/and9 API.

Processing flow:
    User Query → brain/orchestrator.Orchestrator.process()
    → Normalize → Detect Intent → Execute Action → Log → Return

Design rules enforced:
    - Device actions always beat search actions
    - Chrome only opens for explicit SEARCH intent
    - All actions pass through Android Executor (single entry point)
    - Every request logged through QueryLogger
    - Broken imports fixed (app.javis.* → app.skills.* / app.core.*)
"""
import logging
from typing import Any, Dict, Optional

from app.and9.brain.orchestrator import Orchestrator
from app.and9.core.logger import get_logger, is_debug_enabled

logger = logging.getLogger(__name__)


class AND9:
    """Main AND9 entry point — delegates to brain/orchestrator.py.

    Usage:
        and9 = AND9()
        result = and9.process("call mummy")
        # → {response, action, payload, brain, intent, ...}

        stats = and9.get_stats()
        # → {subconscious, history, logs}
    """

    def __init__(self, events_sys=None, enable_patterns: bool = True):
        """Initialize AND9 with the new brain Orchestrator.

        Args:
            events_sys: Optional EventSystem for reminder persistence.
            enable_patterns: Enable subconscious pattern learning.
        """
        self.orchestrator = Orchestrator(
            events_sys=events_sys,
            enable_patterns=enable_patterns,
        )
        self.enable_patterns = enable_patterns
        logger.info("AND9 initialized (patterns=%s, debug=%s)",
                     enable_patterns, is_debug_enabled())

    def process(self, query: str) -> Dict[str, Any]:
        """Process a user query through the AND9 pipeline.

        See brain/orchestrator.py for detailed pipeline docs.

        Args:
            query: Raw user input string.

        Returns:
            Dict with response, action, payload, brain, intent,
            parameters, time_ms, success, metadata.
        """
        return self.orchestrator.process(query)

    def get_stats(self) -> Dict[str, Any]:
        """Get system statistics from the orchestrator.

        Returns:
            Dict with stats from subconscious and query logs.
        """
        return self.orchestrator.get_stats()
