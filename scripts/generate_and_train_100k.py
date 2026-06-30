import sys
import os
import json
import random
import time

# Ensure app package and micro_brain compatibility folder are importable
sys.path.insert(0, "/root/github/and9")

from ai.datasets.generate_daily_1m import DailyConversationGenerator
from ai.training.train import Trainer
from micro_brain.config import DATASETS_DIR, INTENTS

def main():
    print("=== Step 1: Generating 100k Intent Dataset ===")
    generator = DailyConversationGenerator(seed=42)
    
    # Scale down the distribution to 100,000 total samples
    scaled_distribution = {intent: val // 10 for intent, val in generator.DISTRIBUTION.items()}
    generator.DISTRIBUTION = scaled_distribution
    
    # Generate the samples
    examples = generator.generate()
    
    # Save the 100k dataset as intents.json so that Trainer loads it automatically
    filepath = generator.save("intents.json")
    print(f"Generated {len(examples)} examples.")
    
    print("\n=== Step 2: Training the TinyNeuralNetwork on 100k Dataset ===")
    trainer = Trainer()
    
    # We will train for 10 epochs to keep it fast while ensuring high accuracy
    epochs = 10
    print(f"Starting training for {epochs} epochs...")
    
    result = trainer.train(epochs=epochs, save_model=True)
    
    if "error" in result:
        print(f"Training failed: {result['error']}")
        return 1

    print("\n" + "=" * 50)
    print("100K TRAINING & DEPLOYMENT SUMMARY")
    print("=" * 50)
    print(f"Training time: {result['training_time_seconds']:.1f}s")
    print(f"Test accuracy: {result['evaluation']['accuracy']:.4f}")
    print(f"Model size (FP32): {result['model_size_mb']:.3f}MB")
    
    # Verify quantization
    q_path = os.path.join("/root/github/and9/ai/models", "intent_model_int8.npz")
    if os.path.exists(q_path):
        q_size = os.path.getsize(q_path) / (1024 * 1024)
        print(f"Model size (INT8 quantized): {q_size:.3f}MB")
    else:
        print("Warning: Quantized model not found.")

    return 0

if __name__ == "__main__":
    sys.exit(main())
