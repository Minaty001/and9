#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════╗
║        MICRO NEURAL BRAIN - MAIN ENTRY POINT     ║
║   A lightweight cognitive system for Termux       ║
╚══════════════════════════════════════════════════╝

This is NOT a chatbot.
This is NOT an LLM.
This is a Micro Neural Cognitive System.

Usage:
    python main.py              # Interactive console mode
    python main.py --gui        # GUI Dashboard mode
    python main.py --cli        # CLI command mode
    python main.py --train      # Train the neural network
    python main.py --evaluate   # Evaluate performance
    python main.py --generate   # Generate intent dataset
"""

import os
import sys
import time
import json
import argparse
import signal
from datetime import datetime
from typing import Optional

from config import INTENTS, NN_CONFIG
from utils.logger import get_logger
from utils.metrics import get_metrics

logger = get_logger()


class MicroNeuralBrain:
    """
    The main cognitive system that integrates all five brains.

    Orchestrates:
    1. Reflex Brain  → Fast pattern matching
    2. Neural Brain  → Intent recognition
    3. Memory Brain  → SQLite memory system
    4. Decision Brain → Action planning
    5. Learning Brain → Habit learning
    """

    def __init__(self, verbose: bool = False):
        self.start_time = time.time()
        self.verbose = verbose
        self.initialized = False

        # Will be populated on init
        self.reflex = None
        self.neural = None
        self.memory = None
        self.decision = None
        self.learning = None
        self.metrics = None

        logger.info("=" * 50)
        logger.info("MICRO NEURAL BRAIN - Initializing")
        logger.info("=" * 50)

    def initialize(self) -> bool:
        """Initialize all brain components."""
        try:
            self._init_brains()
            self.initialized = True
            elapsed = (time.time() - self.start_time) * 1000
            logger.info(f"All brains initialized in {elapsed:.0f}ms")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize brain: {e}")
            return False

    def _init_brains(self):
        """Initialize each brain component."""
        from brain.reflex import ReflexBrain
        from brain.neural import NeuralBrain
        from brain.memory import MemoryBrain
        from brain.decision import DecisionBrain
        from brain.learning import LearningBrain

        logger.info("Initializing Reflex Brain...")
        self.reflex = ReflexBrain()

        logger.info("Initializing Neural Brain...")
        self.neural = NeuralBrain()

        logger.info("Initializing Memory Brain...")
        self.memory = MemoryBrain()

        logger.info("Initializing Decision Brain...")
        self.decision = DecisionBrain()

        logger.info("Initializing Learning Brain...")
        self.learning = LearningBrain()

        self.metrics = get_metrics()
        self.metrics.set_memory_count(self.memory.get_memory_count())

        # Log component stats
        logger.info(f"  Reflex:  {self.reflex.get_stats()['actions_registered']} actions")
        logger.info(f"  Neural:  {self.neural.get_stats()['parameters']} parameters")
        logger.info(f"  Memory:  {self.memory.get_memory_count()} memories")
        logger.info(f"  Learning:{self.learning.get_stats()['habits_learned']} habits")

    def process(self, text: str) -> dict:
        """
        Process user input through the full brain pipeline.

        Returns a dict with the complete processing result.
        """
        if not self.initialized:
            return {"error": "Brain not initialized"}

        if not text or not text.strip():
            return {"intent": "UNKNOWN", "confidence": 0, "action": "none", "response": "Say something!"}

        result = {
            "query": text,
            "timestamp": datetime.now().isoformat(),
            "pipeline": {},
        }

        # ── Step 1: Reflex Brain ────────────────────────
        t0 = time.time()
        reflex_intent, reflex_conf, reflex_action = self.reflex.match_intent(text)
        result["pipeline"]["reflex"] = {
            "intent": reflex_intent,
            "confidence": round(reflex_conf, 4),
            "action": reflex_action.name if reflex_action else None,
            "time_ms": round((time.time() - t0) * 1000, 2),
        }

        # ── Step 2: Neural Brain ────────────────────────
        t0 = time.time()
        nn_intent, nn_conf, nn_probs = self.neural.recognize_intent(text)
        result["pipeline"]["neural"] = {
            "intent": nn_intent,
            "confidence": round(nn_conf, 4),
            "time_ms": round((time.time() - t0) * 1000, 2),
        }
        self.metrics.log_neural_inference(result["pipeline"]["neural"]["time_ms"])

        # ── Step 3: Combine signals ─────────────────────
        # Prefer neural if confident, otherwise reflex
        if nn_conf >= reflex_conf:
            final_intent = nn_intent
            final_confidence = nn_conf
        else:
            final_intent = reflex_intent
            final_confidence = reflex_conf

        result["intent"] = final_intent
        result["confidence"] = round(final_confidence, 4)

        # ── Step 4: Decision Brain ──────────────────────
        t0 = time.time()
        context = {"reflex_intent": reflex_intent, "reflex_confidence": reflex_conf}
        memories = self.memory.search_memory(text, limit=3)
        action_plan = self.decision.decide(final_intent, final_confidence, context, memories, text)
        result["pipeline"]["decision"] = {
            "action": action_plan.action,
            "confidence": round(action_plan.confidence, 4),
            "requires_confirmation": action_plan.requires_confirmation,
            "reasoning": action_plan.reasoning,
            "time_ms": round((time.time() - t0) * 1000, 2),
        }
        result["action"] = action_plan.action
        result["action_plan"] = {
            "action": action_plan.action,
            "params": action_plan.params,
            "fallback": action_plan.fallback_action,
        }

        # ── Step 5: Execute Action ──────────────────────
        t0 = time.time()
        action_result = None
        if reflex_action:
            action_result = self.reflex.execute_action(reflex_action, text)
            if self.verbose:
                logger.info(f"  Action: {reflex_action.name} → {action_result['message']}")

        result["pipeline"]["execution"] = {
            "executed": reflex_action is not None,
            "result": action_result,
            "time_ms": round((time.time() - t0) * 1000, 2),
        }

        if action_result:
            self.metrics.log_action(reflex_action.name,
                                    action_result.get("success", False),
                                    action_result.get("duration_ms", 0))

        # ── Step 6: Memory Brain ────────────────────────
        t0 = time.time()
        self.memory.save_episodic_memory(
            event=text,
            importance=final_confidence,
            context=f"intent={final_intent}",
        )
        self.memory.log_activity(
            query=text,
            intent=final_intent,
            action=action_plan.action,
            result=json.dumps(action_result) if action_result else "no_action",
            duration=action_result.get("duration_ms", 0) if action_result else 0,
            success=1 if (action_result and action_result.get("success")) else 0,
        )
        result["pipeline"]["memory"] = {
            "saved": True,
            "time_ms": round((time.time() - t0) * 1000, 2),
        }

        # ── Step 7: Learning Brain ──────────────────────
        t0 = time.time()
        self.learning.observe(
            intent=final_intent,
            action=action_plan.action,
            success=bool(action_result and action_result.get("success")) if action_result else True,
            duration_ms=action_result.get("duration_ms", 0) if action_result else 0,
            context={"query": text},
        )

        # Check for habit prediction
        from datetime import datetime as dt
        now = dt.now()
        habit_prediction = self.learning.predict_next_intent()
        if habit_prediction:
            if self.verbose:
                logger.info(f"  Habit prediction: {habit_prediction['intent']} "
                           f"(conf={habit_prediction['confidence']:.2f})")

        result["pipeline"]["learning"] = {
            "habit_prediction": habit_prediction,
            "time_ms": round((time.time() - t0) * 1000, 2),
        }

        # ── Metrics ─────────────────────────────────────
        self.metrics.log_intent(final_intent, final_confidence, correct=True)
        self.metrics.set_memory_count(self.memory.get_memory_count())

        # Total time
        result["total_time_ms"] = round(sum(
            step.get("time_ms", 0) for step in result["pipeline"].values()
        ), 2)

        # Generate response
        result["response"] = self._generate_response(result)

        return result

    def _generate_response(self, result: dict) -> str:
        """Generate a concise response based on processing result."""
        intent = result["intent"]
        action = result.get("action", "")

        if intent == "UNKNOWN":
            return "I didn't understand that. Try asking me to open an app, check weather, etc."

        if result.get("action_plan", {}).get("requires_confirmation"):
            return f"I think you want to {action}. Please provide more details."

        if "execution" in result.get("pipeline", {}):
            exec_result = result["pipeline"]["execution"].get("result", {})
            if exec_result and exec_result.get("success"):
                return exec_result["message"]
            elif exec_result:
                return f"Could not execute: {exec_result.get('message', 'unknown error')}"

        return f"Processing: {action} (confidence: {result['confidence']:.0%})"

    def get_status(self) -> dict:
        """Get full system status."""
        uptime = time.time() - self.start_time
        status = {
            "uptime_seconds": round(uptime, 1),
            "uptime_formatted": self._format_uptime(uptime),
            "initialized": self.initialized,
        }

        if self.initialized:
            status["reflex"] = self.reflex.get_stats()
            status["neural"] = self.neural.get_stats()
            status["memory"] = self.memory.get_stats()
            status["decision"] = self.decision.get_stats()
            status["learning"] = self.learning.get_stats()
            status["metrics"] = self.metrics.get_summary()

        return status

    def _format_uptime(self, seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        parts = []
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        parts.append(f"{secs}s")
        return " ".join(parts)


# ═══════════════════════════════════════════════════════════
# CONSOLE MODE
# ═══════════════════════════════════════════════════════════

def run_console(brain: MicroNeuralBrain):
    """Run interactive console mode."""
    print("\n" + "=" * 50)
    print("  🧠 Micro Neural Brain - Console Mode")
    print("  Type your command below. 'help' for commands.")
    print("=" * 50)

    commands = {
        "help": "Show this help",
        "status": "Show brain status",
        "stats": "Show performance metrics",
        "memory": "Show recent memories",
        "habits": "Show learned habits",
        "train": "Quick-train neural network",
        "gui": "Launch GUI dashboard",
        "quit": "Exit",
    }

    while True:
        try:
            text = input("\n❯ ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not text:
            continue

        # Built-in commands
        if text.lower() == "quit" or text.lower() == "exit":
            print("Goodbye!")
            break
        elif text.lower() == "help":
            print("\nCommands:")
            for cmd, desc in commands.items():
                print(f"  {cmd:10s} - {desc}")
            continue
        elif text.lower() == "status":
            status = brain.get_status()
            print(f"\nUptime: {status.get('uptime_formatted', 'N/A')}")
            if "reflex" in status:
                print(f"Reflex: {status['reflex']['actions_registered']} actions")
            if "neural" in status:
                print(f"Neural: {status['neural']['trained']} (trained)")
            if "memory" in status:
                mem = status["memory"]
                print(f"Memory: {mem.get('episodic_memory', 0)} episodic, "
                      f"{mem.get('semantic_memory', 0)} semantic, "
                      f"{mem.get('habits', 0)} habits")
            if "learning" in status:
                learn = status["learning"]
                print(f"Learning: {learn.get('habits_learned', 0)} habits, "
                      f"{learn.get('overall_success_rate', 0):.1%} success")
            continue
        elif text.lower() == "stats":
            summary = brain.metrics.get_summary()
            print(f"\nPerformance Metrics:")
            for key, value in summary.items():
                print(f"  {key:20s}: {value}")
            continue
        elif text.lower() == "memory":
            activities = brain.memory.get_recent_activities(limit=10)
            print(f"\nRecent Activities ({len(activities)}):")
            for act in activities:
                print(f"  [{act.get('timestamp', '')[:19]}] {act.get('intent', '')}: {act.get('query', '')}")
            continue
        elif text.lower() == "habits":
            habits = brain.learning.get_habits(min_confidence=0.3)
            print(f"\nLearned Habits ({len(habits)}):")
            for h in habits:
                print(f"  {h['name']:30s} conf={h['confidence']:.2f}")
            continue
        elif text.lower() == "train":
            print("\nRunning quick training (20 epochs)...")
            from training.train import Trainer
            trainer = Trainer()
            result = trainer.quick_train(epochs=20)
            if "error" in result:
                print(f"Training error: {result['error']}")
            else:
                print(f"Training complete. Accuracy: {result['evaluation']['accuracy']:.4f}")
            continue
        elif text.lower() == "gui":
            print("\nLaunching GUI...")
            brain.metrics = get_metrics()
            launch_gui(brain)
            continue

        # Process through brain
        result = brain.process(text)
        print(f"\n  Intent:     {result.get('intent', '?')}")
        print(f"  Confidence: {result.get('confidence', 0):.1%}")
        print(f"  Action:     {result.get('action', '?')}")
        if result.get("response"):
            print(f"  Response:   {result['response']}")

        if brain.verbose and "pipeline" in result:
            print(f"  Pipeline:")
            for step, data in result["pipeline"].items():
                print(f"    {step}: {data.get('time_ms', 0):.1f}ms")


# ═══════════════════════════════════════════════════════════
# GUI MODE
# ═══════════════════════════════════════════════════════════

def launch_gui(brain: Optional[MicroNeuralBrain] = None):
    """Launch the GUI dashboard."""
    try:
        from gui.dashboard import launch_dashboard
        if brain:
            launch_dashboard(
                reflex=brain.reflex,
                neural=brain.neural,
                memory=brain.memory,
                decision=brain.decision,
                learning=brain.learning,
                metrics=brain.metrics,
            )
        else:
            launch_dashboard()
    except ImportError as e:
        logger.error(f"Cannot launch GUI: {e}")
        print(f"Error: {e}")
        print("Install customtkinter: pip install customtkinter")


# ═══════════════════════════════════════════════════════════
# CLI COMMAND MODE
# ═══════════════════════════════════════════════════════════

def run_command(brain: MicroNeuralBrain, command: str):
    """Process a single command (used from CLI)."""
    result = brain.process(command)
    print(json.dumps(result, indent=2, default=str))


# ═══════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Micro Neural Brain - A lightweight cognitive system"
    )
    parser.add_argument("--gui", action="store_true", help="Launch GUI dashboard")
    parser.add_argument("--cli", type=str, help="Process a single command (JSON output)")
    parser.add_argument("--train", action="store_true", help="Train the neural network")
    parser.add_argument("--evaluate", action="store_true", help="Evaluate model performance")
    parser.add_argument("--generate", action="store_true", help="Generate intent dataset")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--no-logo", action="store_true", help="Skip logo display")
    args = parser.parse_args()

    # Handle standalone tasks
    if args.generate:
        print("Generating intent dataset...")
        from datasets.generate_dataset import IntentDatasetGenerator
        gen = IntentDatasetGenerator()
        gen.generate(target=5500)
        gen.save()
        return 0

    if args.train:
        print("Training neural network...")
        from training.train import Trainer
        trainer = Trainer()
        result = trainer.full_train()
        if "error" in result:
            print(f"Error: {result['error']}")
            return 1
        print(f"\nTraining complete!")
        print(f"  Accuracy: {result['evaluation']['accuracy']:.4f}")
        print(f"  Time: {result['training_time_seconds']:.1f}s")
        print(f"  Model size: {result['model_size_mb']:.4f}MB")
        return 0

    if args.evaluate:
        print("Evaluating model...")
        from training.evaluate import Evaluator
        evaluator = Evaluator()
        test_set = evaluator.load_test_set()
        results = evaluator.evaluate(test_set)
        evaluator.print_report(results)
        return 0

    # Initialize the brain
    if not args.no_logo:
        print("\n" + "=" * 50)
        print("  🧠  MICRO NEURAL BRAIN")
        print("  ⚡  Cognitive System for Android Termux")
        print("  📦  RAM Budget: 50MB")
        print("=" * 50 + "\n")

    brain = MicroNeuralBrain(verbose=args.verbose)

    if not brain.initialize():
        print("FATAL: Could not initialize brain system.")
        return 1

    print(f"  ✓ Reflex Brain: {brain.reflex.get_stats()['actions_registered']} actions")
    print(f"  ✓ Neural Brain: {brain.neural.get_stats()['parameters']} parameters")
    print(f"  ✓ Memory Brain: {brain.memory.get_memory_count()} memories")
    print(f"  ✓ Decision Brain: Ready")
    print(f"  ✓ Learning Brain: Ready")
    print(f"\n  Startup: {brain.metrics.get_uptime_seconds():.1f}s")

    # Mode selection
    if args.gui:
        print("\nLaunching GUI Dashboard...")
        launch_gui(brain)
    elif args.cli:
        run_command(brain, args.cli)
    else:
        run_console(brain)

    return 0


if __name__ == "__main__":
    # Handle Ctrl+C gracefully
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    sys.exit(main())
