"""
╔══════════════════════════════════════════════════╗
║   MICRO NEURAL BRAIN - GUI DASHBOARD            ║
║   CustomTkinter-based brain activity monitor     ║
╚══════════════════════════════════════════════════╝

Displays:
    - Brain Activity Overview
    - Current Intent & Confidence
    - Memory Statistics
    - Neural Activity Visualizer
    - System Monitor (CPU/RAM)
    - Learning Progress
    - Activity Log
"""

import os
import sys
import time
import threading
import numpy as np
from datetime import datetime
from collections import deque
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import GUI_CONFIG, INTENTS

try:
    import customtkinter as ctk
    CTK_AVAILABLE = True
except ImportError:
    CTK_AVAILABLE = False
    print("CustomTkinter not installed. GUI unavailable.")
    print("Install with: pip install customtkinter")


# ── Import neural brain components (lazy) ──────────────────
def _import_brain():
    from brain.reflex import ReflexBrain
    from brain.neural import NeuralBrain
    from brain.memory import MemoryBrain
    from brain.decision import DecisionBrain
    from brain.learning import LearningBrain
    from utils.metrics import get_metrics
    return (
        ReflexBrain(), NeuralBrain(), MemoryBrain(),
        DecisionBrain(), LearningBrain(), get_metrics()
    )


# ═══════════════════════════════════════════════════════════
# NEURAL ACTIVITY VISUALIZER (Canvas-based)
# ═══════════════════════════════════════════════════════════

class NeuralActivityVisualizer(ctk.CTkCanvas if CTK_AVAILABLE else object):
    """
    Real-time neural activity visualization.

    Shows a simplified neural network firing pattern
    with animated nodes and connections.
    """

    def __init__(self, master, width=400, height=200):
        if not CTK_AVAILABLE:
            return
        super().__init__(master, width=width, height=height,
                         bg="#1a1a2e", highlightthickness=0)
        self.width = width
        self.height = height
        self.activity_levels = deque(maxlen=50)
        self._running = False
        self._anim_frame = 0

        # Node positions (simplified 3-layer visualization)
        self.nodes = {
            "input": [(50, 40 + i * 25) for i in range(5)],
            "hidden": [(200, 30 + i * 22) for i in range(6)],
            "output": [(350, 50 + i * 30) for i in range(3)],
        }

    def start(self):
        if not CTK_AVAILABLE:
            return
        self._running = True
        self._animate()

    def stop(self):
        self._running = False

    def set_activity(self, level: float):
        """Set current neural activity level (0-1)."""
        self.activity_levels.append(level)

    def _animate(self):
        if not self._running or not CTK_AVAILABLE:
            return
        self.delete("all")

        self._anim_frame += 1
        # Draw connections
        for layer_name, nodes in self.nodes.items():
            next_layer = list(self.nodes.values())[min(
                list(self.nodes.keys()).index(layer_name) + 1,
                len(self.nodes) - 1
            )] if layer_name != "output" else []
            for x1, y1 in nodes:
                for x2, y2 in next_layer:
                    intensity = self._get_connection_intensity()
                    color = self._intensity_color(intensity)
                    self.create_line(x1, y1, x2, y2, fill=color, width=1)

        # Draw nodes
        for layer_name, nodes in self.nodes.items():
            for i, (x, y) in enumerate(nodes):
                intensity = self._get_node_intensity(layer_name, i)
                color = self._intensity_color(intensity)
                radius = 5 + intensity * 8
                self.create_oval(x - radius, y - radius,
                                 x + radius, y + radius,
                                 fill=color, outline="#ffffff44", width=1)

        # Activity waveform at bottom
        self._draw_waveform()

        if self._running:
            self.after(GUI_CONFIG["neural_visualizer_update_ms"], self._animate)

    def _get_connection_intensity(self) -> float:
        if self.activity_levels:
            return self.activity_levels[-1] * (0.3 + 0.7 * np.sin(self._anim_frame * 0.1 + 1))
        return 0.1

    def _get_node_intensity(self, layer: str, idx: int) -> float:
        if not self.activity_levels:
            return 0.3
        base = self.activity_levels[-1]
        phase = (self._anim_frame * 0.05 + idx * 0.5 + hash(layer) * 0.1) % (2 * np.pi)
        return max(0.1, min(1.0, base * (0.5 + 0.5 * np.sin(phase))))

    def _intensity_color(self, intensity: float) -> str:
        if intensity < 0.3:
            r, g, b = int(30 * intensity), int(80 * intensity), int(150 * intensity)
        elif intensity < 0.6:
            r, g, b = int(50 + 100 * (intensity - 0.3)), int(100 + 100 * (intensity - 0.3)), int(50)
        else:
            r, g, b = int(150 + 100 * (intensity - 0.6)), int(50), int(50)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _draw_waveform(self):
        if not self.activity_levels:
            return
        levels = list(self.activity_levels)
        w, h = self.width, self.height
        margin = 10
        wave_h = 30
        y_base = h - wave_h - margin

        self.create_text(w // 2, y_base - 10, text="Neural Activity",
                         fill="#888888", font=("Arial", 8))

        n = len(levels)
        if n < 2:
            return
        for i in range(n - 1):
            x1 = margin + (w - 2 * margin) * i / n
            x2 = margin + (w - 2 * margin) * (i + 1) / n
            y1 = y_base + wave_h - levels[i] * wave_h
            y2 = y_base + wave_h - levels[i + 1] * wave_h
            color = self._intensity_color(levels[i])
            self.create_line(x1, y1, x2, y2, fill=color, width=2)


# ═══════════════════════════════════════════════════════════
# BRAIN ACTIVITY INDICATOR
# ═══════════════════════════════════════════════════════════

class BrainActivityFrame(ctk.CTkFrame if CTK_AVAILABLE else object):
    """Shows current brain state with visual indicators."""

    def __init__(self, master):
        if not CTK_AVAILABLE:
            return
        super().__init__(master, fg_color="#16213e")
        self.grid_columnconfigure(1, weight=1)

        self.brain_labels = {}
        brains = [
            ("🧠 Reflex", "#00b894"),
            ("🧠 Memory", "#00cec9"),
            ("🧠 Neural", "#6c5ce7"),
            ("🧠 Decision", "#fd79a8"),
            ("🧠 Learning", "#fdcb6e"),
        ]

        for i, (name, color) in enumerate(brains):
            frame = ctk.CTkFrame(self, fg_color="#1a1a3e", height=30)
            frame.grid(row=i, column=0, columnspan=2, sticky="ew", pady=2, padx=5)
            frame.grid_propagate(False)

            indicator = ctk.CTkLabel(frame, text="●", text_color=color,
                                     font=("Arial", 14))
            indicator.pack(side="left", padx=(8, 5))

            label = ctk.CTkLabel(frame, text=name, text_color="#dfe6e9",
                                 font=("Arial", 12), anchor="w")
            label.pack(side="left", fill="x", expand=True)

            status = ctk.CTkLabel(frame, text="IDLE", text_color="#636e72",
                                  font=("Arial", 10))
            status.pack(side="right", padx=8)

            self.brain_labels[name.strip("🧠 ")] = (indicator, status)

    def set_brain_status(self, brain: str, status: str, active: bool = False):
        if brain not in self.brain_labels:
            return
        indicator, status_label = self.brain_labels[brain]
        if active:
            indicator.configure(text_color="#00b894")
            status_label.configure(text=status, text_color="#00b894")
        else:
            indicator.configure(text_color="#636e72")
            status_label.configure(text=status, text_color="#636e72")


# ═══════════════════════════════════════════════════════════
# MAIN DASHBOARD
# ═══════════════════════════════════════════════════════════

class MicroBrainDashboard:
    """
    Main dashboard for the Micro Neural Brain.
    Uses CustomTkinter for a modern, lightweight GUI.
    """

    def __init__(self):
        if not CTK_AVAILABLE:
            print("CustomTkinter not available. Cannot start GUI.")
            return

        self.root = ctk.CTk()
        self.root.title("Micro Neural Brain - Cognitive Dashboard")
        self.root.geometry(f"{GUI_CONFIG['window_size'][0]}x{GUI_CONFIG['window_size'][1]}")
        ctk.set_appearance_mode(GUI_CONFIG["theme"])
        ctk.set_default_color_theme("dark-blue")

        # Brain components
        self.reflex = None
        self.neural = None
        self.memory = None
        self.decision = None
        self.learning = None
        self.metrics = None

        # State
        self._current_intent = "—"
        self._current_confidence = 0.0
        self._running = False

        # Build UI
        self._build_ui()

        # Update timer
        self._update_timer()

    def set_brain_components(self, reflex, neural, memory, decision, learning, metrics):
        """Set brain component references."""
        self.reflex = reflex
        self.neural = neural
        self.memory = memory
        self.decision = decision
        self.learning = learning
        self.metrics = metrics

    def _build_ui(self):
        """Build the dashboard UI."""
        # Main grid
        self.root.grid_columnconfigure(0, weight=2)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        # ── LEFT PANEL ──────────────────────────────────
        left = ctk.CTkFrame(self.root, fg_color="#0a0a1a")
        left.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        left.grid_rowconfigure(3, weight=1)

        # Header
        header = ctk.CTkLabel(left, text="🧠 MICRO NEURAL BRAIN",
                              font=("Arial", 20, "bold"), text_color="#00b894")
        header.grid(row=0, column=0, pady=(10, 5))

        subtitle = ctk.CTkLabel(left, text="Cognitive System v1.0",
                                font=("Arial", 10), text_color="#636e72")
        subtitle.grid(row=1, column=0, pady=(0, 10))

        # Neural Activity Visualizer
        self.neural_viz = NeuralActivityVisualizer(left, width=500, height=200)
        self.neural_viz.grid(row=2, column=0, padx=10, pady=5, sticky="ew")

        # Brain Activity Frame
        self.brain_activity = BrainActivityFrame(left)
        self.brain_activity.grid(row=3, column=0, sticky="nsew", padx=10, pady=5)

        # ── RIGHT PANEL ─────────────────────────────────
        right = ctk.CTkFrame(self.root, fg_color="#0a0a1a")
        right.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        right.grid_columnconfigure(0, weight=1)

        # Intent Display
        intent_frame = ctk.CTkFrame(right, fg_color="#16213e")
        intent_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))

        ctk.CTkLabel(intent_frame, text="CURRENT INTENT",
                     font=("Arial", 9, "bold"), text_color="#636e72").pack(anchor="w", padx=10, pady=(5, 0))

        self.intent_label = ctk.CTkLabel(intent_frame, text="—",
                                         font=("Arial", 28, "bold"), text_color="#ffffff")
        self.intent_label.pack(anchor="w", padx=10, pady=(0, 2))

        self.confidence_bar = ctk.CTkProgressBar(intent_frame, width=200, height=12,
                                                 progress_color="#00b894")
        self.confidence_bar.pack(anchor="w", padx=10, pady=(0, 5))
        self.confidence_bar.set(0)

        self.confidence_label = ctk.CTkLabel(intent_frame, text="Confidence: 0%",
                                             font=("Arial", 10), text_color="#636e72")
        self.confidence_label.pack(anchor="w", padx=10, pady=(0, 5))

        # Stats Frame
        stats_frame = ctk.CTkFrame(right, fg_color="#16213e")
        stats_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)

        ctk.CTkLabel(stats_frame, text="SYSTEM STATISTICS",
                     font=("Arial", 9, "bold"), text_color="#636e72").pack(anchor="w", padx=10, pady=(5, 0))

        self.stats_labels = {}
        stats_items = [
            ("ram", "RAM Usage", ""),
            ("cpu", "CPU", ""),
            ("memory", "Memories", ""),
            ("habits", "Habits", ""),
            ("accuracy", "Accuracy", ""),
            ("responsetime", "Response", ""),
            ("actions", "Actions", ""),
        ]
        for key, label, _ in stats_items:
            row_frame = ctk.CTkFrame(stats_frame, fg_color="transparent")
            row_frame.pack(fill="x", padx=10, pady=1)
            ctk.CTkLabel(row_frame, text=label + ":",
                         font=("Arial", 10), text_color="#b2bec3").pack(side="left")
            val = ctk.CTkLabel(row_frame, text="—",
                               font=("Arial", 10, "bold"), text_color="#dfe6e9")
            val.pack(side="right")
            self.stats_labels[key] = val

        # Activity Log
        log_frame = ctk.CTkFrame(right, fg_color="#16213e")
        log_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        right.grid_rowconfigure(2, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(log_frame, text="ACTIVITY LOG",
                     font=("Arial", 9, "bold"), text_color="#636e72").grid(row=0, column=0, sticky="w", padx=10, pady=(5, 0))

        self.log_textbox = ctk.CTkTextbox(log_frame, height=150, font=("Consolas", 9))
        self.log_textbox.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.log_textbox.configure(state="disabled")

        # Control buttons
        control_frame = ctk.CTkFrame(right, fg_color="transparent")
        control_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=5)

        self.start_btn = ctk.CTkButton(control_frame, text="▶ Start",
                                       command=self._toggle_brain,
                                       fg_color="#00b894", hover_color="#00a381")
        self.start_btn.pack(side="left", padx=5)

        self.quit_btn = ctk.CTkButton(control_frame, text="✕ Quit",
                                      command=self._quit,
                                      fg_color="#d63031", hover_color="#b71c1c")
        self.quit_btn.pack(side="right", padx=5)

        # Input bar
        input_frame = ctk.CTkFrame(self.root, fg_color="#16213e")
        input_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 10))
        input_frame.grid_columnconfigure(0, weight=1)

        self.input_entry = ctk.CTkEntry(input_frame, placeholder_text="Enter command...",
                                        font=("Arial", 12))
        self.input_entry.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        self.input_entry.bind("<Return>", self._on_input)

        process_btn = ctk.CTkButton(input_frame, text="Process",
                                    command=self._on_input_click,
                                    fg_color="#6c5ce7", hover_color="#5a4bd1")
        process_btn.grid(row=0, column=1, padx=(0, 10), pady=10)

        # Status bar
        self.status_bar = ctk.CTkLabel(self.root, text="Ready",
                                       font=("Arial", 9), text_color="#636e72",
                                       anchor="w")
        self.status_bar.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 5))

    def _toggle_brain(self):
        """Start/stop the brain system."""
        if self._running:
            self._running = False
            self.neural_viz.stop()
            self.start_btn.configure(text="▶ Start", fg_color="#00b894")
            self.status_bar.configure(text="Brain paused")
        else:
            self._running = True
            self.neural_viz.start()
            self.start_btn.configure(text="⏸ Pause", fg_color="#fdcb6e")
            self.status_bar.configure(text="Brain active")

            # Set initial brain status
            self.brain_activity.set_brain_status("Reflex", "READY", True)
            self.brain_activity.set_brain_status("Memory", "READY", True)
            self.brain_activity.set_brain_status("Neural", "READY", True)
            self.brain_activity.set_brain_status("Decision", "READY", True)
            self.brain_activity.set_brain_status("Learning", "READY", True)

    def _on_input(self, event=None):
        """Handle input from entry field."""
        self._on_input_click()

    def _on_input_click(self):
        """Process user input."""
        text = self.input_entry.get().strip()
        if not text:
            return
        self.input_entry.delete(0, "end")
        self._process_text(text)

    def _process_text(self, text: str):
        """Process text through the brain system."""
        self.log(f"> {text}")

        if not self._running:
            self.log("System paused. Click Start to activate.")
            return

        if not all([self.reflex, self.neural, self.memory,
                    self.decision, self.learning, self.metrics]):
            self.log("Brain components not initialized.")
            return

        # 1. Reflex Brain (fast match)
        self.brain_activity.set_brain_status("Reflex", "ACTIVE", True)
        reflex_intent, reflex_conf, reflex_action = self.reflex.match_intent(text)
        self.brain_activity.set_brain_status("Reflex", "READY", False)

        # 2. Neural Brain (intent recognition)
        self.brain_activity.set_brain_status("Neural", "PROCESSING", True)
        nn_intent, nn_conf, probs = self.neural.recognize_intent(text)

        # Update neural visualizer
        activity = max(0.1, nn_conf)
        self.neural_viz.set_activity(activity)
        self.brain_activity.set_brain_status("Neural", "READY", False)

        # 3. Decision Brain - combine signals
        self.brain_activity.set_brain_status("Decision", "ACTIVE", True)

        # Use neural result if confident, otherwise reflex
        if nn_conf >= reflex_conf:
            intent, confidence = nn_intent, nn_conf
        else:
            intent, confidence = reflex_intent, reflex_conf

        # Get context
        context = {"reflex_intent": reflex_intent, "reflex_confidence": reflex_conf}
        memories = self.memory.search_memory(text, limit=3)

        action_plan = self.decision.decide(intent, confidence, context, memories, text)
        self.brain_activity.set_brain_status("Decision", "READY", False)

        # 4. Execute action
        if reflex_action:
            result = self.reflex.execute_action(reflex_action, text)
            self.log(f"  → {result['action']}: {result['message']} ({result['duration_ms']:.0f}ms)")
            self.metrics.log_action(reflex_action.name, result["success"], result["duration_ms"])
        else:
            self.log(f"  → {action_plan.action} (no direct action)")

        # 5. Memory Brain - save experience
        self.brain_activity.set_brain_status("Memory", "STORING", True)
        self.memory.save_episodic_memory(
            event=text,
            emotion="",
            importance=confidence,
            context=f"intent={intent}",
        )
        self.memory.log_activity(text, intent, action_plan.action,
                                 result="executed" if reflex_action else "planned",
                                 duration=result.get("duration_ms", 0) if reflex_action else 0,
                                 success=1 if (reflex_action and result.get("success")) else 0)
        self.brain_activity.set_brain_status("Memory", "READY", False)

        # 6. Learning Brain
        self.brain_activity.set_brain_status("Learning", "OBSERVING", True)
        self.learning.observe(
            intent=intent,
            action=action_plan.action,
            success=bool(reflex_action and result.get("success")) if reflex_action else True,
            duration_ms=result.get("duration_ms", 0) if reflex_action else 0,
            context={"query": text},
        )
        self.brain_activity.set_brain_status("Learning", "READY", False)

        # Update metrics
        self.metrics.log_intent(intent, confidence)
        self.metrics.set_memory_count(self.memory.get_memory_count())

        # Update UI
        self._current_intent = intent
        self._current_confidence = confidence
        self.intent_label.configure(text=intent)
        self.confidence_bar.set(confidence)
        self.confidence_label.configure(text=f"Confidence: {confidence:.1%}")

        if confidence < 0.3:
            self.confidence_bar.configure(progress_color="#d63031")
        elif confidence < 0.7:
            self.confidence_bar.configure(progress_color="#fdcb6e")
        else:
            self.confidence_bar.configure(progress_color="#00b894")

    def log(self, message: str):
        """Add message to activity log."""
        if not hasattr(self, 'log_textbox'):
            return
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", f"[{timestamp}] {message}\n")
        self.log_textbox.see("end")

        # Trim
        lines = self.log_textbox.get("1.0", "end").split("\n")
        if len(lines) > GUI_CONFIG["max_log_lines"]:
            self.log_textbox.delete("1.0", f"{len(lines) - GUI_CONFIG['max_log_lines'] + 1}.0")

        self.log_textbox.configure(state="disabled")

    def _update_timer(self):
        """Periodic UI update."""
        if not CTK_AVAILABLE:
            return

        if self.metrics and self._running:
            summary = self.metrics.get_summary()
            self.stats_labels["ram"].configure(
                text=f"{summary['ram_usage_mb']:.1f} MB / 50 MB"
            )
            self.stats_labels["cpu"].configure(
                text=f"{summary['cpu_percent']:.1f}%"
            )
            self.stats_labels["memory"].configure(
                text=str(summary["memory_count"])
            )
            self.stats_labels["habits"].configure(
                text=str(summary.get("habits_learned", 0))
            )
            self.stats_labels["accuracy"].configure(
                text=f"{summary['accuracy']:.1%}"
            )
            self.stats_labels["responsetime"].configure(
                text=f"{summary['avg_response_time_ms']:.0f}ms"
            )
            self.stats_labels["actions"].configure(
                text=str(summary["actions_executed"])
            )

        self.root.after(GUI_CONFIG["update_interval_ms"], self._update_timer)

    def _quit(self):
        """Quit the application."""
        self._running = False
        self.neural_viz.stop()
        self.root.quit()
        self.root.destroy()

    def run(self):
        """Start the dashboard main loop."""
        if not CTK_AVAILABLE:
            return
        self.root.mainloop()


# ═══════════════════════════════════════════════════════════
# LAUNCHER FUNCTION
# ═══════════════════════════════════════════════════════════

def launch_dashboard(reflex=None, neural=None, memory=None,
                     decision=None, learning=None, metrics=None):
    """
    Launch the brain dashboard with optional pre-initialized components.
    If components not provided, they are imported fresh.
    """
    if not CTK_AVAILABLE:
        print("Error: CustomTkinter not installed.")
        print("Install with: pip install customtkinter")
        return

    from brain.reflex import ReflexBrain
    from brain.neural import NeuralBrain
    from brain.memory import MemoryBrain
    from brain.decision import DecisionBrain
    from brain.learning import LearningBrain
    from utils.metrics import get_metrics

    dashboard = MicroBrainDashboard()
    dashboard.set_brain_components(
        reflex or ReflexBrain(),
        neural or NeuralBrain(),
        memory or MemoryBrain(),
        decision or DecisionBrain(),
        learning or LearningBrain(),
        metrics or get_metrics(),
    )
    dashboard.run()


if __name__ == "__main__":
    launch_dashboard()
