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

from brain.reflex import ReflexBrain
from brain.neural import NeuralBrain
from brain.memory import MemoryBrain
from brain.decision import DecisionBrain
from brain.learning import LearningBrain

__all__ = [
    "ReflexBrain",
    "NeuralBrain",
    "MemoryBrain",
    "DecisionBrain",
    "LearningBrain",
]
