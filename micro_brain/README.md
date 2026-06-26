# Micro Neural Brain

A lightweight offline cognitive system for Android Termux — intent recognition, memory, reflexes, and learning using pure NumPy (no LLM, no cloud).

> **This is NOT a chatbot.**  
> **This is NOT an LLM.**  
> This is a **Micro Neural Cognitive System** with a 50MB RAM budget.

## Architecture — Five Brains

```
Input → Reflex → Neural → Memory → Decision → Learning
         ↑          ↓         ↑         ↓          ↓
     (keywords)  (NN)    (SQLite)   (actions)  (habits)
```

| # | Brain | File | Purpose | Speed |
|---|-------|------|---------|-------|
| 1 | **Reflex** | `brain/reflex.py` | Keyword/pattern matching → instant actions | <50ms |
| 2 | **Memory** | `brain/memory.py` | 8-layer SQLite memory (working, episodic, semantic, preferences, skills, habits, goals, activity log) | <10ms |
| 3 | **Neural** | `brain/neural.py` | 128→64→32→20 fully-connected network for intent classification | <5ms |
| 4 | **Decision** | `brain/decision.py` | Combines Reflex + Neural scores, queries memory, produces ActionPlan | <20ms |
| 5 | **Learning** | `brain/learning.py` | Frequency/time-based habit discovery from past actions | Background |

## Usage

```bash
# Interactive console
python main.py

# GUI dashboard (requires: pip install customtkinter)
python main.py --gui

# Train the neural network
python main.py --train

# Evaluate model performance
python main.py --evaluate

# Generate training dataset
python main.py --generate

# CLI one-shot
python main.py --cli "torch on"
```

## Training

- **Model**: 3-layer dense NN (128 → 64 → 32 → 20 intents)
- **Training data**: 5000+ Hindi/English/Hinglish examples across 20 intents
- **Accuracy**: ~68-70% (test set), 9.8s training for 100 epochs
- **Quantization**: INT8 model also generated (12KB vs 42KB)

### Intent Classes

`OPEN_APP`, `CLOSE_APP`, `PLAY_MUSIC`, `PAUSE_MUSIC`, `SEARCH_WEB`, `WEATHER`, `TIME`, `DATE`, `FLASHLIGHT_ON`, `FLASHLIGHT_OFF`, `VOLUME_UP`, `VOLUME_DOWN`, `HOME`, `BACK`, `SETTING`, `REMINDER`, `CALL`, `MESSAGE`, `CAMERA`, `UNKNOWN`

## Supported Reflex Actions

| Action | Android | Desktop |
|--------|---------|---------|
| Open app | `am start` via Termux | Simulated |
| Close app | Simulated | Simulated |
| Flashlight on/off | `termux-torch on/off` | Simulated |
| Volume up/down | `input keyevent 24/25` | Simulated |
| Home/Back | `input keyevent 3/4` | Simulated |
| Web search, weather, time, date | Python response | Python response |

### 📅 Timezone, Alarm & Reminder Commands

- **Time / Timezone in City**: "what is the time in Mumbai", "current time in Delhi", "dilli ka time"
- **Set Alarm**: "alarm 7 am", "alarm tomorrow 7 am", "alarm after 5 minutes", "alarm lagao 7 baje"
- **Set Reminder**: "remind me after 5 min", "remind me tomorrow", "remind me to call mummy at 7 pm", "5 minute baad yaad dilana"

## Standalone Status

micro_brain is an **independent subsystem** within the JARVIS PCOS project tree. It:
- Has **zero dependencies** on `app/` — runs standalone
- Uses its own virtualenv (`brain_venv/`, numpy + psutil)
- Is **not imported** by the main Flask app
- Shares the same project root but operates as a separate tool

## Project Structure

```
micro_brain/
├── main.py                 ← Entry point (CLI / GUI / Train / Eval)
├── config.py               ← All configuration
├── __init__.py             ← Package exports
├── brain/                  ← Five brains
│   ├── reflex.py
│   ├── neural.py
│   ├── memory.py
│   ├── decision.py
│   └── learning.py
├── training/
│   ├── train.py
│   └── evaluate.py
├── datasets/
│   ├── generate_dataset.py
│   └── intents.json        ← 5000+ training examples
├── models/
│   ├── intent_model.npz
│   ├── intent_model_int8.npz
│   └── vocab.json
├── database/
│   └── memory.db           ← SQLite memory store
├── gui/
│   └── dashboard.py        ← CustomTkinter dashboard
└── utils/
    ├── logger.py
    └── metrics.py
```

## Requirements

- Python 3.10+
- numpy (for neural network)
- psutil (for system stats in console)
- customtkinter (optional, for GUI mode)

Install: `pip install numpy psutil customtkinter`
