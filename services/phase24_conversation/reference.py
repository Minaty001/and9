"""
Phase 24 — Reference Resolver.

Resolve references (pronouns, anaphora) using recent conversation context.
"""

import re
import logging
from typing import Any, Dict, List, Optional

from .models import DialogueState

logger = logging.getLogger(__name__)


class ReferenceResolver:
    """Resolve references using recent context from the last N turns."""

    def __init__(self, max_context_turns: int = 3):
        self._max_context_turns = max_context_turns

    def resolve(self, reference: str, session_id: str, dialogue_states: List[DialogueState]) -> str:
        """Resolve a reference using recent dialogue context.

        Args:
            reference: The reference text to resolve (e.g., "it", "that", "there").
            session_id: Session identifier.
            dialogue_states: List of recent dialogue states for context.

        Returns:
            Resolved reference string, or the original reference if unresolved.
        """
        reference_lower = reference.lower().strip()

        # Common anaphoric references
        pronoun_map = {
            "it": None,
            "that": None,
            "this": None,
            "there": None,
            "they": None,
            "them": None,
            "he": None,
            "she": None,
            "his": None,
            "her": None,
            "its": None,
        }

        if reference_lower not in pronoun_map:
            return reference

        # Look through recent dialogue states (most recent first)
        context = list(reversed(dialogue_states[-self._max_context_turns:]))

        for state in context:
            # Check references map
            if state.references:
                # Return the first (most recent) entity value
                for key, value in state.references.items():
                    if isinstance(value, str) and value:
                        logger.debug(
                            "Resolved '%s' -> '%s' from session %s",
                            reference, value, session_id,
                        )
                        return value

            # Check recent entities
            if state.recent_entities:
                for key, value in state.recent_entities.items():
                    if isinstance(value, str) and value:
                        return value

            # Check active topic
            if state.active_topic and state.active_topic != "general":
                return state.active_topic

        # Unresolved - return original
        return reference

    def extract_references(self, text: str) -> List[str]:
        """Extract potential reference words from text.

        Args:
            text: The text to scan.

        Returns:
            List of reference words found.
        """
        ref_words = {"it", "that", "this", "there", "they", "them", "he", "she", "his", "her", "its"}
        words = re.findall(r'\b\w+\b', text.lower())
        return [w for w in words if w in ref_words]
