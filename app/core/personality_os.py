"""
╔══════════════════════════════════════════════════════════════╗
║           PERSONAL OS — Master Cognitive Architecture        ║
║   Wires together all brains, memory, learning, automation   ║
╚══════════════════════════════════════════════════════════════╝

This module initializes and connects every component of the
cognitive architecture into one unified system.

Architecture:
                                  ┌─────────────────┐
                                  │   AGENT LOOP    │
                                  │ (Observe-Think- │
                                  │  Act-Reflect-   │
                                  │  Learn-Improve) │
                                  └────────┬────────┘
                                           │
┌──────────────────────────────────────────┼──────────────────────────┐
│                                          │                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┴──────────┐               │
│  │  REFLEX  │  │  HABIT   │  │     REASONING       │  COGNITIVE    │
│  │  BRAIN   │→ │  BRAIN   │→ │      BRAIN          │  ENGINE       │
│  │ (<300ms) │  │ (~200ms) │  │     (1-5s)          │               │
│  └──────────┘  └──────────┘  └─────────────────────┘               │
│                                          │                          │
│  ┌───────────────────────────────────────┼──────────────────┐      │
│  │              MEMORY SYSTEM            │                  │      │
│  │  ┌────────┐  ┌──────────┐  ┌─────────┴──────────┐      │      │
│  │  │WORKING │  │ EPISODIC │  │     SEMANTIC       │      │      │
│  │  │MEMORY  │→ │  MEMORY  │→ │     MEMORY         │      │      │
│  │  └────────┘  └──────────┘  └────────────────────┘      │      │
│  │  ┌──────────────────┐  ┌──────────────────────┐       │      │
│  │  │PROCEDURAL MEMORY │  │   KNOWLEDGE GRAPH    │       │      │
│  │  └──────────────────┘  └──────────────────────┘       │      │
│  └───────────────────────────────────────────────────────┘      │
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐       │
│  │              LEARNING SYSTEM                         │       │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │       │
│  │  │    PATTERN   │  │    SKILL     │  │ PREFERENCE │ │       │
│  │  │   LEARNING   │  │   LEARNING   │  │  LEARNING  │ │       │
│  │  └──────────────┘  └──────────────┘  └────────────┘ │       │
│  └──────────────────────────────────────────────────────┘       │
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐       │
│  │              AUTOMATION SYSTEM                        │       │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │       │
│  │  │    GOALS     │  │    HABITS    │  │ SCHEDULED  │ │       │
│  │  │   TRACKING   │  │   TRACKING   │  │  ACTIONS   │ │       │
│  │  └──────────────┘  └──────────────┘  └────────────┘ │       │
│  └──────────────────────────────────────────────────────┘       │
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐       │
│  │              ANDROID INTEGRATION                      │       │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────┐ │       │
│  │  │ACCESSIBILITY│  │   OVERLAY  │  │  APP CONTROL  │ │       │
│  │  └────────────┘  └────────────┘  └────────────────┘ │       │
│  └──────────────────────────────────────────────────────┘       │
└──────────────────────────────────────────────────────────────────┘
"""

import logging
import os
import time
from typing import Optional

logger = logging.getLogger("personality_os")


class PersonalOS:
    """Master integration point for the entire cognitive architecture.

    Initializes and connects:
    - Cognitive Engine (Reflex + Habit + Reasoning brains)
    - Memory System (Working, Episodic, Semantic, Procedural)
    - Learning System (Pattern, Skill, Preference)
    - Automation System (Goals, Habits, Scheduled Actions)
    - Agent Loop (Continuous Observe-Think-Act-Reflect-Learn)
    - Android Integration
    - API routes

    Usage:
        os = PersonalOS()
        os.start()
        result = os.process("Open WhatsApp")
        stats = os.get_stats()
    """

    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self._initialized = False
        self._started = False

        # Core components (lazy-initialized)
        self.cognitive_engine = None
        self.learning_system = None
        self.memory_consolidation = None
        self.memory_system = None
        self.procedural_memory = None
        self.automation_system = None
        self.agent_loop = None
        self.reflection_engine = None
        self.knowledge_graph = None

        logger.info("PersonalOS: Instance created")

    # ═══════════════════════════════════════════════════════════════
    # INITIALIZATION
    # ═══════════════════════════════════════════════════════════════

    def initialize(self):
        """Initialize all components. Called once at startup."""
        if self._initialized:
            return

        logger.info("=" * 60)
        logger.info("PersonalOS: Initializing cognitive architecture...")
        logger.info("=" * 60)

        try:
            # 1. Procedural Memory (no dependencies)
            from app.memory.long_term import ProceduralMemory
            self.procedural_memory = ProceduralMemory()
            logger.info("✓ Procedural Memory initialized")

            # 2. Memory Consolidation (no dependencies)
            from app.core.memory_consolidation import MemoryConsolidation
            self.memory_consolidation = MemoryConsolidation()
            logger.info("✓ Memory Consolidation initialized")

            # 3. Learning System (depends on procedural memory)
            from app.core.learning_system import LearningSystem
            self.learning_system = LearningSystem(enable_all=True)
            if self.learning_system.skill_learner:
                self.learning_system.skill_learner._procedural_memory = self.procedural_memory
            logger.info("✓ Learning System initialized (Pattern + Skill + Preference)")

            # 4. Load existing memory system (Supabase)
            try:
                from app.memory.episodic.memory import get_memory
                self.memory_system = get_memory()
                logger.info("✓ Memory System (Supabase) initialized")
            except Exception as e:
                logger.warning(f"Memory System skipped: {e}")

            # 5. Knowledge Graph
            try:
                from app.memory.semantic.knowledge_graph import KnowledgeGraph
                if self.memory_system:
                    self.knowledge_graph = KnowledgeGraph(self.memory_system)
                    logger.info("✓ Knowledge Graph initialized")
            except Exception as e:
                logger.warning(f"Knowledge Graph skipped: {e}")

            # 6. Load existing reflection engine
            try:
                from app.brain.decision.reflection import ReflectionEngine
                if self.memory_system:
                    self.reflection_engine = ReflectionEngine(self.memory_system)
                    logger.info("✓ Reflection Engine initialized")
            except Exception as e:
                logger.warning(f"Reflection Engine skipped: {e}")

            # 7. Automation System
            from app.services.automation.automation_system import AutomationSystem
            self.automation_system = AutomationSystem()
            logger.info("✓ Automation System initialized")

            # 8. Cognitive Engine (the core)
            try:
                # Try to load Conscious Brain
                from app.brain.conscious.conscious_brain import ConsciousBrain
                conscious_brain = ConsciousBrain()
                logger.info("✓ Conscious Brain loaded")
            except Exception as e:
                conscious_brain = None
                logger.warning(f"Conscious Brain not available: {e}")

            from app.brain.planner.cognitive_engine import (
                CognitiveEngine, ReflexProcessor, HabitProcessor,
            )
            self.cognitive_engine = CognitiveEngine(
                reflex_processor=ReflexProcessor(),
                habit_processor=HabitProcessor(),
                conscious_brain=conscious_brain,
                memory_system=self.memory_system,
                learning_system=self.learning_system,
                enable_learning=True,
                memory_consolidation=self.memory_consolidation,
            )
            logger.info("✓ Cognitive Engine initialized (Reflex + Habit + Reasoning)")

            # 9. Agent Loop (depends on everything above)
            from app.core.agent_loop import AgentLoop
            self.agent_loop = AgentLoop(
                cognitive_engine=self.cognitive_engine,
                learning_system=self.learning_system,
                memory_consolidation=self.memory_consolidation,
                enable_proactive=True,
            )
            logger.info("✓ Agent Loop initialized")

            self._initialized = True
            logger.info("=" * 60)
            logger.info("PersonalOS: ALL SYSTEMS INITIALIZED")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"PersonalOS: Initialization failed: {e}", exc_info=True)
            raise

    def start(self):
        """Start all background services.

        Call this after initialize() to start:
        - Agent Loop (continuous observation)
        - Automation System (scheduled checks)
        - Memory Consolidation (background cycles)
        """
        if self._started:
            logger.warning("PersonalOS: Already started")
            return

        if not self._initialized:
            self.initialize()

        logger.info("PersonalOS: Starting background services...")

        try:
            # Start agent loop
            if self.agent_loop:
                self.agent_loop.start()
                logger.info("✓ Agent Loop started")

            # Start automation system
            if self.automation_system:
                self.automation_system.start()
                logger.info("✓ Automation System started")

            # Start memory consolidation
            if self.memory_consolidation:
                self.memory_consolidation.start()
                logger.info("✓ Memory Consolidation started")

            self._started = True
            logger.info("PersonalOS: All services running")

        except Exception as e:
            logger.error(f"PersonalOS: Start failed: {e}", exc_info=True)

    def stop(self):
        """Stop all background services gracefully."""
        logger.info("PersonalOS: Stopping services...")

        if self.agent_loop:
            self.agent_loop.stop()
        if self.automation_system:
            self.automation_system.stop()
        if self.memory_consolidation:
            self.memory_consolidation.stop()

        self._started = False
        logger.info("PersonalOS: All services stopped")

    # ═══════════════════════════════════════════════════════════════
    # MAIN PROCESSING INTERFACE
    # ═══════════════════════════════════════════════════════════════

    def process(self, user_input: str, **context) -> dict:
        """Process any user input through the full cognitive architecture.

        This is the MAIN entry point for all user interactions.

        Args:
            user_input: The user's command, question, or message.
            **context: Optional context (emotion, topic, source).

        Returns:
            Dict with response and processing metadata.
        """
        if not self._initialized:
            self.initialize()

        if not self.cognitive_engine:
            return {
                "response": "Cognitive engine not available. Please check system status.",
                "success": False,
            }

        try:
            # Queue observation in agent loop
            if self.agent_loop:
                self.agent_loop.observe(
                    obs_type="user_input",
                    content=user_input,
                    source="user",
                    importance=0.9,
                    metadata=context,
                )

            # Process through cognitive engine
            result = self.cognitive_engine.process(user_input, **context)

            # Return user-friendly response
            return result.to_dict()

        except Exception as e:
            logger.error(f"PersonalOS: Process error: {e}", exc_info=True)
            return {
                "response": f"Kuch gadbad ho gayi: {str(e)}. Please try again! 😅",
                "success": False,
                "error": str(e),
            }

    def observe_notification(self, title: str, text: str, app: str = ""):
        """Observe a notification from an app.

        This feeds into the agent loop and learning system.
        """
        if not self._initialized:
            self.initialize()

        content = f"[{app}] {title}: {text}" if app else f"{title}: {text}"

        if self.agent_loop:
            self.agent_loop.observe(
                obs_type="notification",
                content=content,
                source=app or "notification",
                importance=0.5,
            )

    def observe_screen_change(self, screen_info: str, app: str = ""):
        """Observe a screen/UI state change."""
        if self.agent_loop:
            self.agent_loop.observe(
                obs_type="screen_change",
                content=screen_info,
                source=app or "system",
                importance=0.3,
            )

    # ═══════════════════════════════════════════════════════════════
    # UTILITY METHODS
    # ═══════════════════════════════════════════════════════════════

    def get_stats(self) -> dict:
        """Get comprehensive system statistics."""
        stats = {
            "initialized": self._initialized,
            "started": self._started,
            "uptime": None,
        }

        if self.cognitive_engine:
            stats["cognitive_engine"] = self.cognitive_engine.get_stats()

        if self.learning_system:
            stats["learning"] = self.learning_system.get_stats()

        if self.procedural_memory:
            stats["procedural_memory"] = self.procedural_memory.get_stats()

        if self.memory_consolidation:
            stats["memory_consolidation"] = self.memory_consolidation.get_stats()

        if self.automation_system:
            stats["automation"] = self.automation_system.get_stats()

        if self.agent_loop:
            stats["agent_loop"] = self.agent_loop.get_stats()

        return stats

    def get_daily_reflection(self) -> dict:
        """Get end-of-day reflection from the cognitive engine."""
        if self.cognitive_engine:
            return self.cognitive_engine.get_daily_reflection()
        return {"summary": "Cognitive engine not available."}

    def get_all_learnings(self) -> dict:
        """Get all accumulated learnings (patterns, skills, preferences)."""
        if self.learning_system:
            return self.learning_system.get_all_learnings()
        return {}

    def get_goal_summary(self) -> str:
        """Get a summary of all goals."""
        if self.automation_system:
            return self.automation_system.get_goal_summary()
        return "Automation system not available."

    def add_goal(self, title: str, category: str = "personal",
                  priority: str = "medium") -> dict:
        """Add a new goal."""
        if self.automation_system:
            goal = self.automation_system.add_goal(title, category, priority)
            return {"goal_id": goal.goal_id, "title": goal.title, "success": True}
        return {"success": False, "error": "Automation system not available"}

    def add_habit(self, name: str, frequency: str = "daily") -> dict:
        """Add a new habit to track."""
        if self.automation_system:
            habit = self.automation_system.add_habit(name, frequency=frequency)
            return {"habit_id": habit.habit_id, "name": habit.name, "success": True}
        return {"success": False, "error": "Automation system not available"}
