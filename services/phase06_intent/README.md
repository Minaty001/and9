# Phase 6: Intent Detection

## Overview

Classifies user queries into 28 intent categories using a lightweight NumPy neural network (128→64→32→28). Supports keyword-based fast path overrides, multi-intent detection, and multi-source confidence scoring.

## Architecture

### TinyNeuralNetwork
```
Input(128) → Dense(64, ReLU) → Dense(32, ReLU) → Dense(28, Softmax)
```
- NumPy-only, no external ML framework
- <2MB model size (INT8 quantized)
- ~1ms inference on device

### IntentClassifier
- **Fast path**: keyword overrides for known commands (no NN needed)
- **NN path**: neural network for novel queries
- Returns top-K predictions with confidence

### ConfidenceScorer
Combines multiple signals:
```python
score = nn_confidence * 0.5 + query_quality * 0.15 + historical * 0.15 + keyword_boost * 0.2
```

## Intent Categories (28)

| Category | Intents |
|----------|---------|
| App Control | OPEN_APP, CLOSE_APP, HOME, BACK, SETTING |
| Media | PLAY_MUSIC, PAUSE_MUSIC, CAMERA |
| Device | FLASHLIGHT_ON/OFF, VOLUME_UP/DOWN |
| Communication | CALL, MESSAGE |
| Information | SEARCH_WEB, WEATHER, TIME, DATE |
| Productivity | REMINDER |
| Knowledge | PYTHON_CODING, GENERAL_KNOWLEDGE, MEDICINE_KNOWLEDGE, MOVIE_KNOWLEDGE |
| System | CHAT, CAPABILITIES, AI_NEWS_MODELS, WEB_CODING |
| Fallback | UNKNOWN |

## Usage

```python
from services.phase06_intent import IntentDetectionService

svc = IntentDetectionService()
await svc.initialize()

# Detect intent from embedding
result = await svc.detect(embedding_vector, "open whatsapp")
print(f"Intent: {result.intent} (conf={result.confidence:.2f})")

# Check if clarification needed
if await svc.requires_clarification(result.confidence):
    print("Please clarify your request")
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `JARVIS_INTENT_INPUT_DIM` | 128 | Input embedding dimension |
| `JARVIS_INTENT_HIDDEN_1` | 64 | First hidden layer |
| `JARVIS_INTENT_HIDDEN_2` | 32 | Second hidden layer |
| `JARVIS_INTENT_OUTPUT_DIM` | 28 | Intent classes |
| `JARVIS_INTENT_MIN_CONFIDENCE` | 0.5 | Clarification threshold |
| `JARVIS_INTENT_HIGH_CONFIDENCE` | 0.85 | Auto-execution threshold |

## Integration

```python
# Wire into Phase 3 Query Pipeline
from services.phase03_query import PipelineStage

async def intent_handler(ctx):
    embedding = ctx.get("embedding")
    text = ctx.get("query", "")
    result = await intent_svc.detect(embedding, text)
    ctx["intent"] = result.intent
    ctx["confidence"] = result.confidence
    return StageResult(stage=PipelineStage.INTENT, data=ctx)
```
