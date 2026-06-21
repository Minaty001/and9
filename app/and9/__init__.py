"""
AND9 — Personal Android AI Operating System.

Multi-brain cognitive architecture:
  - Reflex Brain:    Instant, no-LLM execution (<100ms)
  - Subconscious:    Pattern learning, habits, routines
  - Conscious Brain: LLM reasoning, planning, complex tasks
"""

from app.and9.and9 import AND9
from app.and9.brain_types import BrainType, IntentType, BrainResult

__all__ = ["AND9", "BrainType", "IntentType", "BrainResult"]
