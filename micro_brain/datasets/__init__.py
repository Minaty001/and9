"""Training datasets for the Micro Neural Brain.

intents.json — Generated training data (5000+ samples across 20 intent classes).
generate_dataset.py — Script that produces intents.json.
"""

from .generate_dataset import generate_dataset, INTENTS

__all__ = ["generate_dataset", "INTENTS"]
