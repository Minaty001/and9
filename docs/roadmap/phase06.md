# Phase 06: Intent Detection

## Purpose
Classifies user queries into 28 intent categories using a lightweight NumPy neural network (128→64→32→28). Supports keyword-based fast path overrides for known commands, multi-intent detection, and multi-source confidence scoring combining NN confidence, query quality, historical accuracy, and keyword boost.

## Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `JARVIS_INTENT_INPUT_DIM` | 128 | Input embedding dimension |
| `JARVIS_INTENT_HIDDEN_1` | 64 | First hidden layer |
| `JARVIS_INTENT_HIDDEN_2` | 32 | Second hidden layer |
| `JARVIS_INTENT_OUTPUT_DIM` | 28 | Intent classes |
| `JARVIS_INTENT_MIN_CONFIDENCE` | 0.5 | Clarification threshold |
| `JARVIS_INTENT_HIGH_CONFIDENCE` | 0.85 | Auto-execution threshold |

## Architecture
```
IntentClassifier
  ├── Fast path: KEYWORD_OVERRIDES dict
  └── NN path: TinyNeuralNetwork
        Input(128) → Dense(64, ReLU) → Dense(32, ReLU) → Dense(28, Softmax)
ConfidenceScorer
  └── score = nn_confidence*0.5 + query_quality*0.15 + historical*0.15 + keyword_boost*0.2
```

## Code
```python
class TinyNeuralNetwork:
    def predict(self, embedding: List[float]) -> np.ndarray:
        x = np.array(embedding).reshape(1, -1)
        a1 = np.maximum(0, np.dot(x, self._weights["w1"]) + self._biases["b1"])
        a2 = np.maximum(0, np.dot(a1, self._weights["w2"]) + self._biases["b2"])
        z3 = np.dot(a2, self._weights["w3"]) + self._biases["b3"]
        probs = np.exp(z3 - np.max(z3)) / np.sum(np.exp(z3 - np.max(z3)))
        return probs.flatten()

class IntentClassifier:
    def classify(self, embedding, text="") -> IntentResult:
        if text.lower() in self.KEYWORD_OVERRIDES:
            return IntentResult(intent=..., confidence=0.95, ...)
        intent_name, confidence, _ = self.nn.predict_intent(embedding)
        return IntentResult(intent=intent_name, confidence=confidence, ...)
```

## Location
`app/brain/neural/` — intent detection module
