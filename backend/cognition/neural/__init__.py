"""
AND9 — Neural Brain Bridge.

Connects the main cognitive pipeline to the micro_brain's TinyNeuralNetwork.
No external API calls — purely on-device, dataset-trained intent classification.

Usage:
    from backend.cognition.neural.bridge import NeuralBridge
    bridge = NeuralBridge()
    result = bridge.process("set a reminder for 5 seconds")
    # → {"intent": "REMINDER", "confidence": 0.95, "action": "set_reminder",
    #     "response": "Reminder set kar diya!", ...}
"""

from backend.cognition.neural.bridge import NeuralBridge
from backend.cognition.neural.rag import RAGEngine, RAGContext, get_rag_response

__all__ = ["NeuralBridge", "RAGEngine", "RAGContext", "get_rag_response"]
