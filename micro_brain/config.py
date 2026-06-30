import os
from pathlib import Path
from app.brain.neural.neural import NN_CONFIG, INTENTS, INTENT_LABELS

# DATASETS_DIR relative to the repository root
DATASETS_DIR = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ai", "datasets")))
