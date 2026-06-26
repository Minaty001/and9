"""
╔══════════════════════════════════════════════════╗
║           BRAIN 3: NEURAL BRAIN                  ║
║   Tiny Neural Network for Intent Recognition     ║
╚══════════════════════════════════════════════════╝

Architecture:
    Input (128-dim embedding)
    → Dense(128, ReLU)
    → Dense(64, ReLU)
    → Dense(32, ReLU)
    → Dense(num_intents, Softmax)

Model Size: <2MB (INT8 quantized)
Framework: NumPy-based (lightweight, no PyTorch dependency)
"""
from __future__ import annotations

import os
import json
import math
import time
try:
    import numpy as np
except ImportError:  # pragma: no cover - exercised only in minimal envs
    np = None
from typing import Optional, List, Tuple, Dict
from dataclasses import dataclass

from config import NN_CONFIG, INTENTS, INTENT_LABELS
from utils.logger import get_logger

logger = get_logger()


def _require_numpy() -> None:
    """Raise a clear error if NumPy-backed features are unavailable."""
    if np is None:
        raise ImportError(
            "NumPy is required for micro_brain neural features. "
            "Install dependencies with `pip install numpy`."
        )


@dataclass
class NeuralConfig:
    """Neural network hyperparameters."""
    input_dim: int = NN_CONFIG["input_dim"]
    hidden_1: int = NN_CONFIG["hidden_1"]
    hidden_2: int = NN_CONFIG["hidden_2"]
    output_dim: int = len(INTENTS)
    learning_rate: float = NN_CONFIG["learning_rate"]
    epochs: int = NN_CONFIG["epochs"]
    batch_size: int = NN_CONFIG["batch_size"]
    model_path: str = NN_CONFIG["model_path"]
    vocab_path: str = NN_CONFIG["vocab_path"]


class TextEmbedding:
    """
    Lightweight text-to-vector embedding.
    No pre-trained models needed. Uses character-level features.
    Output: 128-dim vector
    """

    # Class-level constant data (never changes between instances)
    CHAR_SET = (
        "abcdefghijklmnopqrstuvwxyz"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "0123456789"
        " .,!?-+:@#$%&*()[]{}'\""
        "अआइईउऊऋएऐओऔकखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसह"
        "ािीुूृेैोौंः्"
        "़ऽ"
    )

    # Intent-specific keyword groups (dims 92-127) — created once
    _KEYWORD_GROUPS = [
        ["open", "kholo", "khol", "launch", "start"],
        ["close", "band", "exit", "hatao"],
        ["play", "music", "song", "gaana", "bajao"],
        ["pause", "stop", "rok"],
        ["search", "google", "dhundh", "dhoondh", "khoj", "find"],
        ["weather", "mausam", "temperature"],
        ["time", "samay", "kitna", "bajaa", "baje", "ghanti"],
        ["date", "tareekh", "din"],
        ["remind", "reminder", "yaad", "alarm"],
        ["call", "phone", "dial", "fone"],
        ["message", "text", "sms", "msg", "bhej"],
        ["camera", "photo", "picture", "selfie"],
        ["flash", "torch", "light"],
        ["volume", "aawaz", "sound"],
        ["home", "gher"],
        ["back", "peeche", "wapis", "pichh"],
        ["setting"],
        ["whatsapp", "wa"],
        ["youtube", "yt"],
        ["telegram", "insta", "instagram"],
        ["maps", "map"],
        ["mail", "gmail"],
        ["calculator", "calc"],
        ["calendar"],
        ["clock", "alarm"],
        ["playstore", "store", "play store"],
        ["spotify", "music player"],
        ["wifi", "bluetooth"],
        ["up", "increase", "badhao", "zyada", "tez", "plus", "aur"],
        ["down", "decrease", "kam", "ghatao", "minus", "halka"],
        ["weather", "mausam", "temperature"],
        ["kholo", "khol", "chalu", "jalao"],
        ["band", "off", "bujhao"],
        ["unknown", "hello", "hi", "how"],
        ["camera", "photo", "selfie"],
        ["phone", "contact", "number", "dial"],
    ]

    def __init__(self, dim: int = 128):
        _require_numpy()
        self.dim = dim
        self.char_set = self.CHAR_SET
        self.char_to_idx = {c: i for i, c in enumerate(self.CHAR_SET)}
        self.vocab_size = len(self.CHAR_SET)
        self._zeros = np.zeros(dim, dtype=np.float32)  # reusable empty array

    def embed(self, text: str) -> np.ndarray:
        """
        Convert text to 128-dim embedding vector.

        Hybrid approach combining character-level features for robustness
        with word-level features for discrimination.
        """
        text = str(text).strip()
        if not text:
            return self._zeros.copy()

        embedding = self._zeros.copy()
        text_lower = text.lower()
        words = text_lower.split()
        total_chars = len(text_lower)

        # ── 1. Character frequency (dims 0-39) ─────────────────
        ct = self.char_to_idx
        for char in text_lower[:80]:
            idx = ct.get(char)
            if idx is not None:
                embedding[idx % 40] += 1.0
        s = embedding[:40].sum()
        if s > 0:
            embedding[:40] /= s

        # ── 2. Character bigrams via hashing (dims 40-55) ──────
        seen = set()
        n_minus_1 = len(text_lower) - 1
        for i in range(n_minus_1):
            bg = text_lower[i:i + 2]
            if bg not in seen:
                seen.add(bg)
                h = (ord(bg[0]) * 31 + ord(bg[-1])) & 0x0F
                embedding[40 + h] += 0.1

        # ── 3. Word-level features (dims 56-71) ───────────────
        for word in words:
            h = hash(word) & 0x0F
            embedding[56 + h] += 1.0
        for i in range(len(words) - 1):
            h = hash(words[i] + '_' + words[i + 1]) & 0x0F
            embedding[64 + h] += 1.0

        # ── 4. Direction / opposition (dims 72-79) ────────────
        wset = set(words) if len(words) > 3 else words  # fast membership for short lists
        embedding[72] = 1.0 if 'on' in wset else 0.0
        embedding[73] = 1.0 if 'off' in wset else 0.0
        embedding[74] = 1.0 if 'up' in wset else 0.0
        embedding[75] = 1.0 if 'down' in wset else 0.0
        embedding[76] = 1.0 if ('play' in text_lower or 'bajao' in text_lower or 'chalao' in text_lower) else 0.0
        embedding[77] = 1.0 if ('pause' in text_lower or 'stop' in text_lower or 'rok' in text_lower or 'band' in text_lower) else 0.0
        embedding[78] = 1.0 if ('kholo' in text_lower or 'open' in text_lower or 'chalu' in text_lower or 'on' in wset or 'jalao' in text_lower) else 0.0
        embedding[79] = 1.0 if ('badhao' in text_lower or 'increase' in text_lower or 'zyada' in text_lower or 'tez' in text_lower) else 0.0

        # ── 5. Structural / script features (dims 80-91) ──────
        n_words = len(words)
        embedding[80] = min(1.0, total_chars / 60.0)
        embedding[81] = min(1.0, n_words / 10.0)
        embedding[82] = 1.0 if n_words == 1 else 0.0
        embedding[83] = 1.0 if '?' in text else 0.0
        embedding[84] = 1.0 if '!' in text else 0.0

        devanagari = sum(1 for c in text if '\u0900' <= c <= '\u097F')
        embedding[85] = min(1.0, devanagari / max(1, total_chars))
        english = sum(1 for c in text_lower if 'a' <= c <= 'z')
        embedding[86] = min(1.0, english / max(1, total_chars))
        digits = sum(1 for c in text if c.isdigit())
        embedding[87] = min(1.0, digits / max(1, total_chars))

        embedding[88] = 1.0 if any(k in words for k in ("please", "pls", "karo", "kar", "dijiye")) else 0.0

        # Hindi-specific action verb markers
        embedding[89] = 1.0 if any(c in text_lower for c in "kholochalaobajaobataobadhaokambanddhundh") else 0.0

        # ── 6. Intent-specific keyword groups (dims 92-127) ────
        for i, kws in enumerate(self._KEYWORD_GROUPS):
            idx = 92 + i
            if idx < 128:
                embedding[idx] = 1.0 if any(kw in text_lower for kw in kws) else 0.0

        return embedding


class DenseLayer:
    """A fully-connected neural network layer."""

    def __init__(self, input_size: int, output_size: int,
                 activation: str = "relu"):
        _require_numpy()
        self.input_size = input_size
        self.output_size = output_size
        self.activation = activation

        # He initialization
        scale = math.sqrt(2.0 / input_size)
        self.weights = np.random.randn(input_size, output_size).astype(np.float32) * scale
        self.bias = np.zeros(output_size, dtype=np.float32)

        # Cache for backprop
        self.input_cache = None
        self.z_cache = None
        self._training = False  # Set True during training forward/backward

    def forward(self, x: np.ndarray) -> np.ndarray:
        """Forward pass."""
        self.input_cache = x.copy() if self._training else None
        z = x @ self.weights + self.bias
        self.z_cache = z.copy() if self._training else None

        if self.activation == "relu":
            return np.maximum(0, z)
        elif self.activation == "softmax":
            exp_z = np.exp(z - np.max(z, axis=-1, keepdims=True))
            return exp_z / (np.sum(exp_z, axis=-1, keepdims=True) + 1e-10)
        return z

    def backward(self, grad: np.ndarray, lr: float) -> np.ndarray:
        """Backward pass with gradient descent."""
        if self.activation == "relu":
            grad = grad * (self.z_cache > 0).astype(np.float32)

        grad_weights = self.input_cache.T @ grad
        grad_bias = np.sum(grad, axis=0)
        grad_input = grad @ self.weights.T

        # Update weights
        self.weights -= lr * grad_weights
        self.bias -= lr * grad_bias

        return grad_input


class TinyNeuralNetwork:
    """
    Tiny Feed-Forward Neural Network.

    Architecture: 128 → 64 → 32 → num_intents
    Activations: ReLU → ReLU → ReLU → Softmax
    Loss: Cross-Entropy
    """

    def __init__(self, config: Optional[NeuralConfig] = None):
        _require_numpy()
        self.config = config or NeuralConfig()
        self.layers: List[DenseLayer] = []
        self._build()

        self.embedding = TextEmbedding(self.config.input_dim)
        self.trained = False
        self.loss_history = []

    def _build(self):
        """Build the network architecture."""
        sizes = [
            self.config.input_dim,
            self.config.hidden_1,
            self.config.hidden_2,
            self.config.output_dim,
        ]
        # Exactly one activation per layer: len(sizes)-1 = 3 layers
        activations = ["relu", "relu", "softmax"]

        for i in range(len(sizes) - 1):
            layer = DenseLayer(sizes[i], sizes[i + 1], activations[i])
            self.layers.append(layer)

        logger.info(f"NeuralBrain: Built network {sizes}")

    def forward(self, x: np.ndarray) -> np.ndarray:
        """Full forward pass through all layers."""
        # Set training flag on all layers
        for layer in self.layers:
            layer._training = False

        out = x
        for layer in self.layers:
            out = layer.forward(out)
        return out

    def predict(self, text: str) -> Tuple[str, float, np.ndarray]:
        """
        Predict intent from text.

        Returns:
            (intent_name, confidence, all_probabilities)
        """
        vector = self.embedding.embed(text)
        vector = vector.reshape(1, -1)
        probs = self.forward(vector)
        probs = probs.flatten()

        pred_idx = int(np.argmax(probs))
        confidence = float(probs[pred_idx])

        intent = INTENTS[pred_idx] if pred_idx < len(INTENTS) else "UNKNOWN"

        return intent, confidence, probs

    def train(self, texts: List[str], labels: List[int],
              val_texts: Optional[List[str]] = None,
              val_labels: Optional[List[int]] = None,
              epochs: Optional[int] = None,
              lr: Optional[float] = None) -> Dict:
        """
        Train the network on intent data.

        Returns training history.
        """
        epochs = epochs or self.config.epochs
        lr = lr or self.config.learning_rate
        batch_size = self.config.batch_size

        # Embed all texts
        X = np.array([self.embedding.embed(t) for t in texts], dtype=np.float32)
        y = np.array(labels, dtype=np.int64)

        # One-hot encode labels
        y_onehot = np.zeros((len(y), self.config.output_dim), dtype=np.float32)
        y_onehot[np.arange(len(y)), y] = 1.0

        # Validation data
        X_val = None
        y_val_onehot = None
        if val_texts and val_labels:
            X_val = np.array([self.embedding.embed(t) for t in val_texts], dtype=np.float32)
            y_val = np.array(val_labels, dtype=np.int64)
            y_val_onehot = np.zeros((len(y_val), self.config.output_dim), dtype=np.float32)
            y_val_onehot[np.arange(len(y_val)), y_val] = 1.0

        n_samples = len(X)
        history = {
            "train_loss": [],
            "val_loss": [],
            "train_acc": [],
            "val_acc": [],
        }

        logger.info(f"NeuralBrain: Training {n_samples} samples for {epochs} epochs")

        for epoch in range(epochs):
            # Shuffle
            perm = np.random.permutation(n_samples)
            X_shuffled = X[perm]
            y_shuffled = y_onehot[perm]

            epoch_loss = 0.0
            epoch_correct = 0
            epoch_total = 0

            # Mini-batch training
            for start in range(0, n_samples, batch_size):
                end = min(start + batch_size, n_samples)
                X_batch = X_shuffled[start:end]
                y_batch = y_shuffled[start:end]

                # Set training flag
                for layer in self.layers:
                    layer._training = True

                # Forward
                out = X_batch
                for layer in self.layers:
                    out = layer.forward(out)

                # Cross-entropy loss
                loss = -np.sum(y_batch * np.log(out + 1e-10)) / len(X_batch)
                epoch_loss += loss

                # Accuracy
                preds = np.argmax(out, axis=1)
                true = np.argmax(y_batch, axis=1)
                epoch_correct += np.sum(preds == true)
                epoch_total += len(X_batch)

                # Backward
                grad = out - y_batch  # dL/dsoftmax
                for layer in reversed(self.layers):
                    grad = layer.backward(grad, lr)

            avg_loss = epoch_loss / (n_samples / batch_size + 1)
            train_acc = epoch_correct / epoch_total
            history["train_loss"].append(float(avg_loss))
            history["train_acc"].append(float(train_acc))

            # Validation
            if X_val is not None:
                for layer in self.layers:
                    layer._training = False
                val_out = X_val
                for layer in self.layers:
                    val_out = layer.forward(val_out)
                val_loss = float(-np.sum(y_val_onehot * np.log(val_out + 1e-10)) / len(X_val))
                val_preds = np.argmax(val_out, axis=1)
                val_true = np.argmax(y_val_onehot, axis=1)
                val_acc = float(np.sum(val_preds == val_true) / len(X_val))
                history["val_loss"].append(val_loss)
                history["val_acc"].append(val_acc)

            if (epoch + 1) % 10 == 0 or epoch == 0:
                val_str = f", val_loss={history['val_loss'][-1]:.4f}, val_acc={history['val_acc'][-1]:.4f}" if X_val is not None else ""
                logger.info(
                    f"  Epoch {epoch+1}/{epochs}: loss={avg_loss:.4f}, acc={train_acc:.4f}{val_str}"
                )

        self.trained = True
        self.loss_history = history["train_loss"]
        logger.info(f"NeuralBrain: Training complete. Final acc={train_acc:.4f}")

        return history

    def evaluate(self, texts: List[str], labels: List[int]) -> Dict:
        """Evaluate the network on test data."""
        X = np.array([self.embedding.embed(t) for t in texts], dtype=np.float32)
        y = np.array(labels, dtype=np.int64)

        for layer in self.layers:
            layer._training = False
        out = X
        for layer in self.layers:
            out = layer.forward(out)

        preds = np.argmax(out, axis=1)
        correct = np.sum(preds == y)
        accuracy = correct / len(y)

        # Per-class metrics
        class_metrics = {}
        for i, intent in enumerate(INTENTS):
            mask = y == i
            if np.sum(mask) > 0:
                class_acc = np.sum(preds[mask] == i) / np.sum(mask)
                class_metrics[intent] = float(class_acc)

        # Confusion matrix
        cm = np.zeros((len(INTENTS), len(INTENTS)), dtype=np.int32)
        for t, p in zip(y, preds):
            cm[t, p] += 1

        return {
            "accuracy": float(accuracy),
            "total_samples": len(y),
            "correct": int(correct),
            "class_accuracy": class_metrics,
            "confusion_matrix": cm.tolist(),
        }

    def save(self, path: Optional[str] = None):
        """Save model weights to disk."""
        save_path = path or self.config.model_path
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        model_data = {
            "config": {
                "input_dim": self.config.input_dim,
                "hidden_1": self.config.hidden_1,
                "hidden_2": self.config.hidden_2,
                "output_dim": self.config.output_dim,
            },
            "weights": [],
            "biases": [],
        }

        for layer in self.layers:
            model_data["weights"].append(layer.weights.tolist())
            model_data["biases"].append(layer.bias.tolist())

        # Save as compressed numpy
        np_data = {}
        for i, (w, b) in enumerate(zip(model_data["weights"], model_data["biases"])):
            np_data[f"layer_{i}_weights"] = np.array(w, dtype=np.float32)
            np_data[f"layer_{i}_bias"] = np.array(b, dtype=np.float32)

        np.savez_compressed(save_path, **np_data)

        # Save config separately
        config_path = save_path.replace(".npz", "_config.json")
        with open(config_path, "w") as f:
            json.dump(model_data["config"], f)

        # Save vocab
        self._save_vocab()

        size_mb = os.path.getsize(save_path) / (1024 * 1024)
        logger.info(f"NeuralBrain: Model saved to {save_path} ({size_mb:.2f}MB)")

        return size_mb

    def load(self, path: Optional[str] = None):
        """Load model weights from disk."""
        load_path = path or self.config.model_path

        if not os.path.exists(load_path):
            logger.warning(f"NeuralBrain: Model not found at {load_path}")
            return False

        try:
            data = np.load(load_path)
            for i, layer in enumerate(self.layers):
                w_key = f"layer_{i}_weights"
                b_key = f"layer_{i}_bias"
                if w_key in data and b_key in data:
                    layer.weights = data[w_key].astype(np.float32)
                    layer.bias = data[b_key].astype(np.float32)

            self.trained = True
            logger.info(f"NeuralBrain: Model loaded from {load_path}")
            return True

        except Exception as e:
            logger.error(f"NeuralBrain: Failed to load model: {e}")
            return False

    def _save_vocab(self):
        """Save vocabulary/embedding state."""
        vocab_data = {
            "char_set": self.embedding.char_set,
            "char_to_idx": self.embedding.char_to_idx,
        }
        with open(self.config.vocab_path, "w", encoding="utf-8") as f:
            json.dump(vocab_data, f, ensure_ascii=False)

    def load_vocab(self, path: Optional[str] = None):
        """Load vocabulary."""
        load_path = path or self.config.vocab_path
        if os.path.exists(load_path):
            try:
                with open(load_path, "r", encoding="utf-8") as f:
                    vocab_data = json.load(f)
                self.embedding.char_set = vocab_data.get("char_set", self.embedding.char_set)
                self.embedding.char_to_idx = vocab_data.get("char_to_idx", self.embedding.char_to_idx)
                self.embedding.vocab_size = len(self.embedding.char_set)
                logger.info("NeuralBrain: Vocabulary loaded")
                return True
            except Exception as e:
                logger.error(f"NeuralBrain: Failed to load vocab: {e}")
        return False

    def quantize(self) -> Dict:
        """
        Quantize model to INT8 for smaller size.
        Returns quantization parameters.
        """
        scales = []
        zero_points = []
        quantized_weights = []

        for i, layer in enumerate(self.layers):
            w = layer.weights
            w_min = w.min()
            w_max = w.max()
            scale = (w_max - w_min) / 255.0 if w_max != w_min else 1.0
            zero_point = -round(w_min / scale) if scale > 0 else 0
            qw = np.clip(np.round(w / scale + zero_point), 0, 255).astype(np.uint8)

            quantized_weights.append(qw)
            scales.append(scale)
            zero_points.append(zero_point)

        # Save quantized model
        q_path = self.config.model_path.replace(".npz", "_int8.npz")
        q_data = {}
        for i, (qw, s, zp) in enumerate(zip(quantized_weights, scales, zero_points)):
            q_data[f"q{i}_w"] = qw
            q_data[f"q{i}_s"] = np.array([s], dtype=np.float32)
            q_data[f"q{i}_zp"] = np.array([zp], dtype=np.int32)
            q_data[f"q{i}_b"] = self.layers[i].bias.astype(np.float32)

        np.savez_compressed(q_path, **q_data)
        size_mb = os.path.getsize(q_path) / (1024 * 1024)

        logger.info(f"NeuralBrain: INT8 quantized model saved ({size_mb:.2f}MB)")
        return {
            "scales": scales,
            "zero_points": zero_points,
            "size_mb": size_mb,
        }

    def get_model_size_mb(self) -> float:
        """Get current model size estimate in MB."""
        total_params = 0
        for layer in self.layers:
            total_params += layer.weights.size + layer.bias.size
        return total_params * 4 / (1024 * 1024)  # float32 estimate

    def get_stats(self) -> dict:
        """Get neural brain statistics."""
        return {
            "architecture": f"{self.config.input_dim}→{self.config.hidden_1}→{self.config.hidden_2}→{self.config.output_dim}",
            "parameters": sum(l.weights.size + l.bias.size for l in self.layers),
            "trained": self.trained,
            "model_size_mb": round(self.get_model_size_mb(), 3),
            "embedding_dim": self.config.input_dim,
            "num_intents": self.config.output_dim,
            "loss_history_length": len(self.loss_history),
        }


class NeuralBrain:
    """
    Neural Brain - Intent Recognition Engine.

    Wraps the TinyNeuralNetwork with convenient APIs
    for the brain system.
    """

    def __init__(self):
        self.network = TinyNeuralNetwork()
        self._load_model()

    def _load_model(self) -> bool:
        """Try to load existing model."""
        model_path = NN_CONFIG["model_path"]
        if os.path.exists(model_path):
            self.network.load(model_path)
            self.network.load_vocab()
            return True
        logger.info("NeuralBrain: No existing model found, using untrained network")
        return False

    def recognize_intent(self, text: str) -> Tuple[str, float, np.ndarray]:
        """
        Recognize intent from text.

        Returns:
            (intent_name, confidence, probabilities)
        """
        start = time.time()
        intent, confidence, probs = self.network.predict(text)
        duration_ms = (time.time() - start) * 1000

        logger.debug(f"NeuralBrain: '{text}' → {intent} ({confidence:.2f}) in {duration_ms:.1f}ms")
        return intent, confidence, probs

    def train(self, texts: List[str], labels: List[int],
              val_texts: List[str] = None, val_labels: List[int] = None,
              epochs: int = None) -> Dict:
        """Train the neural network."""
        history = self.network.train(texts, labels, val_texts, val_labels, epochs)
        self.network.save()
        return history

    def evaluate(self, texts: List[str], labels: List[int]) -> Dict:
        """Evaluate the neural network."""
        return self.network.evaluate(texts, labels)

    def get_stats(self) -> dict:
        """Get neural brain stats."""
        return self.network.get_stats()
