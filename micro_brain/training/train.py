"""
╔══════════════════════════════════════════════════╗
║     MICRO NEURAL BRAIN - TRAINING PIPELINE       ║
║   Train the tiny neural network on intent data   ║
╚══════════════════════════════════════════════════╝
"""

import os
import sys
import json
import time
import random
import numpy as np
from typing import List, Dict, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import NN_CONFIG, INTENTS, DATASETS_DIR
from brain.neural import NeuralBrain, NeuralConfig, TinyNeuralNetwork
from utils.logger import get_logger

logger = get_logger()


class Trainer:
    """
    Training pipeline for the Micro Neural Brain's intent classifier.
    Handles dataset loading, training, validation, and model export.
    """

    def __init__(self):
        self.neural_brain = NeuralBrain()
        self.network = self.neural_brain.network
        self.dataset = None

    def load_dataset(self, filename: str = "intents.json") -> List[Dict]:
        """Load intent dataset."""
        filepath = DATASETS_DIR / filename
        if not filepath.exists():
            logger.error(f"Dataset not found: {filepath}")
            logger.info("Run datasets/generate_dataset.py first")
            return []

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.dataset = data["examples"]
        logger.info(f"Loaded {len(self.dataset)} examples from {filepath}")
        return self.dataset

    def split_data(self, examples: List[Dict],
                   val_split: float = 0.2,
                   test_split: float = 0.1) -> tuple:
        """Split dataset into train/val/test."""
        random.seed(42)
        random.shuffle(examples)
        n = len(examples)
        n_test = int(n * test_split)
        n_val = int(n * val_split)

        test = examples[:n_test]
        val = examples[n_test:n_test + n_val]
        train = examples[n_test + n_val:]

        logger.info(f"Split: train={len(train)}, val={len(val)}, test={len(test)}")

        train_texts = [e["text"] for e in train]
        train_labels = [e["label"] for e in train]
        val_texts = [e["text"] for e in val]
        val_labels = [e["label"] for e in val]
        test_texts = [e["text"] for e in test]
        test_labels = [e["label"] for e in test]

        return (train_texts, train_labels), (val_texts, val_labels), (test_texts, test_labels)

    def train(self, epochs: Optional[int] = None,
              learning_rate: Optional[float] = None,
              save_model: bool = True) -> Dict:
        """
        Run the full training pipeline.

        Args:
            epochs: Number of training epochs (default from config)
            learning_rate: Learning rate (default from config)
            save_model: Whether to save model after training

        Returns:
            Training history dict
        """
        # Load dataset
        examples = self.load_dataset()
        if not examples:
            return {"error": "No dataset loaded"}

        # Split
        train_data, val_data, test_data = self.split_data(examples)
        train_texts, train_labels = train_data
        val_texts, val_labels = val_data

        start_time = time.time()

        # Train
        history = self.network.train(
            texts=train_texts,
            labels=train_labels,
            val_texts=val_texts,
            val_labels=val_labels,
            epochs=epochs or NN_CONFIG["epochs"],
            lr=learning_rate or NN_CONFIG["learning_rate"],
        )

        training_time = time.time() - start_time
        logger.info(f"Training completed in {training_time:.1f}s")

        # Evaluate on test set
        test_texts, test_labels = test_data
        eval_results = self.network.evaluate(test_texts, test_labels)
        logger.info(
            f"Test accuracy: {eval_results['accuracy']:.4f} "
            f"({eval_results['correct']}/{eval_results['total_samples']})"
        )

        # Class-wise accuracy
        logger.info("Class-wise accuracy:")
        for intent, acc in sorted(eval_results["class_accuracy"].items()):
            logger.info(f"  {intent:20s}: {acc:.4f}")

        # Save model
        if save_model:
            model_size = self.network.save()
            logger.info(f"Model saved ({model_size:.3f}MB)")

            # Quantize
            quant_info = self.network.quantize()
            logger.info(f"INT8 quantized: {quant_info['size_mb']:.3f}MB")

        return {
            "history": history,
            "evaluation": eval_results,
            "training_time_seconds": training_time,
            "model_size_mb": self.network.get_model_size_mb(),
        }

    def quick_train(self, epochs: int = 20) -> Dict:
        """Quick training for testing purposes."""
        return self.train(epochs=epochs)

    def full_train(self) -> Dict:
        """Full training with best params."""
        return self.train(
            epochs=NN_CONFIG["epochs"],
            learning_rate=NN_CONFIG["learning_rate"],
        )


def main():
    """Run training from command line."""
    import argparse
    parser = argparse.ArgumentParser(description="Train Micro Neural Brain")
    parser.add_argument("--epochs", type=int, default=None,
                        help="Number of training epochs")
    parser.add_argument("--quick", action="store_true",
                        help="Quick training (20 epochs)")
    parser.add_argument("--lr", type=float, default=None,
                        help="Learning rate")
    args = parser.parse_args()

    trainer = Trainer()
    if args.quick:
        result = trainer.quick_train(epochs=args.epochs or 20)
    else:
        result = trainer.full_train() if not args.epochs else trainer.train(
            epochs=args.epochs, learning_rate=args.lr
        )

    if "error" in result:
        print(f"Training failed: {result['error']}")
        return 1

    print("\n" + "=" * 50)
    print("TRAINING SUMMARY")
    print("=" * 50)
    print(f"Training time: {result['training_time_seconds']:.1f}s")
    print(f"Test accuracy: {result['evaluation']['accuracy']:.4f}")
    print(f"Model size: {result['model_size_mb']:.3f}MB")

    # Final train accuracy
    if result["history"]["train_acc"]:
        print(f"Final train accuracy: {result['history']['train_acc'][-1]:.4f}")
    if result["history"].get("val_acc") and result["history"]["val_acc"]:
        print(f"Final val accuracy: {result['history']['val_acc'][-1]:.4f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
