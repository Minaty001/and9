"""
AND9 — Personal Android AI Operating System.

Multi-brain cognitive architecture with centralized routing.

Refactored structure:
  - brain/orchestrator.py  → Main processing pipeline
  - router/                → Normalizer + Intent detection
  - intents/               → Parameter extraction per intent type
  - actions/               → Action execution per action type
  - android/               → Action registry + Android executor
  - contacts/              → Contact resolution
  - apps/                  → Package resolution
  - media/                 → YouTube handler
  - alarms/timers/reminders/ → Time-based action managers
  - core/                  → Logger, config, constants

Public API:
    AND9           → Main entry point (process, get_stats)
    BrainType      → REFLEX, SUBCONSCIOUS, CONSCIOUS
    IntentType     → 20 intent categories
    BrainResult    → Universal result dataclass
"""

from app.and9.and9 import AND9
from app.and9.brain_types import BrainType, IntentType, BrainResult

__all__ = ["AND9", "BrainType", "IntentType", "BrainResult"]
