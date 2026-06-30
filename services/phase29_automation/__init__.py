"""
Phase 29 — Automation Engine
=============================

If-this-then-that automation system. Manages triggers (time, schedule,
event, context), actions, rule validation, and execution history.

Components:
    - RuleEngine: Evaluates rules and executes actions
    - AutomationService: ServiceBase wrapper
"""

from .rule_engine import RuleEngine
from .service import AutomationService
from .config import AutomationConfig
from .models import AutomationRule, Trigger, Action, RuleExecution

__all__ = [
    "RuleEngine",
    "AutomationService",
    "AutomationConfig",
    "AutomationRule",
    "Trigger",
    "Action",
    "RuleExecution",
]
