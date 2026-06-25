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

__all__ = ["brain", "training", "utils", "gui"]
