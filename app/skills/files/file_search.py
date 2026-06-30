"""
File Search Engine.

Index and search files by content/name/metadata.
Supports document indexing with MIME-based metadata and document-specific search.
"""

from __future__ import annotations

import re
import time
import os
import logging
from typing import Any, Dict, List, Optional, Set
from collections import defaultdict

from .virtual_fs import FileItem

logger = logging.getLogger(__name__)


DOCUMENT_MIME_PREFIXES: Set[str] = {
    "text/", "application/json", "application/xml", "application/x-yaml",
    "application/javascript", "application/pdf",
}


class FileSearchEngine:
    """Search engine for indexing and finding files.

    Supports both general file search and document-specific search with
    MIME-based document type metadata.

    Usage:
        engine = FileSearchEngine()
        engine.index_file(item, "content")
        engine.index_document(item, "document text content")
        results = engine.search("query")
        doc_results = engine.search_documents("query", "txt")
    """

    def __init__(self):
        self._name_index: Dict[str, Set[str]] = defaultdict(set)
        self._content_index: Dict[str, Set[str]] = defaultdict(set)
        self._tag_index: Dict[str, Set[str]] = defaultdict(set)
        self._file_map: Dict[str, FileItem] = {}
        self._content_map: Dict[str, str] = {}
        self._indexed_count = 0

        self._document_index: Dict[str, Set[str]] = defaultdict(set)
        self._document_metadata: Dict[str, Dict[str, Any]] = {}
        self._document_types: Dict[str, Set[str]] = defaultdict(set)
        self._indexed_document_count = 0

    def index_file(self, path: str, item: FileItem, content: str = "") -> bool:
        self._file_map[path] = item
        if content:
            self._content_map[path] = content

        name = item.name.lower()
        for token in re.findall(r'\w+', name):
            self._name_index[token].add(path)

        if content:
            for token in re.findall(r'\w+', content.lower()):
                self._content_index[token].add(path)

        for tag in item.tags:
            self._tag_index[tag.lower()].add(path)

        self._indexed_count += 1
        return True

    def search(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        if not query.strip():
            return self._list_all(filters)

        tokens = re.findall(r'\w+', query.lower())
        matched_paths: Optional[Set[str]] = None

        for token in tokens:
            name_matches = self._name_index.get(token, set())
            content_matches = self._content_index.get(token, set())
            tag_matches = self._tag_index.get(token, set())
            combined = name_matches | content_matches | tag_matches

            if matched_paths is None:
                matched_paths = combined
            else:
                matched_paths &= combined

        if matched_paths is None:
            return []

        results = []
        for path in matched_paths:
            item = self._file_map.get(path)
            if not item:
                continue
            if filters and not self._matches_filters(item, filters):
                continue
            results.append({
                "path": path, "name": item.name, "file_type": item.file_type,
                "extension": item.extension, "size_bytes": item.size_bytes,
                "mime_type": item.mime_type, "score": self._compute_score(path, tokens),
            })

        results.sort(key=lambda r: r["score"], reverse=True)
        return results

    def reindex(self) -> int:
        count = self._indexed_count
        self._name_index.clear()
        self._content_index.clear()
        self._tag_index.clear()
        self._file_map.clear()
        self._content_map.clear()
        self._indexed_count = 0
        self._document_index.clear()
        self._document_metadata.clear()
        self._document_types.clear()
        self._indexed_document_count = 0
        return count

    # ── Document Indexing ───────────────────────────────────────────────

    def index_document(self, file_item: FileItem, content: str) -> bool:
        path = file_item.path
        mime_type = file_item.mime_type or "application/octet-stream"

        doc_type = "unknown"
        for prefix in sorted(DOCUMENT_MIME_PREFIXES, key=len, reverse=True):
            if mime_type.startswith(prefix.rstrip("*")):
                doc_type = prefix.rstrip("/").replace("/", "_")
                break

        ext = (file_item.extension or "").lower().lstrip(".")
        if ext:
            doc_type = ext

        word_count = len(re.findall(r'\w+', content)) if content else 0

        self._document_metadata[path] = {
            "path": path, "mime_type": mime_type, "document_type": doc_type,
            "word_count": word_count, "char_count": len(content) if content else 0,
            "extension": file_item.extension or "", "indexed_at": time.time(),
        }

        if content:
            for token in re.findall(r'\w+', content.lower()):
                self._document_index[token].add(path)

        self._document_types[doc_type].add(path)
        self._indexed_document_count += 1
        logger.debug("Indexed document: %s (type=%s, words=%d)", path, doc_type, word_count)
        return True

    def search_documents(self, query: str, document_type: Optional[str] = None) -> List[Dict[str, Any]]:
        if not query.strip():
            return self._list_documents(document_type)

        tokens = re.findall(r'\w+', query.lower())
        matched_paths: Optional[Set[str]] = None

        for token in tokens:
            doc_matches = self._document_index.get(token, set())
            name_matches = self._name_index.get(token, set())
            content_matches = self._content_index.get(token, set())
            combined = doc_matches | name_matches | content_matches

            if matched_paths is None:
                matched_paths = combined
            else:
                matched_paths &= combined

        if matched_paths is None:
            return []

        results = []
        for path in matched_paths:
            if document_type and path not in self._document_types.get(document_type, set()):
                continue
            item = self._file_map.get(path)
            meta = self._document_metadata.get(path, {})
            results.append({
                "path": path, "name": item.name if item else os.path.basename(path),
                "mime_type": meta.get("mime_type", ""),
                "document_type": meta.get("document_type", ""),
                "word_count": meta.get("word_count", 0),
                "char_count": meta.get("char_count", 0),
                "score": self._compute_score(path, tokens),
            })

        results.sort(key=lambda r: r["score"], reverse=True)
        return results

    def reindex_documents(self) -> int:
        count = self._indexed_document_count
        self._document_index.clear()
        self._document_metadata.clear()
        self._document_types.clear()
        self._indexed_document_count = 0
        for path, content in self._content_map.items():
            item = self._file_map.get(path)
            if item:
                self.index_document(item, content)
        reindexed = self._indexed_document_count
        logger.info("Re-indexed %d documents (cleared %d)", reindexed, count)
        return count

    def get_index_stats(self) -> Dict[str, Any]:
        return {
            "indexed_files": self._indexed_count,
            "name_index_terms": len(self._name_index),
            "content_index_terms": len(self._content_index),
            "tag_index_terms": len(self._tag_index),
            "total_file_map_size": len(self._file_map),
            "indexed_documents": self._indexed_document_count,
            "document_index_terms": len(self._document_index),
            "document_types": dict((k, len(v)) for k, v in self._document_types.items()),
        }

    def _matches_filters(self, item: FileItem, filters: Dict[str, Any]) -> bool:
        for key, value in filters.items():
            if key == "file_type" and item.file_type != value:
                return False
            if key == "extension" and item.extension != value:
                return False
            if key == "mime_type" and value not in item.mime_type:
                return False
            if key == "min_size" and item.size_bytes < value:
                return False
            if key == "max_size" and item.size_bytes > value:
                return False
            if key == "is_hidden" and item.is_hidden != value:
                return False
        return True

    def _compute_score(self, path: str, tokens: List[str]) -> int:
        name = path.lower()
        score = 0
        for token in tokens:
            if token in self._name_index and path in self._name_index[token]:
                score += 10
            if token in self._content_index and path in self._content_index[token]:
                score += 2
            if token in self._tag_index and path in self._tag_index[token]:
                score += 5
        return score

    def _list_all(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        results = []
        for path, item in self._file_map.items():
            if filters and not self._matches_filters(item, filters):
                continue
            results.append({
                "path": path, "name": item.name, "file_type": item.file_type,
                "extension": item.extension, "size_bytes": item.size_bytes,
                "mime_type": item.mime_type, "score": 0,
            })
        return results

    def _list_documents(self, document_type: Optional[str] = None) -> List[Dict[str, Any]]:
        results = []
        for path, meta in self._document_metadata.items():
            if document_type and meta.get("document_type") != document_type:
                continue
            results.append({
                "path": path, "name": os.path.basename(path),
                "mime_type": meta.get("mime_type", ""),
                "document_type": meta.get("document_type", ""),
                "word_count": meta.get("word_count", 0),
                "char_count": meta.get("char_count", 0),
                "score": 0,
            })
        return results
