"""
Phase 1 — Core Pydantic Models.

Shared models used across all JARVIS services.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


# ── Enums ───────────────────────────────────────────────────────


class BrainType(str, Enum):
    """Which brain module processed a request."""

    REFLEX = "reflex"
    SUBCONSCIOUS = "subconscious"
    CONSCIOUS = "conscious"
    NEURAL = "neural"
    MEMORY = "memory"
    DECISION = "decision"
    LEARNING = "learning"


class IntentType(str, Enum):
    """Supported intent categories."""

    # Device control
    OPEN_APP = "open_app"
    CLOSE_APP = "close_app"
    HOME = "home"
    BACK = "back"
    SCREENSHOT = "screenshot"
    LOCK_SCREEN = "lock_screen"
    SETTING = "setting"

    # Media
    PLAY_MUSIC = "play_music"
    PAUSE_MUSIC = "pause_music"
    YOUTUBE = "youtube"
    CAMERA = "camera"

    # Device functions
    FLASHLIGHT = "flashlight"
    VOLUME = "volume"
    WIFI = "wifi"
    BLUETOOTH = "bluetooth"
    AIRPLANE_MODE = "airplane_mode"

    # Communication
    CALL = "call"
    MESSAGE = "message"
    CONTACTS = "contacts"

    # Time / Reminders
    TIME = "time"
    DATE = "date"
    SET_ALARM = "set_alarm"
    SET_REMINDER = "set_reminder"
    SET_TIMER = "set_timer"

    # Information
    SEARCH = "search"
    WEATHER = "weather"
    CHAT = "chat"
    EMERGENCY = "emergency"
    ASSISTANT = "assistant"

    # Coding / Knowledge
    PYTHON_CODING = "python_coding"
    WEB_CODING = "web_coding"
    GENERAL_KNOWLEDGE = "general_knowledge"
    MEDICINE_KNOWLEDGE = "medicine_knowledge"
    MOVIE_KNOWLEDGE = "movie_knowledge"

    # System
    UNKNOWN = "unknown"


class ProcessingStage(str, Enum):
    """Pipeline processing stages."""

    RECEIVED = "received"
    NORMALIZED = "normalized"
    TOKENIZED = "tokenized"
    EMBEDDED = "embedded"
    INTENT_DETECTED = "intent_detected"
    ENTITIES_EXTRACTED = "entities_extracted"
    CONTEXT_BUILT = "context_built"
    PLANNED = "planned"
    EXECUTED = "executed"
    COMPLETED = "completed"
    FAILED = "failed"


# ── Core Models ─────────────────────────────────────────────────


class ServiceStatus(BaseModel):
    """Health status of a service."""

    status: str = Field(..., description="healthy, degraded, or unhealthy")
    service_name: str = Field(..., description="Name of the service")
    version: str = Field(default="1.0.0", description="Service version")
    initialized: bool = Field(default=False, description="Whether service is initialized")
    uptime_seconds: float = Field(default=0.0, description="Seconds since initialization")
    error: Optional[str] = Field(default=None, description="Error message if unhealthy")


class PipelineStageResult(BaseModel):
    """Result from a single pipeline stage."""

    stage: ProcessingStage = Field(..., description="Stage name")
    success: bool = Field(default=True, description="Whether stage succeeded")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score")
    time_ms: float = Field(default=0.0, description="Execution time in ms")
    error: Optional[str] = Field(default=None, description="Error message if stage failed")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Stage-specific output data")


class ProcessingResult(BaseModel):
    """Full result from processing a query through the pipeline."""

    query: str = Field(..., description="Original user query")
    normalized_query: Optional[str] = Field(default=None, description="Normalized query text")
    intent: IntentType = Field(default=IntentType.UNKNOWN, description="Detected intent")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Overall confidence")
    entities: Dict[str, Any] = Field(default_factory=dict, description="Extracted entities")
    brain: BrainType = Field(default=BrainType.REFLEX, description="Brain that processed this")

    # Pipeline trace
    stages: List[PipelineStageResult] = Field(default_factory=list, description="Pipeline stage results")
    total_time_ms: float = Field(default=0.0, description="Total processing time in ms")

    # Output
    action: Optional[str] = Field(default=None, description="Executed action name")
    payload: Optional[Dict[str, Any]] = Field(default=None, description="Action payload")
    response: str = Field(default="", description="Response text")
    success: bool = Field(default=True, description="Whether processing succeeded")

    # Metadata
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="Processing timestamp")
    session_id: Optional[str] = Field(default=None, description="Conversation session ID")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class BrainResult(BaseModel):
    """Standard brain output (compatible with existing AND9 BrainResult)."""

    response: str = Field(default="", description="Response text")
    action: Optional[str] = Field(default=None, description="Action to execute")
    payload: Optional[Dict[str, Any]] = Field(default=None, description="Action payload")
    brain: BrainType = Field(default=BrainType.REFLEX, description="Brain that processed this")
    intent: Optional[IntentType] = Field(default=None, description="Detected intent")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Extracted parameters")
    execution_time_ms: float = Field(default=0.0, description="Execution time in ms")
    success: bool = Field(default=True, description="Whether execution succeeded")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict, converting enums to strings."""
        return {
            "response": self.response,
            "action": self.action,
            "payload": self.payload,
            "brain": self.brain.value if self.brain else None,
            "intent": self.intent.value if self.intent else None,
            "parameters": self.parameters,
            "execution_time_ms": self.execution_time_ms,
            "success": self.success,
            "metadata": self.metadata,
        }
