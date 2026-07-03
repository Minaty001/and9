"""
AND9 — Context Manager.

Handles context retention, interruption detection, and context
assembly for the Dialogue Manager.

Key responsibilities:
  - Track active context across conversation turns
  - Detect topic switches (interruptions)
  - Detect resume requests
  - Build context summaries for the action planner
  - Maintain conversation coherence

Interruption Detection Logic:
  1. User sends message with intent A while task with intent B is active
  2. If A != B and task B is still waiting for info → flag as interruption
  3. Pause task B, create task A
  4. Link task A as child of task B
  5. On "continue"/"resume" → restore B, pause A if still active
"""

import logging
import re
from typing import Optional

from app.dialogue_manager.working_memory import WorkingMemory, ShortTermMemory

logger = logging.getLogger(__name__)

# Intents that are considered "instant" — no multi-turn needed
_INSTANT_INTENTS = {
    "flashlight", "volume", "wifi", "bluetooth",
    "camera", "home", "go_home",
}

# Intents that are long-running and more likely to be interrupted
_LONG_RUNNING_INTENTS = {
    "youtube", "music", "call", "message",
    "alarm", "timer", "reminder", "search",
    "open_app",
}


class ContextManager:
    """Manages conversation context across turns.

    Detects interruptions, assembles context for the planner,
    and maintains conversation coherence.
    """

    def __init__(self, working_memory: WorkingMemory,
                 short_term_memory: ShortTermMemory):
        self.wm = working_memory
        self.stm = short_term_memory
        self._consecutive_same_intent = 0

    def detect_interruption(self, new_intent: str,
                            active_task_intent: Optional[str]) -> bool:
        """Detect if the user is switching topics (interrupting).

        An interruption is when:
          - There's an active task waiting for info, AND
          - The new intent is different from the active task intent, AND
          - The new intent is not an instant action (flashlight, etc.)

        Args:
            new_intent: The intent of the new message.
            active_task_intent: The intent of the currently active task.

        Returns:
            True if this is an interruption.
        """
        if not active_task_intent:
            return False

        if new_intent == active_task_intent:
            self._consecutive_same_intent += 1
            return False

        # Reset counter on intent change
        self._consecutive_same_intent = 0

        # If active task is still pending/waiting and new intent is different
        if new_intent != active_task_intent:
            # Don't flag interruptions for instant actions
            if new_intent in _INSTANT_INTENTS:
                return False
            # Chat is not an interruption — it's the default
            if new_intent == "chat" and active_task_intent != "chat":
                # User asking a casual question mid-task
                return True
            return True

        return False

    def detect_resume(self, message: str) -> bool:
        """Detect if the user is asking to resume a paused task.

        Checks for explicit resume keywords.
        """
        resume_keywords = [
            r'\b(continue|resume|go on|jari rakho|jaari rakho)\b',
            r'\b(phir se|again|same as before|same thing)\b',
            r'\b(wahi|wahi kaam|waisa hi)\b',
            r'\b(ab continue|ab resume|ab jari)\b',
        ]
        msg_lower = message.lower().strip()
        for pattern in resume_keywords:
            if re.search(pattern, msg_lower):
                return True

        # Very short affirmative messages after context switch signal resume
        if msg_lower in ("yes", "haan", "ha", "hmm", "ok", "okay", "theek hai"):
            # Check if there are paused tasks
            return True

        return False

    def update_context(self, user_message: str, assistant_response: str,
                       intent: str, task_id: str,
                       entities: Optional[dict[str, str]] = None):
        """Update all context stores after a turn.

        Args:
            user_message: The user's input.
            assistant_response: The assistant's reply.
            intent: Detected intent.
            task_id: Active task ID.
            entities: Optional entities extracted.
        """
        # Add to working memory
        self.wm.add_turn(
            user_message=user_message,
            assistant_message=assistant_response,
            intent=intent,
            task_id=task_id,
            entities=entities or {},
        )

        # Update short-term memory with entities
        if entities:
            for key, value in entities.items():
                self.stm.remember(key, value)

        # Always remember last intent for context
        self.stm.remember("last_intent", intent, ttl=60)

        # Store the last action target for reference resolution
        if entities:
            for target_key in ("search_query", "song_name", "app_name",
                                "contact_name", "query"):
                if target_key in entities:
                    self.stm.remember("last_action_target",
                                      entities[target_key], ttl=120)
                    break

        logger.debug("Context updated: intent=%s task=%s entities=%s",
                     intent, task_id, entities)

    def build_context_summary(self, active_task=None,
                              paused_tasks: Optional[list] = None) -> str:
        """Build a natural-language summary of the current context.

        Used for logging and for the conscious brain to understand
        the current dialogue state.

        Args:
            active_task: The currently active task.
            paused_tasks: List of paused tasks.

        Returns:
            A formatted context summary string.
        """
        parts = []

        if active_task:
            task_info = (
                f"Current Task: {active_task.intent} (ID: {active_task.task_id})\n"
                f"Status: {active_task.status.value}\n"
                f"Filled: {active_task.filled_slots}\n"
                f"Missing: {active_task.missing_slots}\n"
            )
            if active_task.waiting_for:
                task_info += f"Waiting for: {active_task.waiting_for}\n"
            parts.append(task_info)

        if paused_tasks:
            paused_info = "Paused Tasks:\n"
            for task in paused_tasks[-3:]:  # Show last 3
                paused_info += (
                    f"  - {task.intent} (ID: {task.task_id}, "
                    f"filled: {len(task.filled_slots)}/{len(task.required_slots)})\n"
                )
            parts.append(paused_info)

        recent_turns = self.wm.get_last_n(5)
        if recent_turns:
            turns_info = "Recent Conversation:\n"
            for t in recent_turns:
                turns_info += f"  User: {t.user_message[:80]}\n"
                turns_info += f"  Assistant: {t.assistant_message[:80]}\n"
            parts.append(turns_info)

        return "\n".join(parts)

    def should_execute(self, active_task) -> bool:
        """Determine if the active task should be executed now.

        Rules:
          1. All required slots must be filled
          2. Status must be READY_TO_EXECUTE
          3. Task must not be paused or cancelled

        Args:
            active_task: The task to check.

        Returns:
            True if execution should proceed.
        """
        from app.dialogue_manager.state_manager import TaskStatus
        if not active_task:
            return False
        if active_task.status == TaskStatus.CANCELLED:
            return False
        if active_task.status == TaskStatus.PAUSED:
            return False
        return len(active_task.missing_slots) == 0

    def get_conversation_summary(self, max_turns: int = 10) -> str:
        """Get a concise summary of the recent conversation.

        Args:
            max_turns: Maximum turns to include.

        Returns:
            A formatted summary string.
        """
        turns = self.wm.get_last_n(max_turns)
        if not turns:
            return "No conversation history."

        lines = []
        for t in turns:
            lines.append(f"User: {t.user_message}")
            lines.append(f"Assistant: {t.assistant_message}")
        return "\n".join(lines)
