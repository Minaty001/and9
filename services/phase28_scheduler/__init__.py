"""
Phase 28 — Scheduler
=====================

Manages reminders, recurring tasks, alarms, and calendar entries.
Supports conflict detection, time parsing, and persistence.

Components:
    - TimeParser: Parses natural language time expressions
    - SchedulerEngine: Core scheduling logic with conflict detection
    - ReminderManager: Creates and manages reminders
    - SchedulerService: ServiceBase wrapper
"""

from .time_parser import TimeParser
from .scheduler_engine import SchedulerEngine
from .reminder_manager import ReminderManager
from .service import SchedulerService
from .config import SchedulerConfig
from .models import ScheduledItem, TimeExpression, ConflictInfo

__all__ = [
    "TimeParser",
    "SchedulerEngine",
    "ReminderManager",
    "SchedulerService",
    "SchedulerConfig",
    "ScheduledItem",
    "TimeExpression",
    "ConflictInfo",
]
