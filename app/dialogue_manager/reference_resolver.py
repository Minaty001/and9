"""
AND9 — Reference Resolution Engine.

Resolves anaphoric references (pronouns, deixis, and discourse
references) in user messages using conversation context.

Supported resolution types:
  1. Pronouns: it, that, this, them, those, these
  2. Action references: play it, open it, call them, search that
  3. Continuation: continue, resume, go on, same as before
  4. Negation/cancellation: don't, nahi karo, cancel, stop
  5. Deictic references: this one, that one, previous one, the other one
  6. Implicit references: "and" with implied subject from previous turn

Strategy:
  - Uses the WorkingMemory turn buffer and ShortTermMemory entity store
  - Resolves references iteratively using pattern matching
  - Returns the resolved message and metadata about what was resolved
  - Never modifies the original message in-place, always returns a new string
"""

import re
import logging
from typing import Optional

from app.dialogue_manager.working_memory import WorkingMemory, ShortTermMemory

logger = logging.getLogger(__name__)


class ReferenceResolver:
    """Resolves references in user messages using conversation context.

    Uses working memory to find antecedents for pronouns and other
    referring expressions. Returns a resolved message string that
    replaces references with their concrete antecedents.
    """

    # ── Pattern Groups ─────────────────────────────────────────────

    # Patterns that signal a resume/continue request
    RESUME_PATTERNS = [
        re.compile(r'^\s*(continue|resume|go on|jari rakho|jaari rakho|phir se)\s*$', re.IGNORECASE),
        re.compile(r'^\s*(continue|resume|jari rakho)\s+(that|the|us|with)\s', re.IGNORECASE),
        re.compile(r'\b(?:now\s+)?(?:continue|resume)\s+(?:that|the|this|it)\b', re.IGNORECASE),
        re.compile(r'\bnow\s+(?:continue|resume)\b', re.IGNORECASE),
        re.compile(r'\b(same as before|same thing|wahi|wahi kaam)\b', re.IGNORECASE),
        re.compile(r'\b(resume|continue)\s+(?:karo|karein|kar do|kardo)\b', re.IGNORECASE),
    ]

    # Patterns that signal cancellation
    CANCEL_PATTERNS = [
        re.compile(r'\b(?:cancel|stop|abort|halt|cancel karo|band karo|cancel kar do|'
                   r'nahi (?:karna|kar|chahiye)|mat karo|rok do|hua|hoga)\b', re.IGNORECASE),
        re.compile(r"\b(?:don't|dont|do not|dont't)\s+(?:play|want|need|like|karna|karo)\b", re.IGNORECASE),
    ]

    # Pronoun patterns
    IT_PATTERN = re.compile(r'\bit\b', re.IGNORECASE)
    THAT_PATTERN = re.compile(r'\bthat\b', re.IGNORECASE)
    THIS_PATTERN = re.compile(r'\bthis\b', re.IGNORECASE)
    THEM_PATTERN = re.compile(r'\bthem\b', re.IGNORECASE)
    THOSE_PATTERN = re.compile(r'\bthose\b', re.IGNORECASE)
    THESE_PATTERN = re.compile(r'\bthese\b', re.IGNORECASE)

    # Action + reference patterns: "play it", "open it", "call them", etc.
    ACTION_REF_PATTERNS = [
        re.compile(r'\b(play|play karo|bajao|chalao|sunao)\s+(?:that|it|this)\b', re.IGNORECASE),
        re.compile(r'\b(open|kholo|khol)\s+(?:that|it|this|them)\b', re.IGNORECASE),
        re.compile(r'\b(call|phone|dial)\s+(?:them|that person|him|her|us)\b', re.IGNORECASE),
        re.compile(r'\b(message|msg|text|sms)\s+(?:them|him|her|that person)\b', re.IGNORECASE),
        re.compile(r'\b(search|find|dhundh|dhundo|search karo)\s+(?:that|it|this)\b', re.IGNORECASE),
        re.compile(r'\b(set|lagao|daal do)\s+(?:that|it|this)\b', re.IGNORECASE),
    ]

    def __init__(self, working_memory: WorkingMemory,
                 short_term_memory: ShortTermMemory):
        self.wm = working_memory
        self.stm = short_term_memory

    def resolve(self, message: str) -> tuple[str, dict]:
        """Resolve all references in a user message.

        Args:
            message: The raw user message.

        Returns:
            Tuple of (resolved_message, resolution_metadata).
            resolution_metadata contains:
              - resolved: bool — whether any resolution was applied
              - resume_requested: bool
              - cancel_requested: bool
              - resolved_references: list of (reference, antecedent) pairs
              - original_message: str
        """
        original = message.strip()
        if not original:
            return original, {
                "resolved": False,
                "resume_requested": False,
                "cancel_requested": False,
                "resolved_references": [],
                "original_message": original,
            }

        resolved = original
        resolved_refs = []
        resume_requested = self._is_resume_request(original)
        cancel_requested = self._is_cancel_request(original)

        # 1. Resolve "it" → last action target
        if self.IT_PATTERN.search(resolved):
            antecedent = self._resolve_it()
            if antecedent:
                resolved = self.IT_PATTERN.sub(antecedent, resolved, count=1)
                resolved_refs.append(("it", antecedent))

        # 2. Resolve "that" → last mentioned entity
        if self.THAT_PATTERN.search(resolved):
            antecedent = self._resolve_that()
            if antecedent:
                resolved = self.THAT_PATTERN.sub(antecedent, resolved, count=1)
                resolved_refs.append(("that", antecedent))

        # 3. Resolve "this" → current context item
        if self.THIS_PATTERN.search(resolved):
            antecedent = self._resolve_this()
            if antecedent:
                resolved = self.THIS_PATTERN.sub(antecedent, resolved, count=1)
                resolved_refs.append(("this", antecedent))

        # 4. Resolve "them"/"those"/"these"
        if self.THEM_PATTERN.search(resolved):
            antecedent = self._resolve_them()
            if antecedent:
                resolved = self.THEM_PATTERN.sub(antecedent, resolved, count=1)
                resolved_refs.append(("them", antecedent))

        if self.THOSE_PATTERN.search(resolved):
            antecedent = self._resolve_them()  # same logic
            if antecedent:
                resolved = self.THOSE_PATTERN.sub(antecedent, resolved, count=1)
                resolved_refs.append(("those", antecedent))

        if self.THESE_PATTERN.search(resolved):
            antecedent = self._resolve_this()
            if antecedent:
                resolved = self.THESE_PATTERN.sub(antecedent, resolved, count=1)
                resolved_refs.append(("these", antecedent))

        # 5. Resolve action + reference patterns (e.g., "play it")
        resolved, action_refs = self._resolve_action_references(resolved)
        resolved_refs.extend(action_refs)

        logger.debug("Reference resolution: '%s' → '%s' (refs=%s)",
                     original, resolved, resolved_refs)

        return resolved, {
            "resolved": len(resolved_refs) > 0,
            "resume_requested": resume_requested,
            "cancel_requested": cancel_requested,
            "resolved_references": resolved_refs,
            "original_message": original,
        }

    def _is_resume_request(self, message: str) -> bool:
        """Check if the message is a resume/continue request."""
        return any(p.match(message) for p in self.RESUME_PATTERNS)

    def _is_cancel_request(self, message: str) -> bool:
        """Check if the message is a cancel/stop request."""
        return any(p.search(message) for p in self.CANCEL_PATTERNS)

    def _resolve_it(self) -> Optional[str]:
        """Resolve 'it' — the last action's target entity.

        Priority:
          1. ShortTermMemory: last_action_target
          2. WorkingMemory: last turn's entity
          3. WorkingMemory: last mentioned content
        """
        # Check STM first
        target = self.stm.recall("last_action_target")
        if target:
            return str(target)

        # Check working memory for last entity
        entities = self.wm.get_all_entities()
        for key in ["search_query", "song_name", "app_name", "contact_name",
                     "message_text", "query"]:
            if key in entities:
                return str(entities[key])

        # Check last turn for any meaningful content
        last_msg = self.wm.get_last_user_message()
        if last_msg:
            # Extract the last noun phrase (simple heuristic)
            words = last_msg.split()
            if words:
                return words[-1]  # Last word as fallback

        return None

    def _resolve_that(self) -> Optional[str]:
        """Resolve 'that' — previously mentioned entity.

        Similar to 'it' but prefers the entity before the most recent one.
        """
        # Check STM for last_mentioned
        target = self.stm.recall("last_referenced")
        if target:
            return str(target)

        # Fall back to 'it' resolution
        return self._resolve_it()

    def _resolve_this(self) -> Optional[str]:
        """Resolve 'this' — current context item.

        Returns the current task's primary entity if available.
        """
        target = self.stm.recall("current_entity")
        if target:
            return str(target)
        return self._resolve_it()

    def _resolve_them(self) -> Optional[str]:
        """Resolve 'them' — last plural reference.

        Returns the last mentioned contact or group.
        """
        target = self.stm.recall("last_contact")
        if target:
            return str(target)

        # Check for contact in entities
        entities = self.wm.get_all_entities()
        for key in ["contact_name"]:
            if key in entities:
                return str(entities[key])
        return None

    def _resolve_action_references(self, message: str) -> tuple[str, list]:
        """Resolve action-reference combos like 'play it', 'open it'.

        These are replaced with explicit action + entity descriptions.

        Returns:
            Tuple of (modified_message, list_of_(reference, antecedent)).
        """
        resolved_refs = []
        for pattern in self.ACTION_REF_PATTERNS:
            if pattern.search(message):
                antecedent = self._resolve_it()
                if antecedent:
                    # Replace the reference with the concrete entity
                    # e.g., "play it" → "play <song_name>"
                    replacement_fn = lambda m, ant=antecedent: ant  # noqa: E731
                    # Simple: replace full pattern match with just the antecedent
                    message = pattern.sub(antecedent, message)
                    resolved_refs.append((pattern.pattern[:20], antecedent))
        return message, resolved_refs

    # ── Convenience Methods ────────────────────────────────────────

    def is_resume(self, message: str) -> bool:
        """Quick check if message is a resume request."""
        return self._is_resume_request(message)

    def is_cancel(self, message: str) -> bool:
        """Quick check if message is a cancel request."""
        return self._is_cancel_request(message)

    def extract_cancel_target(self, message: str) -> Optional[str]:
        """Try to extract what the user wants to cancel.

        E.g., "cancel music" → "music", "stop the alarm" → "alarm",
        "don't play music" → "music".
        """
        cancel_patterns = [
            re.compile(r'(?:cancel|stop|band karo|nahi)\s+(?:the\s+)?(\w+)', re.IGNORECASE),
            re.compile(r'(\w+)\s+(?:cancel|stop|band karo|mat karo)', re.IGNORECASE),
            re.compile(r"(?:don't|dont|do not)\s+(?:\w+\s+)?(\w+)", re.IGNORECASE),
        ]
        for pattern in cancel_patterns:
            m = pattern.search(message)
            if m:
                target = m.group(1).lower().strip()
                # Map to known intents
                intent_map = {
                    "song": "music",
                    "music": "music",
                    "gaana": "music",
                    "youtube": "youtube",
                    "video": "youtube",
                    "alarm": "alarm",
                    "timer": "timer",
                    "reminder": "reminder",
                    "remind": "reminder",
                    "call": "call",
                    "message": "message",
                    "search": "search",
                    "app": "open_app",
                }
                return intent_map.get(target, target)
        return None
