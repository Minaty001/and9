# Phase 27: Knowledge Base

## Purpose
Structured Q&A knowledge with fast retrieval, tagging, confidence scoring, import/export, and auto-linking. `KnowledgeStore` provides in-memory storage with tag and category indexing, substring/word search, and LRU-style eviction. `KnowledgeBase` is the high-level API with query execution, related-entry discovery, bulk import/export, and automatic linking between entries that share tags.

## Architecture
```
KnowledgeBase
  ├── add_knowledge(question, answer, category, tags, source, confidence) → KnowledgeEntry
  ├── query(KnowledgeQuery) → KnowledgeResult
  ├── find_related(entry_id) → List[KnowledgeEntry]
  ├── import_from_dict(data) → int
  ├── export_to_dict() → List[Dict]
  ├── bulk_add(entries) → int
  ├── get_stats() → dict
  └── _auto_link(entry) — link entries with shared tags

KnowledgeStore
  ├── add(entry) / get(id) / update(id) / delete(id)
  ├── search(query, min_confidence, max_results) → List[KnowledgeEntry]
  ├── get_by_tag(tag) / get_by_category(category)
  ├── list_all() / count() / clear()
  └── Internal: tag_index, category_index

Models: KnowledgeEntry, KnowledgeQuery, KnowledgeResult
```

## Code
```python
class KnowledgeStore:
    def add(self, entry: KnowledgeEntry) -> KnowledgeEntry:
        if len(self._entries) >= self._max_entries:
            oldest = min(self._entries.values(), key=lambda e: e.access_count)
            self.delete(oldest.id)
        self._entries[entry.id] = entry
        self._index_entry(entry)
        return entry

    def search(self, query, min_confidence=0.0, max_results=10) -> List[KnowledgeEntry]:
        scored = []
        for entry in self._entries.values():
            if entry.confidence < min_confidence: continue
            score = 0.0
            entry_text = (entry.question + " " + entry.answer).lower()
            if query.lower() in entry_text: score += 10.0
            word_matches = sum(1 for w in query.lower().split() if w in entry_text)
            if word_matches > 0: score += word_matches * 2.0
            if score > 0: scored.append((score, entry))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored[:max_results]]

class KnowledgeBase:
    def add_knowledge(self, question, answer, category="general", **kw) -> KnowledgeEntry:
        entry = KnowledgeEntry(id=uuid.uuid4().hex[:12], question=question, answer=answer, category=category, **kw)
        if self._enable_auto_linking: self._auto_link(entry)
        self.store.add(entry)
        return entry

    def query(self, query_obj: KnowledgeQuery) -> KnowledgeResult:
        t0 = time.perf_counter()
        results = self.store.search(query=query_obj.query, min_confidence=query_obj.min_confidence)
        elapsed = (time.perf_counter() - t0) * 1000
        return KnowledgeResult(entries=results, query=query_obj.query, total_found=len(results), search_time_ms=round(elapsed, 2))
```

## Location
`app/memory/semantic/knowledge_base.py` — knowledge base, store, models, query/retrieve logic
