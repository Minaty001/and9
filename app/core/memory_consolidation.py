"""
╔══════════════════════════════════════════════════════════════╗
║           MEMORY CONSOLIDATION — Working → Episodic → Semantic ║
║   Background process that manages memory across time scales  ║
╚══════════════════════════════════════════════════════════════╝

Memory consolidation is the process of:
1. Promoting important Working Memory → Episodic Memory
2. Consolidating Episodic Memory patterns → Semantic Memory
3. Forgetting low-importance memories to free capacity
4. Strengthening frequently accessed memory pathways

This runs as a background process, mimicking the human brain's
memory consolidation during sleep/rest.
"""

import logging
import time
import threading
import json
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class ConsolidatedMemory:
    """A consolidated memory entry."""
    memory_id: str
    content: str
    memory_type: str  # 'working', 'episodic', 'semantic'
    importance: float
    access_count: int = 0
    emotional_intensity: float = 0.0
    topics: List[str] = field(default_factory=list)
    entities: Dict[str, str] = field(default_factory=dict)
    timestamp: float = 0.0
    last_accessed: float = 0.0
    consolidated: bool = False
    source: str = ""


class MemoryConsolidation:
    """Background memory consolidation engine.

    Responsibilities:
    1. Scan working memory → promote important entries to episodic
    2. Scan episodic memory → extract patterns for semantic
    3. Forget low-importance, old memories
    4. Strengthen frequently-accessed memories
    5. Generate consolidated summaries

    Run this as a background thread that wakes periodically.
    """

    def __init__(
        self,
        consolidate_interval: float = 300.0,  # 5 minutes between cycles
        importance_threshold: float = 0.3,    # Min importance to promote
        forget_threshold_days: float = 30.0,  # Forget after 30 days
        max_working_memory: int = 100,
        max_episodic_memory: int = 1000,
    ):
        self.consolidate_interval = consolidate_interval
        self.importance_threshold = importance_threshold
        self.forget_threshold_days = forget_threshold_days
        self.max_working_memory = max_working_memory
        self.max_episodic_memory = max_episodic_memory

        # In-memory storage (in production, backed by Supabase/SQLite)
        self._lock = threading.RLock()
        self._working_memory: List[ConsolidatedMemory] = []
        self._episodic_memory: List[ConsolidatedMemory] = []
        self._semantic_memory: Dict[str, ConsolidatedMemory] = {}
        self._semantic_patterns: Dict[str, Counter] = defaultdict(Counter)

        # Stats
        self._cycles_run = 0
        self._total_promoted = 0
        self._total_forgotten = 0
        self._running = False

    # ── Public API ──────────────────────────────────────────────

    def start(self):
        """Start the background consolidation thread."""
        if self._running:
            return
        self._running = True
        thread = threading.Thread(target=self._run_loop, daemon=True)
        thread.start()
        logger.info(f"MemoryConsolidation: Started (interval={self.consolidate_interval}s)")

    def stop(self):
        """Stop the consolidation thread."""
        self._running = False

    def add_to_working(self, content: str, importance: float = 0.5,
                       topics: List[str] = None, entities: Dict[str, str] = None,
                       source: str = "") -> str:
        """Add a memory to working memory.

        Working memory is short-term, high-detail storage.
        Important entries will be promoted to episodic memory.
        """
        mem = ConsolidatedMemory(
            memory_id=self._generate_id("wm"),
            content=content,
            memory_type="working",
            importance=min(1.0, importance),
            topics=topics or ["general"],
            entities=entities or {},
            timestamp=time.time(),
            last_accessed=time.time(),
            source=source,
        )

        with self._lock:
            self._working_memory.append(mem)
            # Enforce size limit
            if len(self._working_memory) > self.max_working_memory:
                self._trim_lowest_importance(self._working_memory, self.max_working_memory)

        return mem.memory_id

    def add_episodic(self, content: str, importance: float = 0.5,
                     emotional_intensity: float = 0.0,
                     topics: List[str] = None, entities: Dict[str, str] = None,
                     source: str = "") -> str:
        """Add a memory directly to episodic memory."""
        mem = ConsolidatedMemory(
            memory_id=self._generate_id("ep"),
            content=content,
            memory_type="episodic",
            importance=min(1.0, importance),
            emotional_intensity=min(1.0, emotional_intensity),
            topics=topics or ["general"],
            entities=entities or {},
            timestamp=time.time(),
            last_accessed=time.time(),
            source=source,
        )

        with self._lock:
            self._episodic_memory.append(mem)
            if len(self._episodic_memory) > self.max_episodic_memory:
                self._trim_lowest_importance(self._episodic_memory, self.max_episodic_memory)

        return mem.memory_id

    def add_semantic(self, key: str, value: str, importance: float = 0.5,
                     topics: List[str] = None, source: str = "") -> bool:
        """Add or update a semantic memory (fact/knowledge)."""
        mem = ConsolidatedMemory(
            memory_id=f"sm_{key}",
            content=f"{key}: {value}",
            memory_type="semantic",
            importance=min(1.0, importance),
            topics=topics or ["general"],
            entities={key: value},
            timestamp=time.time(),
            last_accessed=time.time(),
            consolidated=True,
            source=source,
        )

        with self._lock:
            existing = self._semantic_memory.get(key)
            if existing:
                # Strengthen existing memory
                existing.importance = min(1.0, existing.importance + 0.1)
                existing.access_count += 1
                existing.last_accessed = time.time()
            else:
                self._semantic_memory[key] = mem
                logger.debug(f"MemoryConsolidation: New semantic memory '{key}' = '{value[:50]}'")

        return True

    # ── Consolidation Cycle ─────────────────────────────────────

    def consolidate_now(self) -> Dict:
        """Run one consolidation cycle immediately.

        Returns stats about what was done.
        """
        stats = {
            "working_promoted": 0,
            "patterns_extracted": 0,
            "semantic_updated": 0,
            "forgotten": 0,
        }

        try:
            # 1. Promote working → episodic
            stats["working_promoted"] = self._promote_working_to_episodic()

            # 2. Extract patterns from episodic → semantic
            stats["patterns_extracted"], stats["semantic_updated"] = \
                self._extract_semantic_patterns()

            # 3. Forget low-importance memories
            stats["forgotten"] = self._forget_low_importance()

            with self._lock:
                self._cycles_run += 1
                self._total_promoted += stats["working_promoted"]
                self._total_forgotten += stats["forgotten"]

        except Exception as e:
            logger.error(f"MemoryConsolidation: Cycle failed: {e}")

        return stats

    def _promote_working_to_episodic(self) -> int:
        """Promote high-importance working memory to episodic."""
        promoted = 0
        with self._lock:
            to_promote = [
                m for m in self._working_memory
                if m.importance >= self.importance_threshold and not m.consolidated
            ]
            for mem in to_promote:
                mem.memory_type = "episodic"
                mem.memory_id = self._generate_id("ep")
                mem.consolidated = True
                self._episodic_memory.append(mem)
                self._working_memory.remove(mem)
                promoted += 1

        if promoted > 0:
            logger.debug(f"MemoryConsolidation: Promoted {promoted} working → episodic")
        return promoted

    def _extract_semantic_patterns(self) -> tuple:
        """Extract semantic patterns from episodic memory.

        Scans episodic memory for:
        - Repeated topics → strengthen semantic associations
        - Named entities → store as semantic facts
        - Emotional patterns → tag for emotional memory

        Returns (patterns_extracted, semantic_updated).
        """
        patterns = 0
        semantic_updates = 0

        with self._lock:
            # Count topic frequencies
            topic_counts = Counter()
            entity_pairs = defaultdict(set)

            for mem in self._episodic_memory:
                for topic in mem.topics:
                    topic_counts[topic] += 1
                for k, v in mem.entities.items():
                    entity_pairs[k].add(v)

            # Extract patterns from frequently co-occurring topics
            frequent_topics = {t for t, c in topic_counts.most_common() if c >= 3}
            for topic in frequent_topics:
                key = f"frequent_topic:{topic}"
                if key not in self._semantic_memory:
                    self._semantic_memory[key] = ConsolidatedMemory(
                        memory_id=key,
                        content=f"User frequently engages with '{topic}' ({topic_counts[topic]} times)",
                        memory_type="semantic",
                        importance=min(0.9, topic_counts[topic] / 10),
                        topics=[topic],
                        timestamp=time.time(),
                        consolidated=True,
                        source="memory_consolidation",
                    )
                    patterns += 1

            # Extract entities as semantic facts
            for entity_type, values in entity_pairs.items():
                if len(values) >= 2:  # Multiple observations = more reliable
                    # Take most common value
                    value_counts = Counter(values)
                    most_common = value_counts.most_common(1)[0]
                    key = f"entity:{entity_type}"
                    self._semantic_memory[key] = ConsolidatedMemory(
                        memory_id=key,
                        content=f"{entity_type}: {most_common[0]}",
                        memory_type="semantic",
                        importance=min(0.8, most_common[1] / 5),
                        topics=[],
                        entities={entity_type: most_common[0]},
                        timestamp=time.time(),
                        consolidated=True,
                        source="memory_consolidation",
                    )
                    semantic_updates += 1

        return patterns, semantic_updates

    def _forget_low_importance(self) -> int:
        """Forget low-importance, old memories.

        Returns count of forgotten memories.
        """
        forgotten = 0
        now = time.time()
        cutoff = now - (self.forget_threshold_days * 86400)

        with self._lock:
            # Forget from working memory
            self._working_memory = [
                m for m in self._working_memory
                if m.importance >= 0.2 or m.timestamp >= cutoff
            ]

            # Forget from episodic memory
            before = len(self._episodic_memory)
            self._episodic_memory = [
                m for m in self._episodic_memory
                if m.importance >= 0.1 or m.timestamp >= cutoff
            ]
            forgotten = before - len(self._episodic_memory)

        return forgotten

    def _trim_lowest_importance(self, memory_list: list, max_size: int):
        """Trim a memory list to max_size, keeping highest importance."""
        if len(memory_list) <= max_size:
            return
        memory_list.sort(key=lambda m: m.importance, reverse=True)
        del memory_list[max_size:]

    # ── Query ───────────────────────────────────────────────────

    def query(self, query_text: str, memory_types: List[str] = None,
              limit: int = 10) -> List[Dict]:
        """Search across memory types.

        Args:
            query_text: Text to search for.
            memory_types: Types to search ('working', 'episodic', 'semantic').
            limit: Max results.

        Returns:
            List of matching memories as dicts.
        """
        memory_types = memory_types or ["working", "episodic", "semantic"]
        q = query_text.lower()
        results = []

        with self._lock:
            if "working" in memory_types:
                for mem in self._working_memory:
                    if q in mem.content.lower() or any(q in t.lower() for t in mem.topics):
                        results.append(self._to_dict(mem))

            if "episodic" in memory_types:
                for mem in self._episodic_memory:
                    if q in mem.content.lower() or any(q in t.lower() for t in mem.topics):
                        results.append(self._to_dict(mem))

            if "semantic" in memory_types:
                for mem in self._semantic_memory.values():
                    if q in mem.content.lower() or q in mem.memory_id.lower():
                        results.append(self._to_dict(mem))

        results.sort(key=lambda r: r["importance"], reverse=True)
        return results[:limit]

    def recall_semantic(self, key: str) -> Optional[Dict]:
        """Recall a specific semantic memory."""
        with self._lock:
            mem = self._semantic_memory.get(key)
            if mem:
                mem.access_count += 1
                mem.last_accessed = time.time()
                return self._to_dict(mem)
        return None

    # ── Helpers ─────────────────────────────────────────────────

    def _generate_id(self, prefix: str) -> str:
        """Generate a unique memory ID."""
        import uuid
        return f"{prefix}_{uuid.uuid4().hex[:8]}"

    def _to_dict(self, mem: ConsolidatedMemory) -> Dict:
        return {
            "id": mem.memory_id,
            "content": mem.content[:200],
            "type": mem.memory_type,
            "importance": round(mem.importance, 2),
            "access_count": mem.access_count,
            "topics": mem.topics,
            "entities": mem.entities,
            "timestamp": mem.timestamp,
            "consolidated": mem.consolidated,
            "source": mem.source,
        }

    def _run_loop(self):
        """Background loop that runs consolidation periodically."""
        while self._running:
            try:
                time.sleep(self.consolidate_interval)
                if self._running:
                    stats = self.consolidate_now()
                    logger.debug(f"MemoryConsolidation: Cycle done — promoted={stats['working_promoted']}, "
                                 f"patterns={stats['patterns_extracted']}, forgotten={stats['forgotten']}")
            except Exception as e:
                logger.warning(f"MemoryConsolidation: Cycle error: {e}")

    # ── Stats ───────────────────────────────────────────────────

    def get_stats(self) -> dict:
        with self._lock:
            return {
                "cycles_run": self._cycles_run,
                "working_memory_count": len(self._working_memory),
                "episodic_memory_count": len(self._episodic_memory),
                "semantic_memory_count": len(self._semantic_memory),
                "total_promoted": self._total_promoted,
                "total_forgotten": self._total_forgotten,
                "running": self._running,
            }
