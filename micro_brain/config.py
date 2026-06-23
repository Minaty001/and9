"""
╔══════════════════════════════════════════════════╗
║        MICRO NEURAL BRAIN - CONFIGURATION        ║
║        Human Brain Inspired Cognitive System     ║
╚══════════════════════════════════════════════════╝

All configurable parameters for the Micro Neural Brain.
Optimized for 50MB RAM budget in Android Termux.
"""

import os
from pathlib import Path

# ─── Base Paths ───────────────────────────────────────────────
BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
BRAIN_DIR = BASE_DIR / "brain"
MODELS_DIR = BASE_DIR / "models"
DB_DIR = BASE_DIR / "database"
DATASETS_DIR = BASE_DIR / "datasets"
GUI_DIR = BASE_DIR / "gui"
TRAINING_DIR = BASE_DIR / "training"
UTILS_DIR = BASE_DIR / "utils"

# ─── Resource Limits (50MB Target) ──────────────────────────
RAM_BUDGET = {
    "python_runtime": 20,   # MB
    "neural_model": 2,      # MB  (max INT8 quantized model)
    "sqlite": 5,            # MB
    "memory_cache": 5,      # MB
    "gui": 10,              # MB
    "buffers": 8,           # MB
    "total_max": 50,        # MB
}

# ─── Neural Network ──────────────────────────────────────────
NN_CONFIG = {
    "input_dim": 128,         # Embedding dimension
    "hidden_1": 64,          # First hidden layer
    "hidden_2": 32,          # Second hidden layer
    "learning_rate": 0.01,
    "epochs": 100,
    "batch_size": 32,
    "validation_split": 0.2,
    "test_split": 0.1,
    "max_text_length": 50,   # max chars for input
    "model_path": str(MODELS_DIR / "intent_model.npz"),
    "vocab_path": str(MODELS_DIR / "vocab.json"),
    "max_model_size_mb": 2.0,
    "dtype": "int8",         # quantized to INT8
}

# ─── Supported Intents ───────────────────────────────────────
INTENTS = [
    "OPEN_APP",
    "CLOSE_APP",
    "PLAY_MUSIC",
    "PAUSE_MUSIC",
    "SEARCH_WEB",
    "WEATHER",
    "TIME",
    "DATE",
    "REMINDER",
    "CALL",
    "MESSAGE",
    "CAMERA",
    "FLASHLIGHT_ON",
    "FLASHLIGHT_OFF",
    "VOLUME_UP",
    "VOLUME_DOWN",
    "HOME",
    "BACK",
    "SETTING",
    "UNKNOWN",
]

INTENT_LABELS = {name: idx for idx, name in enumerate(INTENTS)}

# ─── Memory Brain ────────────────────────────────────────────
MEMORY_CONFIG = {
    "db_path": str(DB_DIR / "memory.db"),
    "working_memory_size": 10,      # max items
    "short_term_limit": 100,
    "long_term_limit": 1000,
    "importance_decay": 0.01,       # per day
    "forget_threshold": 0.1,        # auto-forget below this
    "promote_threshold": 0.8,       # auto-promote above this
    "max_cache_entries": 500,
}

# ─── Reflex Brain ────────────────────────────────────────────
REFLEX_CONFIG = {
    "cache_size": 100,
    "response_time_target_ms": 50,
    "action_registry_path": str(BRAIN_DIR / "action_registry.json"),
}

# ─── Learning Brain ──────────────────────────────────────────
LEARNING_CONFIG = {
    "min_observations_for_habit": 3,
    "learning_rate": 0.1,
    "decay_factor": 0.95,
    "pattern_window_days": 30,
    "max_habits": 50,
    "prediction_confidence_threshold": 0.6,
}

# ─── Decision Brain ──────────────────────────────────────────
DECISION_CONFIG = {
    "min_confidence_to_act": 0.5,
    "fallback_intent": "UNKNOWN",
    "max_action_history": 50,
}

# ─── GUI ─────────────────────────────────────────────────────
GUI_CONFIG = {
    "window_size": (1024, 700),
    "theme": "dark",
    "update_interval_ms": 1000,   # UI refresh rate
    "neural_visualizer_update_ms": 100,
    "max_log_lines": 100,
}

# ─── Database Schema ─────────────────────────────────────────
DB_SCHEMA = {
    "working_memory": """
        CREATE TABLE IF NOT EXISTS working_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT,
            context TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            importance REAL DEFAULT 0.5,
            access_count INTEGER DEFAULT 1,
            last_accessed DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "episodic_memory": """
        CREATE TABLE IF NOT EXISTS episodic_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            emotion TEXT,
            importance REAL DEFAULT 0.5,
            context TEXT
        )
    """,
    "semantic_memory": """
        CREATE TABLE IF NOT EXISTS semantic_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE,
            value TEXT,
            category TEXT,
            confidence REAL DEFAULT 1.0,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "user_preferences": """
        CREATE TABLE IF NOT EXISTS user_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pref_key TEXT UNIQUE,
            pref_value TEXT,
            category TEXT,
            confidence REAL DEFAULT 1.0,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "skills": """
        CREATE TABLE IF NOT EXISTS skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            description TEXT,
            pattern TEXT,
            enabled INTEGER DEFAULT 1,
            proficiency REAL DEFAULT 0.0,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "habits": """
        CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            pattern TEXT,
            frequency TEXT,
            time_of_day TEXT,
            day_of_week TEXT,
            confidence REAL DEFAULT 0.0,
            occurrences INTEGER DEFAULT 0,
            last_triggered DATETIME,
            enabled INTEGER DEFAULT 1,
            created DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "goals": """
        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            goal TEXT,
            status TEXT DEFAULT 'active',
            progress REAL DEFAULT 0.0,
            deadline DATETIME,
            created DATETIME DEFAULT CURRENT_TIMESTAMP,
            completed DATETIME
        )
    """,
    "activities": """
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            query TEXT,
            intent TEXT,
            action TEXT,
            result TEXT,
            duration REAL,
            success INTEGER
        )
    """,
    "metrics": """
        CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            metric_name TEXT,
            metric_value REAL,
            details TEXT
        )
    """,
}

# ─── Android / Termux Compatibility ──────────────────────────
ANDROID_CONFIG = {
    "termux": os.environ.get("TERMUX_VERSION") is not None,
    "termux_api_available": False,  # detected at runtime
    "adb_available": False,
    "package_manager": "pm" if os.environ.get("TERMUX_VERSION") else "which",
}

# ─── Logging ─────────────────────────────────────────────────
LOG_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    "file": str(BASE_DIR / "brain.log"),
    "max_size_mb": 5,
    "backup_count": 2,
}

# ─── LLM Integration (Future) ────────────────────────────────
LLM_CONFIG = {
    "enabled": False,
    "provider": "openai",
    "model": "gpt-4o-mini",
    "api_key": "",  # set via env or config
    "max_tokens": 256,
    "temperature": 0.7,
    "timeout": 30,
}
