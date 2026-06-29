"""
Augment intent training data with HumanVsAI-2026 Kaggle dataset.

Maps each row's text to one of the 27 existing intents using keyword
analysis, then merges with the existing intents.json for retraining.

Usage:
    python ai/training/augment_kaggle.py          # merge into intents.json
    python ai/training/augment_kaggle.py --dry-run # show distribution only
"""

import csv
import json
import random
import argparse
import sys
from pathlib import Path
from collections import Counter

# ── Paths ───────────────────────────────────────────────────────
KAGGLE_CSV = Path("/tmp/humanvsai_data/HumanVsAI-2026.csv")
DATASETS_DIR = Path(__file__).resolve().parent.parent / "datasets"
INTENTS_JSON = DATASETS_DIR / "intents.json"
AUGMENTED_JSON = DATASETS_DIR / "intents_augmented.json"

# ── 27 Intent labels (must match config.INTENTS) ────────────────
ALL_INTENTS = [
    "OPEN_APP", "CLOSE_APP", "PLAY_MUSIC", "PAUSE_MUSIC",
    "SEARCH_WEB", "WEATHER", "TIME", "DATE", "REMINDER",
    "CALL", "MESSAGE", "CAMERA", "FLASHLIGHT_ON", "FLASHLIGHT_OFF",
    "VOLUME_UP", "VOLUME_DOWN", "HOME", "BACK", "SETTING",
    "PYTHON_CODING", "AI_NEWS_MODELS", "CAPABILITIES",
    "WEB_CODING", "GENERAL_KNOWLEDGE", "MEDICINE_KNOWLEDGE",
    "MOVIE_KNOWLEDGE", "UNKNOWN",
]

INTENT_INDEX = {name: idx for idx, name in enumerate(ALL_INTENTS)}

# ── Keyword → Intent mapping ────────────────────────────────────
# Each entry: (keywords list, target_intent, weight)
INTENT_KEYWORDS = [
    # AI / ML / Models
    (["machine learning", "deep learning", "artificial intelligence", "generative ai",
      "neural network", "data-driven", "llm", "gpt", "transformer",
      "ai model", "ai is", "ml model", "data science", "dataset",
      "artificial", "intelligence", "real world tasks",
      "generative", "data driven", "optimizing", "efficiently"],
     "AI_NEWS_MODELS", 3),
    
    # Coding / Programming
    (["python", "java", "code", "program", "function", "app building",
      "html", "css", "javascript", "coding", "software", "algorithm",
      "debug", "write code", "programming", "develop", "api", "syntax"],
     "PYTHON_CODING", 2),
    (["website", "web dev", "frontend", "backend", "full stack",
      "web design", "responsive", "website banao"],
     "WEB_CODING", 2),

    # Technology (general)
    (["technology", "tech", "digital", "computer", "internet", "smartphone",
      "gadget", "device", "electronic", "machine"],
     "GENERAL_KNOWLEDGE", 1),

    # Medicine / Health
    (["medicine", "doctor", "hospital", "health", "symptom", "disease",
      "patient", "treatment", "medical", "surgery", "exercise", "workout",
      "fitness", "gym", "body", "muscle", "diet", "nutrition", "protein",
      "weight", "fat", "calories"],
     "GENERAL_KNOWLEDGE", 1),

    # Study / Life / Routine
    (["study", "studying", "routine", "life", "sleep", "learning",
      "homework", "exam", "class", "school", "college", "university",
      "read", "book", "knowledge", "practice"],
     "GENERAL_KNOWLEDGE", 1),

    # Personal opinion / casual chat
    (["think", "feel", "believe", "honestly", "guess", "maybe",
      "kinda", "lol", "😂", "try", "tried", "just", "sometimes",
      "doesn", "don", "didn", "importan", "sens"],
     "UNKNOWN", 1),
]

# ── Source → Intent hints ───────────────────────────────────────
SOURCE_HINTS = {
    "research": "AI_NEWS_MODELS",
    "blog":     "GENERAL_KNOWLEDGE",
    "essay":    "GENERAL_KNOWLEDGE",
    "tweet":    "UNKNOWN",
}


def classify_text(text: str, source: str) -> str:
    """Classify a Kaggle text row into one of 27 intents."""
    t = text.lower()

    # Check keyword matches (highest weight wins)
    best_intent = None
    best_weight = 0
    for keywords, intent, weight in INTENT_KEYWORDS:
        if any(kw in t for kw in keywords):
            if weight > best_weight:
                best_weight = weight
                best_intent = intent

    # Fallback to source hint
    if best_intent is None:
        best_intent = SOURCE_HINTS.get(source, "GENERAL_KNOWLEDGE")

    return best_intent


def load_kaggle_csv(path: Path) -> list:
    """Load and classify Kaggle dataset rows."""
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    return rows


def augment(intents_path: Path, dry_run: bool = False):
    """Augment intents.json with Kaggle dataset."""
    if not KAGGLE_CSV.exists():
        print(f"❌ Kaggle CSV not found: {KAGGLE_CSV}")
        print("   Download it first:")
        print("   curl -sL -o /tmp/humanvsai.zip 'https://www.kaggle.com/api/v1/datasets/download/shanza30/humanvsai-2026-synthetic-text-detection-dataset?datasetVersionNumber=1'")
        print("   unzip -o /tmp/humanvsai.zip -d /tmp/humanvsai_data/")
        return

    # Load Kaggle data
    rows = load_kaggle_csv(KAGGLE_CSV)
    print(f"Loaded {len(rows)} rows from Kaggle dataset")

    # Classify each row to an intent
    new_examples = []
    intent_dist = Counter()
    for r in rows:
        intent = classify_text(r["text"], r.get("source", ""))
        intent_dist[intent] += 1
        new_examples.append({
            "text": r["text"],
            "intent": intent,
            "label": INTENT_INDEX[intent],
            # Keep original label as metadata
            "source": "kaggle_humanvsai_2026",
            "original_label": r["label"],
        })

    print(f"\n📊 Mapped intent distribution ({len(new_examples)} new samples):")
    for intent, count in sorted(intent_dist.items(), key=lambda x: -x[1]):
        print(f"  {intent:25s}: {count:4d} ({count/len(new_examples)*100:5.1f}%)")

    if dry_run:
        print("\n🧪 Dry run — no files modified. Run without --dry-run to augment.")
        return

    # Load existing intents.json
    if not intents_path.exists():
        print(f"❌ Existing intents.json not found at {intents_path}")
        print("   Generate it first: python ai/datasets/generate_dataset.py")
        return

    with open(intents_path, encoding="utf-8") as f:
        existing = json.load(f)

    old_count = len(existing.get("examples", []))
    print(f"\nExisting intents.json: {old_count} examples")

    # Merge: shuffle new + existing together
    merged_examples = existing["examples"] + new_examples
    random.shuffle(merged_examples)

    # Create augmented dataset
    augmented = {
        "version": "1.1",
        "description": (
            f"Micro Neural Brain Intent Dataset — augmented with "
            f"HumanVsAI-2026 Kaggle dataset ({len(new_examples)} additional samples)"
        ),
        "intents": ALL_INTENTS,
        "examples": merged_examples,
    }

    # Save
    with open(AUGMENTED_JSON, "w", encoding="utf-8") as f:
        json.dump(augmented, f, ensure_ascii=False, indent=1)

    print(f"\n✅ Augmented dataset saved: {AUGMENTED_JSON}")
    print(f"   Total examples: {len(merged_examples)} (+{len(new_examples)} from Kaggle)")

    # Also copy to intents.json for easy training
    import shutil
    shutil.copy2(AUGMENTED_JSON, intents_path)
    print(f"   Copied to {intents_path} (ready for training)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Augment intent data with Kaggle dataset")
    parser.add_argument("--dry-run", action="store_true", help="Show distribution only, don't modify files")
    args = parser.parse_args()

    augment(INTENTS_JSON, dry_run=args.dry_run)
