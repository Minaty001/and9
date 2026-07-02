"""
AND9 — Advanced Multi-Turn Dialogue Manager.

Production-quality dialogue engine with:
  - Intent detection with slot definitions
  - Slot-filling (one question at a time)
  - Dialogue State Tracking (DST)
  - Multi-task management
  - Working memory (short-term, active, entity memory)
  - Context retention & interruption handling
  - Reference resolution (pronouns, "it", "continue", etc.)
  - Action planning & execution gating

Usage:
    from app.and9.dialogue_manager import DialogueManager

    dm = DialogueManager()
    result = dm.process("Play a song")
    # → {"response": "Which song would you like to hear?", ...}
    result = dm.process("Tum Hi Ho")
    # → {"response": "Playing 'Tum Hi Ho' on YouTube.", ..., "executed": True}

Public API:
    DialogueManager       → Main entry point
    DialogueConfig        → Configuration dataclass
    TaskState             → Per-task state dataclass
    TaskStatus            → Enum of possible task states
    SlotDefinition        → Slot definition with validation
    ExecutionPlan         → Action execution plan
"""

from app.and9.dialogue_manager.dialogue_manager import DialogueManager
from app.and9.dialogue_manager.intent_definitions import (
    IntentDefinition,
    SlotDefinition,
    INTENT_DEFINITIONS,
    get_intent_definition,
)
from app.and9.dialogue_manager.state_manager import TaskState, TaskStatus
from app.and9.dialogue_manager.action_planner import ExecutionPlan
from app.and9.dialogue_manager.working_memory import DialogueConfig

__all__ = [
    "DialogueManager",
    "DialogueConfig",
    "TaskState",
    "TaskStatus",
    "SlotDefinition",
    "IntentDefinition",
    "INTENT_DEFINITIONS",
    "get_intent_definition",
    "ExecutionPlan",
]
