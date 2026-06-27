# AND9 OS — Working Files, Features, Functions, and Locations

This document outlines the verified active modules, their core features, functions, and exact locations in the repository. All listed files have been validated through a 106-test suite (`pytest`) and are fully operational.

---

## 🧠 Cognitive Orchestrators

### 1. AND9 Orchestrator
- **Location:** `app/and9/brain/orchestrator.py` (Delegated entry in `app/and9/and9.py`)
- **Feature:** Multi-brain cognitive execution pipeline.
- **Function:** Classifies user query, normalizes Hinglish/English, evaluates confidence scoring, checks routine suggestions, dispatches device commands to the Android Executor, and traces execution logs to `activities.db`.

### 2. LLM Orchestrator (JARVIS)
- **Location:** `app/core/orchestrator.py`
- **Feature:** High-level LLM reasoning, goal-planning, and multi-layered memory consolidation.
- **Function:** Understands user emotional state, builds context, validates facts via Truth Engine, and manages conversational and task-oriented agents (Coding, Research, Assistant).

---

## 🔀 NLU & Routing

### 1. Intent Router
- **Location:** `app/and9/router/intent_router.py`
- **Feature:** Tiered intent classification with offline fallback.
- **Function:** Checks emergency, calls, app opening, and hardware controls via regex triggers first. Falls back to the trained offline `micro_brain` neural model for classification.

### 2. Confidence Scorer
- **Location:** `app/and9/router/confidence_scorer.py`
- **Feature:** Query classification scoring.
- **Function:** Scores intent match quality based on parameters and intent-specific keyword triggers.

### 3. Entity Extractor
- **Location:** `app/and9/router/entity_extractor.py`
- **Feature:** Heuristic parameter parsing.
- **Function:** Parses contacts, phone numbers, app names, durations, and text bodies.

### 4. Query Normalizer
- **Location:** `app/and9/router/normalizer.py`
- **Feature:** Hinglish-to-English translation.
- **Function:** Translates common Hinglish/Hindi phrasing into standardized English queries.

---

## ⚡ Execution Layer

### 1. Android Action Executor
- **Location:** `app/and9/android/android_executor.py`
- **Feature:** Safe hardware/system control.
- **Function:** Dispatches calls, messages, app launches, volume/flashlight toggles, alarm setup, and YouTube media play.

### 2. Time & Date Parser
- **Location:** `app/and9/utils/time_parser.py`
- **Feature:** Natural language time resolution.
- **Function:** Resolves relative and absolute times (e.g. "next monday at 7 am", "after 5 seconds").

### 3. City Timezone Utility
- **Location:** `app/and9/utils/timezone_utils.py`
- **Feature:** Location-aware time lookups.
- **Function:** Returns timezone-correct current time for major Indian cities.

---

## 💾 Memory & Subsystems

### 1. Four-Layer Memory
- **Location:** `app/core/memory.py`
- **Feature:** Cognitive memory storage.
- **Function:** Implements Working, Episodic, Semantic, and Procedural memory backed by SQLite/Supabase.

### 2. Truth Engine
- **Location:** `app/core/truth_engine.py`
- **Feature:** Fact verification.
- **Function:** Validates memory context prior to LLM submission to prevent hallucination.

### 3. Event and Goal Trackers
- **Location:** `app/core/events.py` & `app/core/goal_tracker.py`
- **Feature:** Actionable planning and alerts.
- **Function:** Manages scheduled reminders, calendars, goals, and daily review reflections.

### 4. Server-Side Timers
- **Location:** `app/core/timer.py` & `app/reminders/scheduler.py`
- **Feature:** Event alerts.
- **Function:** Tracks countdowns, recurring events, and snoozes.

---

## 🔬 Offline Neural Brain (micro_brain)

### 1. Tiny Neural Network
- **Location:** `micro_brain/brain/neural.py`
- **Feature:** Feedforward neural classifier.
- **Function:** Predicts 23 intents from text embeddings. Optimized for 50MB RAM.

### 2. Dataset Generator
- **Location:** `micro_brain/datasets/generate_dataset.py`
- **Feature:** Multilingual dataset builder.
- **Function:** Generates large-scale Hinglish/English queries for training (including custom math, human science, and history templates).

### 3. Model Trainer
- **Location:** `micro_brain/training/train.py`
- **Feature:** Pipeline training and quantization.
- **Function:** Trains feedforward network, exports weights, and quantizes to INT8.
