"""Training datasets for the Micro Neural Brain.

intents.json — Generated training data (5000+ samples across 20 intent classes).
generate_dataset.py — Script that produces intents.json.
"""

from .generate_dataset import IntentDatasetGenerator, INTENTS

__all__ = ["IntentDatasetGenerator", "INTENTS"]
