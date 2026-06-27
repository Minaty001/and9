"""
╔══════════════════════════════════════════════════╗
║           MICRO NEURAL BRAIN                     ║
║   Offline cognitive system for Termux/Android    ║
║   Intent recognition + Memory + Reflex actions   ║
╚══════════════════════════════════════════════════╝

Subpackages:
    brain/        — Five-brains cognitive engine (Reflex → Neural → Memory → Decision → Learning)
    config.py     — Configuration constants
    database/     — SQLite memory persistence
    datasets/     — Training data (generated)
    gui/          — CustomTkinter dashboard
    models/       — Trained neural network weights
    training/     — Training and evaluation pipelines
    utils/        — Logging and metrics tracking
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make the package directory importable as a module root so legacy
# absolute imports like `from config import ...` continue to work when
# the package is imported from the repository root.
_PACKAGE_ROOT = Path(__file__).resolve().parent
if str(_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(_PACKAGE_ROOT))

__all__ = ["brain", "training", "utils", "gui"]
