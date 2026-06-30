"""
Phase 8 — Context Manager.

Manages a sliding window of conversation turns with:
- Time-based exponential decay
- Entity overlap relevance scoring
- Intent match boosting
- Recency weighting
- Relevance-based context pruning
"""

from __future__ import annotations

import time
import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from .config import ContextConfig
from .models import TurnContext, ContextSnapshot

logger = logging.getLogger(__name__)


class TurnScore:
    """Relevance score for a past turn relative to the current query."""

    def __init__(self, turn: TurnContext, score: float):
        self.turn = turn
        self.score = score


class ContextManager:
    """Sliding-window context manager with decay and relevance scoring.

    Usage:
        mgr = ContextManager()
        mgr.add_turn(query="what's the weather", intent="weather_query", entities={"location": ["Delhi"]})
        mgr.add_turn(query="and in Mumbai?", intent="weather_query", entities={"location": ["Mumbai"]})
        snapshot = mgr.get_snapshot()
        scored = mgr.search_relevant("rain in Delhi", top_k=3)
    """

    def __init__(self, config: Optional[ContextConfig] = None):
        self.config = config or ContextConfig()
        self._turns: List[TurnContext] = []
        self._next_turn_id: int = 0
        self._session_id: str = uuid.uuid4().hex[:8]
        self._session_start: float = time.time()
        self._active_entities: Dict[str, List[str]] = {}
        self._initialized = False

        logger.info("ContextManager created (session=%s, max_turns=%d)", self._session_id, self.config.max_turns)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_turn(
        self,
        query: str,
        intent: str = "",
        intent_confidence: float = 0.0,
        entities: Optional[Dict[str, List[str]]] = None,
        normalized_query: str = "",
        embedding: Optional[List[float]] = None,
        response: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TurnContext:
        """Add a new turn to the context window.

        The window slides when max_turns is exceeded.  If auto_decay is
        enabled, existing turns have their relevance decay applied.
        """
        turn = TurnContext(
            turn_id=self._next_turn_id,
            query=query,
            normalized_query=normalized_query or query.lower().strip(),
            intent=intent,
            intent_confidence=intent_confidence,
            entities=entities or {},
            embedding=embedding,
            response=response,
            metadata=metadata or {},
        )
        self._next_turn_id += 1

        # Track entities
        if self.config.enable_entity_tracking and entities:
            self._merge_entities(entities)

        # Apply decay to existing turns
        if self.config.enable_auto_decay:
            self._apply_decay(turn)

        self._turns.append(turn)

        # Slide window
        if len(self._turns) > self.config.max_turns:
            removed = self._turns.pop(0)
            logger.debug("Evicted turn %d: %s", removed.turn_id, removed.query[:40])

        # Prune low-relevance turns (keep at least 3)
        self._prune_low_relevance(min_keep=3)

        logger.debug("Context now has %d turns", len(self._turns))
        return turn

    def get_snapshot(self) -> ContextSnapshot:
        """Return a snapshot of the current context state."""
        recent = list(self._turns)
        current_turn = recent[-1] if recent else None
        elapsed = time.time() - self._session_start
        is_active = (elapsed / 60.0) < self.config.session_timeout_minutes

        return ContextSnapshot(
            session_id=self._session_id,
            turn_count=self._next_turn_id,
            recent_turns=recent,
            current_turn=current_turn,
            active_entities=dict(self._active_entities),
            recent_intents=[t.intent for t in recent if t.intent],
            elapsed_seconds=round(elapsed, 1),
            is_active=is_active,
        )

    def search_relevant(self, query: str, top_k: int = 5) -> List[TurnScore]:
        """Find the most relevant past turns for *query*.

        Scoring combines:
            - entity overlap between *query* and each past turn
            - recency (later turns score higher)
            - decay factor from earlier time-based decay

        Args:
            query: The current query text.
            top_k: Maximum number of results.

        Returns:
            List of TurnScore sorted descending by relevance.
        """
        if not self._turns or not query:
            return []

        query_lower = query.lower().strip()
        query_entities = self._extract_entity_hints(query_lower)
        current_time = datetime.now(timezone.utc)
        total_turns = len(self._turns)

        scored: List[Tuple[float, TurnContext]] = []

        for i, turn in enumerate(self._turns):
            # 1. Recency: later turns score higher
            recency = (i + 1) / total_turns

            # 2. Entity overlap between query and turn entities
            entity_score = self._compute_entity_overlap(query_entities, turn.entities)

            # 3. Intent match — check overlap between query and intent keywords
            intent_score = self._compute_intent_match(query_lower, turn.intent)

            # 4. Decay factor
            decay = turn.decay_factor(self.config.decay_rate)

            # Weighted combination
            score = (
                self.config.recency_weight * recency * decay
                + self.config.entity_overlap_weight * entity_score * decay
                + self.config.intent_match_weight * intent_score
            )

            scored.append((score, turn))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [TurnScore(turn=t, score=s) for s, t in scored[:top_k]]

    def clear(self) -> None:
        """Reset the context window."""
        self._turns.clear()
        self._active_entities.clear()
        self._next_turn_id = 0
        self._session_start = time.time()
        self._session_id = uuid.uuid4().hex[:8]
        logger.info("Context cleared (new session=%s)", self._session_id)

    def get_turn_count(self) -> int:
        return self._next_turn_id

    def get_session_age_seconds(self) -> float:
        return time.time() - self._session_start

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _merge_entities(self, entities: Dict[str, List[str]]) -> None:
        """Merge new entities into the active entity map."""
        for etype, values in entities.items():
            if etype not in self._active_entities:
                self._active_entities[etype] = []
            for val in values:
                if val not in self._active_entities[etype]:
                    self._active_entities[etype].append(val)
                    if len(self._active_entities[etype]) > 20:  # cap per type
                        self._active_entities[etype] = self._active_entities[etype][-20:]

    def _apply_decay(self, new_turn: TurnContext) -> None:
        """Apply time-based decay to existing turns."""
        # Decay is computed lazily via TurnContext.decay_factor();
        # we don't mutate stored turns — just let the factor be
        # computed at query/relevance time.
        pass

    def _prune_low_relevance(self, min_keep: int = 3) -> None:
        """Remove turns whose relevance falls below threshold, if many exist."""
        if len(self._turns) <= min_keep:
            return
        threshold = self.config.relevance_threshold
        # Use a dummy query to score relative to "everything" — for
        # pruning we evaluate overall usefulness by intent diversity
        # and recency.
        kept: List[TurnContext] = []
        for i, turn in enumerate(self._turns):
            # Keep the most recent 3 always
            if i >= len(self._turns) - min_keep:
                kept.append(turn)
                continue
            # Prune based on has-intent + recency
            has_intent = 1.0 if turn.intent else 0.0
            recency = (i + 1) / len(self._turns)
            decay = turn.decay_factor(self.config.decay_rate)
            score = 0.5 * recency * decay + 0.5 * has_intent
            if score >= threshold:
                kept.append(turn)
        self._turns = kept

    @staticmethod
    def _compute_entity_overlap(
        query_entities: Set[str],
        turn_entities: Dict[str, List[str]],
    ) -> float:
        """Jaccard-like entity overlap between query hints and stored entities."""
        if not query_entities or not turn_entities:
            return 0.0
        turn_values = set()
        for vals in turn_entities.values():
            turn_values.update(v.lower() for v in vals)
        intersection = query_entities & turn_values
        union = query_entities | turn_values
        return len(intersection) / max(len(union), 1)

    @staticmethod
    def _compute_intent_match(query_lower: str, intent: str) -> float:
        """Check if query tokens overlap with intent-derived keywords."""
        if not query_lower or not intent:
            return 0.0
        # Split intent by underscore to get component keywords
        intent_parts = set(intent.lower().split("_"))
        # Check if any intent keyword appears in the query
        for part in intent_parts:
            if part and len(part) > 2 and part in query_lower:
                return 1.0
        # Also check for intent-related common words
        INTENT_KEYWORDS = {
            "weather": ["weather", "climate", "temperature", "rain", "forecast"],
            "music": ["play", "music", "song", "gaana", "audio"],
            "alarm": ["alarm", "wake", "remind", "timer", "set"],
            "call": ["call", "phone", "dial", "contact"],
            "message": ["message", "text", "sms", "whatsapp"],
            "navigation": ["navigate", "direction", "route", "map", "location"],
            "search": ["search", "find", "look", "dhoondho"],
        }
        for part in intent_parts:
            if part in INTENT_KEYWORDS:
                for kw in INTENT_KEYWORDS[part]:
                    if kw in query_lower:
                        return 0.8
        return 0.0

    @staticmethod
    def _extract_entity_hints(text: str) -> Set[str]:
        """Simple lowercase token extraction for relevance matching."""
        import re
        tokens = re.findall(r"[a-zA-Z]+", text)
        # Skip very common words that are not entity-like
        STOPWORDS = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "do", "does", "did", "has", "have", "had", "in", "on", "at",
            "to", "for", "of", "with", "and", "or", "but", "not", "no",
            "what", "when", "where", "who", "how", "why", "which",
            "this", "that", "these", "those", "it", "its", "my", "your",
            "i", "you", "we", "they", "he", "she", "me", "him", "her",
            "can", "will", "would", "could", "should", "may", "might",
            "please", "just", "like", "want", "need", "tell", "show",
            "get", "set", "make", "go", "doe",
        }
        return {t for t in tokens if len(t) > 2 and t not in STOPWORDS}
