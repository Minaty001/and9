"""
╔══════════════════════════════════════════════════╗
║    MICRO NEURAL BRAIN - EVALUATION PIPELINE      ║
║   Evaluate model performance with rich metrics   ║
╚══════════════════════════════════════════════════╝
"""

import os
import sys
import json
import time
import random
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import NN_CONFIG, INTENTS, DATASETS_DIR
from brain.neural import NeuralBrain
from utils.logger import get_logger

logger = get_logger()


class Evaluator:
    """
    Evaluates the trained neural brain model with
    comprehensive metrics and visualizations.
    """

    def __init__(self):
        self.neural_brain = NeuralBrain()
        self.network = self.neural_brain.network

    def load_test_set(self, filename: str = "intents.json") -> list:
        """Load test examples from dataset."""
        filepath = DATASETS_DIR / filename
        if not filepath.exists():
            logger.error(f"Dataset not found: {filepath}")
            return []

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        examples = data["examples"]
        # Use 15% for test
        random.seed(42)
        random.shuffle(examples)
        n_test = max(100, int(len(examples) * 0.15))
        test_set = examples[:n_test]
        logger.info(f"Loaded {len(test_set)} test examples")
        return test_set

    def evaluate(self, test_set: list = None) -> dict:
        """Run full evaluation."""
        if test_set is None:
            test_set = self.load_test_set()

        if not test_set:
            return {"error": "No test data"}

        texts = [e["text"] for e in test_set]
        labels = [e["label"] for e in test_set]

        # Run evaluation
        results = self.network.evaluate(texts, labels)

        # Add timing benchmarks
        inference_times = []
        for text in texts[:100]:  # Benchmark on first 100
            start = time.time()
            self.network.predict(text)
            inference_times.append((time.time() - start) * 1000)

        results["avg_inference_time_ms"] = round(np.mean(inference_times), 3)
        results["p95_inference_time_ms"] = round(np.percentile(inference_times, 95), 3)
        results["min_inference_time_ms"] = round(float(np.min(inference_times)), 3)
        results["max_inference_time_ms"] = round(float(np.max(inference_times)), 3)

        # Model size
        model_path = NN_CONFIG["model_path"]
        if os.path.exists(model_path):
            results["model_size_mb"] = round(os.path.getsize(model_path) / (1024 * 1024), 4)

        # Per-intent details
        intent_results = {}
        for i, intent in enumerate(INTENTS):
            mask = np.array([l == i for l in labels])
            n_samples = int(np.sum(mask))
            if n_samples > 0:
                preds = results["confusion_matrix"][i]
                correct = preds[i] if i < len(preds) else 0
                accuracy = correct / n_samples if n_samples > 0 else 0.0
                intent_results[intent] = {
                    "samples": n_samples,
                    "correct": int(correct),
                    "accuracy": round(float(accuracy), 4),
                    "precision": round(float(preds[i] / max(1, sum(
                        results["confusion_matrix"][j][i] for j in range(len(INTENTS))
                    ))), 4),
                }

        results["intent_results"] = intent_results

        return results

    def print_report(self, results: dict):
        """Print a human-readable evaluation report."""
        if "error" in results:
            print(f"ERROR: {results['error']}")
            return

        print("\n" + "=" * 60)
        print("  MICRO NEURAL BRAIN - EVALUATION REPORT")
        print("=" * 60)
        print(f"\nOverall Accuracy: {results['accuracy']:.4f}")
        print(f"Correct: {results['correct']} / {results['total_samples']}")

        if "avg_inference_time_ms" in results:
            print(f"\nInference Speed:")
            print(f"  Average: {results['avg_inference_time_ms']:.2f}ms")
            print(f"  P95:     {results['p95_inference_time_ms']:.2f}ms")
            print(f"  Range:   {results['min_inference_time_ms']:.2f}ms - {results['max_inference_time_ms']:.2f}ms")

        if "model_size_mb" in results:
            print(f"\nModel Size: {results['model_size_mb']:.4f}MB")

        if "intent_results" in results:
            print(f"\n{'Intent':20s} {'Samples':>8s} {'Accuracy':>10s}")
            print("-" * 40)
            for intent, ir in sorted(results["intent_results"].items()):
                bar = "█" * int(ir["accuracy"] * 20) + "░" * (20 - int(ir["accuracy"] * 20))
                print(f"{intent:20s} {ir['samples']:>8d} {ir['accuracy']:>8.2%}  {bar}")

        # Confusion matrix (only top intents)
        print(f"\nConfusion Matrix (truncated to top 10 intents):")
        cm = np.array(results["confusion_matrix"])
        top_indices = np.argsort(-np.sum(cm, axis=1))[:10]
        header = "".join(f"{INTENTS[i][:8]:>8}" for i in top_indices)
        print(f"{'':>20s} |{header}")
        print("-" * (20 + len(top_indices) * 8 + 1))
        for i in top_indices:
            row = "".join(f"{cm[i, j]:>8d}" for j in top_indices)
            print(f"{INTENTS[i][:20]:>20s} |{row}")

    def interactive_test(self):
        """Interactive testing mode."""
        print("\nMicro Neural Brain - Interactive Test")
        print("Type 'quit' to exit\n")

        while True:
            text = input("\nEnter text: ").strip()
            if text.lower() in ("quit", "exit", "q"):
                break

            start = time.time()
            intent, confidence, probs = self.neural_brain.recognize_intent(text)
            duration = (time.time() - start) * 1000

            print(f"Intent: {intent}")
            print(f"Confidence: {confidence:.4f}")
            print(f"Time: {duration:.2f}ms")

            # Show top 3
            top_indices = np.argsort(-probs)[:3]
            print("Top 3:")
            for idx in top_indices:
                print(f"  {INTENTS[idx]}: {probs[idx]:.4f}")


def main():
    """Run evaluation from command line."""
    import argparse
    parser = argparse.ArgumentParser(description="Evaluate Micro Neural Brain")
    parser.add_argument("--interactive", "-i", action="store_true",
                        help="Interactive testing mode")
    parser.add_argument("--json", action="store_true",
                        help="Output results as JSON")
    parser.add_argument("--test-size", type=int, default=None,
                        help="Number of test samples")
    args = parser.parse_args()

    evaluator = Evaluator()

    if args.interactive:
        evaluator.interactive_test()
        return 0

    test_set = evaluator.load_test_set()
    if args.test_size and args.test_size < len(test_set):
        random.shuffle(test_set)
        test_set = test_set[:args.test_size]

    results = evaluator.evaluate(test_set)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        evaluator.print_report(results)

    return 0


if __name__ == "__main__":
    sys.exit(main())
