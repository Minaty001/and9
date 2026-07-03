"""
AND9 — Slot Filling Engine.

Manages the process of collecting required and optional slot values
from the user across multiple conversation turns.

Key behaviors:
  - Asks for exactly ONE missing required slot at a time
  - Never asks for the same slot twice
  - Can fill optional slots if user volunteers the information
  - Tracks what the assistant is currently waiting for
  - Natural, short, context-aware questions
  - Validates slot values when a validation function is defined

Flow per turn:
  1. Receive user message
  2. Try to fill the 'waiting_for' slot from the message
  3. If that slot is already filled, try to auto-classify the message
     into any remaining missing slot
  4. Determine next missing slot
  5. Return the question for that slot (or None if all filled)
"""

import re
import logging
from typing import Optional

from app.dialogue_manager.intent_definitions import (
    get_intent_definition,
    IntentDefinition,
    SlotDefinition,
)

logger = logging.getLogger(__name__)

# ── Simple expression classifiers ─────────────────────────────────
# These help determine what kind of information the user provided
# when the assistant is waiting for a specific slot.

_TIME_PATTERN = re.compile(
    r'^\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM|baje)?\s*$'
    r'|^\d+\s*(?:second|sec|minute|min|hour|hr|ghanta|ghante)s?\s*$'
    r'|^(?:after|in|within)\s+\d+\s*(?:second|sec|minute|min|hour|hr)s?\s*$'
    r'|^\d{1,2}:\d{2}\s*(?:am|pm)?\s*$'
)

_ON_OFF_PATTERN = re.compile(r'^\s*(on|off|chaalu|band|kar(?:do|o)?)\s*$', re.IGNORECASE)

_UP_DOWN_PATTERN = re.compile(r'^\s*(up|down|badhao|kam|mute|max|full)\s*$', re.IGNORECASE)

_CONTENT_TYPE_PATTERN = re.compile(
    r'\b(song|gaana|gana|music|video|playlist|album|movie|film)\b',
    re.IGNORECASE
)

_DURATION_PATTERN = re.compile(
    r'^(\d+)\s*(?:second|sec|minute|min|hour|hr|ghanta|ghante)s?\s*$',
    re.IGNORECASE
)


class SlotFiller:
    """Slot-filling engine for multi-turn dialogue.

    Operates on a TaskState object, determining which slot to ask for
    next and classifying user responses into the appropriate slot.
    """

    def __init__(self):
        self._slot_classifiers = {
            "state": self._classify_on_off,
            "action": self._classify_up_down,
            "content_type": self._classify_content_type,
            "duration_seconds": self._classify_duration,
            "hour": self._classify_time,
            "minute": self._classify_time,
            "trigger_at": self._classify_reminder_time,
            "app_name": self._classify_app_name,
            "contact_name": self._classify_contact_name,
        }

    def get_missing_required_slots(self, task_state) -> list[str]:
        """Get list of required slot names that are not yet filled."""
        if not task_state or not task_state.required_slots:
            return []
        filled = set(task_state.filled_slots.keys())
        return [s for s in task_state.required_slots if s not in filled]

    def get_missing_optional_slots(self, task_state) -> list[str]:
        """Get list of optional slot names that are not yet filled."""
        if not task_state or not task_state.optional_slots:
            return []
        filled = set(task_state.filled_slots.keys())
        return [s for s in task_state.optional_slots if s not in filled]

    def all_required_filled(self, task_state) -> bool:
        """Check if all required slots are filled."""
        return len(self.get_missing_required_slots(task_state)) == 0

    def get_next_question(self, task_state) -> Optional[str]:
        """Get the question for the next missing required slot.

        Returns None if all required slots are filled (ready to execute).
        """
        if self.all_required_filled(task_state):
            return None

        intent_def = get_intent_definition(task_state.intent)
        if not intent_def:
            return None

        # Find the first missing required slot
        filled = set(task_state.filled_slots.keys())
        for slot_def in intent_def.required_slots:
            if slot_def.name not in filled:
                return slot_def.question

        return None

    def get_waiting_for(self, task_state) -> Optional[str]:
        """Get the name of the slot the assistant is currently waiting for."""
        return task_state.waiting_for

    def determine_waiting_for(self, task_state) -> Optional[str]:
        """Determine which slot the assistant should wait for next.

        Updates task_state.waiting_for and returns the slot name.
        """
        missing = self.get_missing_required_slots(task_state)
        if not missing:
            task_state.waiting_for = None
            return None

        # If we're already waiting for a slot that's still missing, keep it
        if task_state.waiting_for and task_state.waiting_for in missing:
            return task_state.waiting_for

        # Move to the next missing slot
        next_slot = missing[0]
        task_state.waiting_for = next_slot
        return next_slot

    def fill_slot(self, task_state, slot_name: str, value: str) -> bool:
        """Fill a specific slot with a value.

        Args:
            task_state: The task state to update.
            slot_name: Name of the slot to fill.
            value: The value to store.

        Returns:
            True if the slot was filled, False if already filled.
        """
        if slot_name in task_state.filled_slots:
            logger.debug("Slot '%s' already filled with '%s', ignoring new value '%s'",
                         slot_name, task_state.filled_slots[slot_name], value)
            return False

        task_state.filled_slots[slot_name] = value.strip() if isinstance(value, str) else value

        # Clear waiting_for if we just filled the slot we were waiting for
        if task_state.waiting_for == slot_name:
            task_state.waiting_for = None

        logger.info("Filled slot '%s' = '%s' (task=%s)", slot_name, value, task_state.task_id)
        return True

    def try_fill_from_message(self, task_state, message: str) -> tuple[bool, str]:
        """Try to fill the currently-waiting slot from a user message.

        Args:
            task_state: Current task state with waiting_for set.
            message: The user's message.

        Returns:
            Tuple of (filled_any, slot_name_or_description).
        """
        message = message.strip()
        if not message:
            return False, ""

        # First, check if we're waiting for a specific slot
        waiting_for = self.determine_waiting_for(task_state)

        if waiting_for:
            # Try to fill the slot we're waiting for
            classifier = self._slot_classifiers.get(waiting_for, self._default_classifier)
            value = classifier(message) if callable(classifier) else message

            if value is not None and str(value).strip():
                self.fill_slot(task_state, waiting_for, str(value))
                return True, waiting_for

            # If the value didn't match the slot we're waiting for,
            # try all missing slots as a fallback
            filled = self._try_auto_classify(task_state, message)
            if filled:
                return True, filled

            return False, waiting_for

        # No waiting_for slot — try auto-classify
        filled = self._try_auto_classify(task_state, message)
        if filled:
            return True, filled

        return False, ""

    def _try_auto_classify(self, task_state, message: str) -> Optional[str]:
        """Try to auto-classify a message into any missing slot.

        Returns the name of the slot that was filled, or None.
        """
        missing_req = self.get_missing_required_slots(task_state)

        for slot_name in missing_req:
            classifier = self._slot_classifiers.get(slot_name, self._default_classifier)
            try:
                value = classifier(message) if callable(classifier) else message
            except Exception:
                value = None

            if value is not None and str(value).strip():
                self.fill_slot(task_state, slot_name, str(value))
                return slot_name

        # Try optional slots
        missing_opt = self.get_missing_optional_slots(task_state)
        for slot_name in missing_opt:
            classifier = self._slot_classifiers.get(slot_name, self._default_classifier)
            try:
                value = classifier(message) if callable(classifier) else message
            except Exception:
                value = None

            if value is not None and str(value).strip():
                self.fill_slot(task_state, slot_name, str(value))
                return slot_name

        return None

    # ── Slot Classifiers ──────────────────────────────────────────

    @staticmethod
    def _default_classifier(message: str) -> Optional[str]:
        """Default: use the entire message as the value."""
        cleaned = message.strip().strip('.,!?')
        return cleaned if cleaned else None

    @staticmethod
    def _classify_on_off(message: str) -> Optional[str]:
        """Classify on/off state from message."""
        m = message.lower().strip()
        if _ON_OFF_PATTERN.match(m):
            if m in ("on", "chaalu", "karo", "kardo"):
                return "on"
            return "off"
        # Check for common expressions
        if re.search(r'\b(on|chaalu|jala|start)\b', m):
            return "on"
        if re.search(r'\b(off|band|bujha|stop|close)\b', m):
            return "off"
        return None

    @staticmethod
    def _classify_up_down(message: str) -> Optional[str]:
        """Classify volume/control action from message."""
        m = message.lower().strip()
        if _UP_DOWN_PATTERN.match(m):
            return m
        if re.search(r'\b(up|badhao|badha|increase|upar)\b', m):
            return "up"
        if re.search(r'\b(down|kam|karo|niche|decrease|low)\b', m):
            return "down"
        if re.search(r'\b(mute|chup|silent|quiet)\b', m):
            return "mute"
        if re.search(r'\b(max|full|highest|jordaar)\b', m):
            return "max"
        return None

    @staticmethod
    def _classify_content_type(message: str) -> Optional[str]:
        """Classify content type (song/video/playlist)."""
        m = message.lower().strip()
        if _CONTENT_TYPE_PATTERN.search(m):
            if re.search(r'\b(song|gaana|gana|music)\b', m):
                return "song"
            if re.search(r'\b(video|movie|film)\b', m):
                return "video"
            if re.search(r'\b(playlist|album)\b', m):
                return "playlist"
        return message  # Return as-is if ambiguous

    @staticmethod
    def _classify_duration(message: str) -> Optional[str]:
        """Classify duration expression and convert to seconds."""
        m = message.lower().strip()
        match = _DURATION_PATTERN.match(m)
        if match:
            number = int(match.group(1))
            unit = match.group(2).lower()
            if unit in ("second", "sec"):
                return str(number)
            elif unit in ("minute", "min"):
                return str(number * 60)
            elif unit in ("hour", "hr", "ghanta", "ghante"):
                return str(number * 3600)
        # Just a number? Assume minutes
        if re.match(r'^\d+$', m):
            return str(int(m) * 60)
        return m  # Let the parser handle it downstream

    @staticmethod
    def _classify_time(message: str) -> Optional[str]:
        """Classify time expression."""
        m = message.strip()
        if _TIME_PATTERN.match(m):
            return m
        return None

    @staticmethod
    def _classify_reminder_time(message: str) -> Optional[str]:
        """Classify reminder time (more flexible than alarm time)."""
        m = message.strip()
        if not m:
            return None
        # Accept any reasonable time expression
        if re.search(r'\d', m):
            return m
        return None

    @staticmethod
    def _classify_app_name(message: str) -> Optional[str]:
        """Classify app name — reject generic command phrases.

        Filters out messages like "open an app", "the app", etc.
        that are intent triggers rather than specific app names.
        """
        msg = message.strip().strip('.,!?')
        if not msg:
            return None
        lower = msg.lower()
        # Reject generic non-specific phrases
        generic = {
            'an app', 'the app', 'some app', 'a app', 'an application',
            'app', 'open', 'open an app', 'open the app', 'open a app',
            'launch', 'start', 'open some app', 'open something',
            'kholo', 'khol', 'khol do', 'kholo app', 'kholo ek app',
            'ek app', 'koi app', 'koi bhi app',
        }
        if lower.strip() in generic:
            return None
        # If message is very short (= 1 word) and not a generic word, accept it
        words = lower.split()
        if len(words) <= 3 and not any(w in generic for w in words):
            return msg
        # Longer messages might contain the app name but also command words
        # Try to strip leading command words
        command_prefixes = ('open', 'kholo', 'khol', 'launch', 'start', 'run')
        for prefix in command_prefixes:
            if lower.startswith(prefix):
                rest = msg[len(prefix):].strip().lstrip()
                if rest and rest.lower() not in generic:
                    return rest
        return msg if len(words) <= 5 else None

    @staticmethod
    def _classify_contact_name(message: str) -> Optional[str]:
        """Classify contact name — reject generic command phrases."""
        msg = message.strip().strip('.,!?')
        if not msg:
            return None
        lower = msg.lower()
        generic = {
            'call', 'someone', 'kisi ko', 'koi', 'kise',
            'call someone', 'call karo', 'phone karo',
            'message', 'msg', 'text', 'sms',
            'message someone', 'msg karo', 'text someone',
        }
        if lower.strip() in generic:
            return None
        # Strip leading command words
        command_prefixes = ('call', 'message', 'text', 'sms', 'msg', 'phone', 'dial')
        for prefix in command_prefixes:
            if lower.startswith(prefix):
                rest = msg[len(prefix):].strip().lstrip()
                if rest and rest.lower() not in generic:
                    return rest
        return msg

    def validate_slot_value(self, slot_name: str, candidate_value: str,
                             original_message: str) -> Optional[str]:
        """Validate a slot value from detected params against the slot classifier.

        For slots with a specific classifier, runs the classifier on the
        candidate value to verify it was not spuriously extracted.
        Also checks very short values against a generic-words list.
        For slots without a classifier, trusts the intent router.

        Args:
            slot_name: The name of the slot.
            candidate_value: The value extracted by the intent router.
            original_message: The full user message for context.

        Returns:
            The validated value, or None if the value should be rejected.
        """
        val = str(candidate_value).strip()
        if not val:
            return None

        # For very short values (< 3 chars), check against common filler words
        COMMON_FILLER = {
            'a', 'an', 'the', 'it', 'is', 'to', 'of', 'in', 'on', 'at',
            'by', 'for', 'and', 'or', 'up', 'do', 'no', 'go',
        }
        if len(val) <= 3 and val.lower() in COMMON_FILLER:
            # Still accept if the value appears as a distinctive part of the message
            # (e.g., "7 AM" → hour=7, where "7" is not a filler word)
            return None

        # If there's a specific classifier for this slot, run it on the value
        classifier = self._slot_classifiers.get(slot_name)
        if classifier is not None and callable(classifier):
            classifier_result = classifier(val)
            if classifier_result is None:
                return None
            return classifier_result

        # No specific classifier — trust the intent router's extraction
        return val

    def get_formatted_response(self, task_state, slot_name: str, value: str) -> str:
        """Generate a natural confirmation response for a filled slot.

        Args:
            task_state: The task state.
            slot_name: Name of the slot that was filled.
            value: The value provided.

        Returns:
            A confirmation string, or empty string if no confirmation needed.
        """
        confirmations = {
            "app_name": f"OK, {value}",
            "search_query": f"'{value}' — achha!",
            "song_name": f"'{value}' — accha gaana hai!",
            "contact_name": f"OK, {value} ko",
            "message_text": f"'{value}' — likh diya!",
            "content_type": f"OK, {value}",
            "hour": f"{value} baje",
            "minute": f"{value} minute",
            "label": f"'{value}' — note kar liya!",
            "duration_seconds": f"{value} seconds ka timer",
            "trigger_at": f"{value} — yaad rahega!",
            "state": f"{value}",
            "action": f"{value}",
            "query": f"'{value}' — dhundhte hain!",
            "artist": f"'{value}' — achha choice!",
            "language": f"OK, {value}",
        }
        return confirmations.get(slot_name, f"'{value}' — theek hai!")

    def format_success_message(self, task_state) -> str:
        """Format the success message for a completed task.

        Fills placeholders in the intent definition's success_message
        with the actual slot values.
        """
        intent_def = get_intent_definition(task_state.intent)
        if not intent_def:
            return "Done! ✅"

        msg = intent_def.success_message
        try:
            msg = msg.format(**task_state.filled_slots)
        except KeyError:
            pass
        return msg
