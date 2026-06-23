"""
Core modules: config, orchestrator, memory, brain, personality OS.

Cognitive Architecture:
- personality_os.PersonalOS — Master integration point wiring all components
- CognitiveEngine — Unified brain orchestrator (Reflex → Habit → Reasoning)
- LearningSystem — Pattern, Skill, and Preference learning
- ProceduralMemory — Reusable learned skills with execution
- MemoryConsolidation — Working → Episodic → Semantic promotion
- AgentLoop — Continuous Observe→Think→Act→Reflect→Learn cycle
- AutomationSystem — Goals, Habits, Scheduled actions
"""

from app.core.personality_os import PersonalOS
