"""
╔══════════════════════════════════════════════════╗
║           MICRO NEURAL BRAIN - BRAINS            ║
║   Five Brains working as one cognitive system    ║
╚══════════════════════════════════════════════════╝

1. Reflex Brain   - Instant pattern-match actions
2. Memory Brain   - SQLite-based memory system
3. Neural Brain   - Intent recognition (tiny NN)
4. Decision Brain - Action selection engine
5. Learning Brain - Habit/pattern learning
"""

from .reflex import ReflexBrain
from .neural import NeuralBrain
from .memory import MemoryBrain
from .decision import DecisionBrain
from .learning import LearningBrain

__all__ = [
    "ReflexBrain",
    "NeuralBrain",
    "MemoryBrain",
    "DecisionBrain",
    "LearningBrain",
]
