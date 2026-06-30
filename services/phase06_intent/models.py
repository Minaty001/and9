"""
Phase 6 — Intent Detection Models.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class IntentType(str, Enum):
    """Supported intent types matching the 28-class output."""

    OPEN_APP = "OPEN_APP"
    CLOSE_APP = "CLOSE_APP"
    PLAY_MUSIC = "PLAY_MUSIC"
    PAUSE_MUSIC = "PAUSE_MUSIC"
    SEARCH_WEB = "SEARCH_WEB"
    WEATHER = "WEATHER"
    TIME = "TIME"
    DATE = "DATE"
    REMINDER = "REMINDER"
    CALL = "CALL"
    MESSAGE = "MESSAGE"
    CAMERA = "CAMERA"
    FLASHLIGHT_ON = "FLASHLIGHT_ON"
    FLASHLIGHT_OFF = "FLASHLIGHT_OFF"
    VOLUME_UP = "VOLUME_UP"
    VOLUME_DOWN = "VOLUME_DOWN"
    HOME = "HOME"
    BACK = "BACK"
    SETTING = "SETTING"
    PYTHON_CODING = "PYTHON_CODING"
    AI_NEWS_MODELS = "AI_NEWS_MODELS"
    CAPABILITIES = "CAPABILITIES"
    WEB_CODING = "WEB_CODING"
    GENERAL_KNOWLEDGE = "GENERAL_KNOWLEDGE"
    MEDICINE_KNOWLEDGE = "MEDICINE_KNOWLEDGE"
    MOVIE_KNOWLEDGE = "MOVIE_KNOWLEDGE"
    CHAT = "CHAT"
    UNKNOWN = "UNKNOWN"

    @classmethod
    def list_names(cls) -> List[str]:
        """Return all intent names as a list."""
        return [item.value for item in cls]


class IntentResult(BaseModel):
    """Result from intent detection."""

    intent: str = Field(..., description="Detected intent name")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence")
    all_probabilities: Dict[str, float] = Field(
        default_factory=dict,
        description="Probabilities for all intent classes",
    )
    is_multi_intent: bool = Field(default=False, description="Whether multiple intents detected")
    secondary_intents: List[dict] = Field(
        default_factory=list,
        description="Secondary intents with confidence",
    )
    time_ms: float = Field(default=0.0, description="Detection time in milliseconds")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
