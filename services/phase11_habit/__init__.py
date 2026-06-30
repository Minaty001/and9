"""
Phase 11 — Habit Brain
========================

Learns recurring routines and user preferences without replacing explicit
user control. Observes patterns in time, location, commands, and history
to suggest automation candidates.

Components:
    - HabitTracker: Observes events, builds and decays habits
    - HabitSuggester: Ranks suggestions by confidence/frequency
    - HabitBrainService: ServiceBase wrapper
"""

from .habit_tracker import HabitTracker, HabitPattern
from .habit_suggester import HabitSuggester, HabitSuggestion
from .service import HabitBrainService
from .config import HabitConfig
from .models import HabitObservation, HabitAuditEntry

__all__ = [
    "HabitTracker",
    "HabitPattern",
    "HabitSuggester",
    "HabitSuggestion",
    "HabitBrainService",
    "HabitConfig",
    "HabitObservation",
    "HabitAuditEntry",
]
