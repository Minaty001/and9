"""
Phase 6 — Intent Detection Configuration.
"""

from pydantic import Field
from services.base.config_base import BaseConfig


class IntentConfig(BaseConfig):
    """Configuration for the intent detection engine."""

    service_name: str = Field(default="jarvis_intent", description="Intent service name")
    input_dim: int = Field(default=128, description="Input embedding dimension")
    hidden_1: int = Field(default=64, description="First hidden layer size")
    hidden_2: int = Field(default=32, description="Second hidden layer size")
    output_dim: int = Field(default=28, description="Number of intent classes")
    learning_rate: float = Field(default=0.01, description="NN learning rate")
    min_confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Minimum confidence threshold")
    high_confidence: float = Field(default=0.85, ge=0.0, le=1.0, description="High confidence threshold")
    fallback_intent: str = Field(default="UNKNOWN", description="Fallback intent when confidence is low")
    model_path: str = Field(default="", description="Path to pretrained model weights")

    class Config:
        env_prefix = "JARVIS_INTENT_"
