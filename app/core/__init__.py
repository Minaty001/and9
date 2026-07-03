"""
app/core — Core modules: config, orchestrator, memory, brain, and supporting services.

Central configuration, LLM orchestration, memory systems, event/reminder engine,
goal tracking, reflection, proactive intelligence, truth engine, and intent tracing.
"""

# Config
from app.core import config

# Brain / LLM
from app.core.brain import ask_llm, ask_llm_json, get_available_models
from app.core.understanding import UnderstandingEngine, MessageAnalysis
from app.core.context_builder import ContextBuilder

# Orchestrator
from app.core.orchestrator import Orchestrator, IntentRouter

# Memory
from app.core.memory import Memory, get_memory
from app.core.working_memory import WorkingMemory
from app.core.knowledge_graph import KnowledgeGraph

# Goals
from app.core.goal_tracker import GoalTracker

# Events / Reminders
from app.core.events import EventSystem, is_event_request

# Reflection
from app.core.reflection import ReflectionEngine

# Proactive
from app.core.proactive import ProactiveEngine

# Truth Engine
from app.core.truth_engine import (
    verify_before_llm, cap_confidence, has_relevant_memory,
    validate_memory, annotate_facts_with_confidence, generate_dont_know_response,
)

# Timer
from app.core.timer import Timer, TimerService, get_timer_service

# Logging
from app.core.logger import QueryLogger, QueryLog, get_logger, is_debug_enabled

# Intent Trace
from app.core.intent_trace import TraceContext, log_trace, init_trace_db, get_recent_traces

# Diagnostics
from app.core.diagnostics import run_diagnostics

# Activity
from app.core.activity_logger import ActivityLogger, get_activity_logger

# Personality
from app.core.personality import build_personality_prompt

# Constants
from app.core.constants import ActionType, ActionRegistry

__all__ = [
    # Sub-module (for config.* access)
    "config",
    # Brain
    "ask_llm", "ask_llm_json", "get_available_models",
    "UnderstandingEngine", "MessageAnalysis", "ContextBuilder",
    # Orchestrator
    "Orchestrator", "IntentRouter",
    # Memory
    "Memory", "get_memory", "WorkingMemory", "KnowledgeGraph",
    # Goals
    "GoalTracker",
    # Events
    "EventSystem", "is_event_request",
    # Reflection
    "ReflectionEngine",
    # Proactive
    "ProactiveEngine",
    # Truth Engine
    "verify_before_llm", "cap_confidence", "has_relevant_memory",
    "validate_memory", "annotate_facts_with_confidence", "generate_dont_know_response",
    # Timer
    "Timer", "TimerService", "get_timer_service",
    # Logging
    "QueryLogger", "QueryLog", "get_logger", "is_debug_enabled",
    # Intent Trace
    "TraceContext", "log_trace", "init_trace_db", "get_recent_traces",
    # Diagnostics
    "run_diagnostics",
    # Activity
    "ActivityLogger", "get_activity_logger",
    # Personality
    "build_personality_prompt",
    # Constants
    "ActionType", "ActionRegistry",
]
