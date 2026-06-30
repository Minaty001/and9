"""
app/core/knowledge_graph.py — Entity-relationship knowledge graph.

Stores and retrieves triples (source → relationship → target) in Supabase
with weighted edges for ranking. Used by the memory system for graph-based
context retrieval across all memory types.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


class KnowledgeGraph:
    """Weighted directed graph backed by Supabase `knowledge_graph` table.

    Each edge is a triple: source_entity → relationship → target_entity
    with a weight, types, metadata, and usage tracking.
    """

    def __init__(self, memory):
        self.memory = memory

    # ── CRUD ──────────────────────────────────────────────────────

    def add_triple(
        self,
        source: str,
        relationship: str,
        target: str,
        weight: float = 1.0,
        source_type: str = "concept",
        target_type: str = "concept",
        metadata: Optional[dict] = None,
    ) -> bool:
        """Insert or update a knowledge graph triple.

        If the triple already exists, its weight is increased and
        last_seen / access_count are updated (upsert behavior).
        """
        triple_id = self._find_triple(source, relationship, target)
        if triple_id is not None:
            return self._bump_triple(triple_id, weight)
        return self._insert_triple(source, relationship, target, weight, source_type, target_type, metadata)

    def _find_triple(self, source: str, relationship: str, target: str) -> Optional[int]:
        sb = self.memory._sb
        if not sb:
            return None
        try:
            res = sb.table("knowledge_graph") \
                .select("id") \
                .eq("source_entity", source) \
                .eq("relationship", relationship) \
                .eq("target_entity", target) \
                .limit(1) \
                .execute()
            if res and res.data:
                return res.data[0]["id"]
        except Exception as e:
            logger.debug(f"KG find failed: {e}")
        return None

    def _bump_triple(self, triple_id: int, additional_weight: float = 1.0) -> bool:
        sb = self.memory._sb
        if not sb:
            return False
        try:
            res = sb.table("knowledge_graph") \
                .select("weight, access_count") \
                .eq("id", triple_id) \
                .limit(1) \
                .execute()
            if not res or not res.data:
                return False
            row = res.data[0]
            current_weight = float(row.get("weight") or 0.0)
            current_access = int(row.get("access_count") or 0)
            
            now = datetime.now(timezone.utc).isoformat()
            sb.table("knowledge_graph") \
                .update({
                    "weight": current_weight + additional_weight,
                    "last_seen": now,
                    "access_count": current_access + 1,
                }) \
                .eq("id", triple_id) \
                .execute()
            return True
        except Exception as e:
            logger.debug(f"KG bump failed: {e}")
            return False

    def _insert_triple(self, source: str, relationship: str, target: str,
                       weight: float, source_type: str, target_type: str,
                       metadata: Optional[dict]) -> bool:
        sb = self.memory._sb
        if not sb:
            return False
        try:
            sb.table("knowledge_graph") \
                .insert({
                    "source_entity": source,
                    "relationship": relationship,
                    "target_entity": target,
                    "weight": weight,
                    "source_type": source_type,
                    "target_type": target_type,
                    "metadata": metadata or {},
                }) \
                .execute()
            return True
        except Exception as e:
            logger.debug(f"KG insert failed: {e}")
            return False

    # ── Query ─────────────────────────────────────────────────────

    def get_related(self, entity: str, max_depth: int = 1, limit: int = 20) -> list:
        """Return all triples connected to an entity (outgoing + incoming)."""
        sb = self.memory._sb
        if not sb:
            return []
        results = []
        try:
            out = sb.table("knowledge_graph") \
                .select("*") \
                .eq("source_entity", entity) \
                .order("weight", desc=True) \
                .limit(limit) \
                .execute()
            if out and out.data:
                results.extend(out.data)
        except Exception as e:
            logger.debug(f"KG out query failed: {e}")

        try:
            inc = sb.table("knowledge_graph") \
                .select("*") \
                .eq("target_entity", entity) \
                .order("weight", desc=True) \
                .limit(limit) \
                .execute()
            if inc and inc.data:
                results.extend(inc.data)
        except Exception as e:
            logger.debug(f"KG in query failed: {e}")

        return results[:limit]

    def get_by_relationship(self, relationship: str, limit: int = 20) -> list:
        """Return all triples with a given relationship type."""
        sb = self.memory._sb
        if not sb:
            return []
        try:
            res = sb.table("knowledge_graph") \
                .select("*") \
                .eq("relationship", relationship) \
                .order("weight", desc=True) \
                .limit(limit) \
                .execute()
            return res.data if res and res.data else []
        except Exception as e:
            logger.debug(f"KG relation query failed: {e}")
            return []

    def search(self, keyword: str, limit: int = 20) -> list:
        """Search for triples where source, relationship, or target contains keyword."""
        sb = self.memory._sb
        if not sb:
            return []
        seen, results = set(), []
        try:
            for col in ("source_entity", "relationship", "target_entity"):
                res = sb.table("knowledge_graph") \
                    .select("*") \
                    .ilike(col, f"%{keyword}%") \
                    .order("weight", desc=True) \
                    .limit(limit) \
                    .execute()
                if res and res.data:
                    for r in res.data:
                        if r["id"] not in seen:
                            seen.add(r["id"])
                            results.append(r)
        except Exception as e:
            logger.debug(f"KG search failed: {e}")
        return results[:limit]

    def get_all_entities(self, entity_type: Optional[str] = None) -> list:
        """Return distinct entity names (optionally filtered by type)."""
        sb = self.memory._sb
        if not sb:
            return []
        try:
            query = sb.table("knowledge_graph") \
                .select("source_entity") \
                .order("access_count", desc=True)
            if entity_type:
                query = query.eq("source_type", entity_type)
            res = query.execute()
            entities = set()
            if res and res.data:
                for r in res.data:
                    entities.add(r["source_entity"])
            # Also collect target entities
            query2 = sb.table("knowledge_graph") \
                .select("target_entity") \
                .order("access_count", desc=True)
            if entity_type:
                query2 = query2.eq("target_type", entity_type)
            res2 = query2.execute()
            if res2 and res2.data:
                for r in res2.data:
                    entities.add(r["target_entity"])
            return sorted(entities)
        except Exception as e:
            logger.debug(f"KG get_all_entities failed: {e}")
            return []

    # ── Context Building ──────────────────────────────────────────

    def build_graph_context(self, topic: str, max_relations: int = 15) -> str:
        """Build a human-readable context string from graph relations relevant to a topic.

        This is injected into LLM prompts so the model can leverage
        known entity relationships.
        """
        relations = self.search(topic, limit=max_relations)
        if not relations:
            return ""

        lines = ["\n=== KNOWLEDGE GRAPH CONTEXT ==="]
        for r in relations:
            weight = r.get("weight", 1.0)
            marker = "★" if weight > 2.0 else "•"
            lines.append(
                f"  {marker} {r['source_entity']} → [{r['relationship']}] → {r['target_entity']}"
            )
        return "\n".join(lines)

    # ── Bulk Operations ───────────────────────────────────────────

    def extract_and_store(self, entities: dict) -> int:
        """Automatically extract triples from a flat entity dict and store them.

        Converts {entity_type: value} pairs into triples:
          "User" → [entity_type] → value
          value → "is_a" → entity_type

        Returns count of triples stored.
        """
        count = 0
        for entity_type, value in entities.items():
            if not value or not isinstance(value, str):
                continue
            # User → has_name → "Saif"
            if self.add_triple("User", f"has_{entity_type}", value,
                               weight=0.8, source_type="user", target_type=entity_type):
                count += 1
            # "Saif" → is_a → "name"
            if self.add_triple(value, "is_a", entity_type,
                               weight=0.6, source_type=entity_type, target_type="attribute"):
                count += 1
        return count

    def delete_triple(self, triple_id: int) -> bool:
        """Delete a triple by ID."""
        sb = self.memory._sb
        if not sb:
            return False
        try:
            sb.table("knowledge_graph").delete().eq("id", triple_id).execute()
            return True
        except Exception as e:
            logger.debug(f"KG delete failed: {e}")
            return False
