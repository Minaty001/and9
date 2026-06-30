import sys
import os
import json
import random
import time
import numpy as np

# Ensure app package and micro_brain compatibility folder are importable
sys.path.insert(0, "/root/github/and9")

from ai.datasets.generate_daily_1m import DailyConversationGenerator
from ai.training.train import Trainer
from micro_brain.config import DATASETS_DIR, INTENTS

def main():
    print("=== STARTING 10M ONLINE INCREMENTAL TRAINING ===")
    start_time = time.time()
    
    # Initialize the generator and trainer
    generator = DailyConversationGenerator(seed=42)
    trainer = Trainer()
    network = trainer.network
    
    # Holdout test set for final evaluation
    print("Generating holdout test set...")
    generator.DISTRIBUTION = {intent: val // 100 for intent, val in generator.DISTRIBUTION.items()}
    test_examples = generator.generate()
    test_texts = [e["text"] for e in test_examples]
    test_labels = [e["label"] for e in test_examples]
    print(f"Holdout test set size: {len(test_examples)}")
    
    # Total chunks to reach 10 million training queries
    # 10 chunks of 1M queries = 10M total queries
    num_chunks = 10
    samples_per_chunk = 1000000
    
    for chunk in range(1, num_chunks + 1):
        chunk_start = time.time()
        print(f"\n--- Chunk {chunk}/{num_chunks} (1,000,000 training samples) ---")
        
        # Reset distribution to 1M scale for this generation chunk
        generator.DISTRIBUTION = {
            "OPEN_APP": 50000,
            "CLOSE_APP": 20000,
            "PLAY_MUSIC": 30000,
            "PAUSE_MUSIC": 20000,
            "SEARCH_WEB": 60000,
            "WEATHER": 30000,
            "TIME": 30000,
            "DATE": 20000,
            "REMINDER": 40000,
            "CALL": 40000,
            "MESSAGE": 40000,
            "CAMERA": 30000,
            "FLASHLIGHT_ON": 20000,
            "FLASHLIGHT_OFF": 20000,
            "VOLUME_UP": 20000,
            "VOLUME_DOWN": 20000,
            "HOME": 20000,
            "BACK": 10000,
            "SETTING": 20000,
            "PYTHON_CODING": 80000,
            "AI_NEWS_MODELS": 80000,
            "CAPABILITIES": 40000,
            "WEB_CODING": 80000,
            "GENERAL_KNOWLEDGE": 150000,
            "MEDICINE_KNOWLEDGE": 60000,
            "MOVIE_KNOWLEDGE": 60000,
            "CHAT": 80000,
            "UNKNOWN": 50000,
        }
        
        # Generate 1M samples for this chunk
        examples = generator.generate()
        texts = [e["text"] for e in examples]
        labels = [e["label"] for e in examples]
        
        # Train for exactly 1 epoch on this chunk to incrementally update weights
        history = network.train(
            texts=texts,
            labels=labels,
            epochs=1,
            lr=0.01
        )
        
        chunk_elapsed = time.time() - chunk_start
        print(f"Chunk {chunk} finished in {chunk_elapsed:.1f}s. Loss: {history['train_loss'][-1]:.4f}, Acc: {history['train_acc'][-1]:.4f}")

    total_time = time.time() - start_time
    print(f"\n10M training finished in {total_time:.1f}s.")
    
    # Save the FP32 model
    print("Saving trained model...")
    network.save()
    
    # Quantize to INT8
    print("Quantizing model to INT8...")
    network.quantize()
    
    # Final Holdout evaluation
    print("\nEvaluating on holdout test set...")
    eval_results = network.evaluate(test_texts, test_labels)
    print(f"Final holdout test accuracy: {eval_results['accuracy']:.4f}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
