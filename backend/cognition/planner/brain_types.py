"""
AND9 — Brain Types, Enums, and Data Classes.

Defines the core data structures that flow through the AND9
multi-brain architecture. Every brain (Reflex, Subconscious,
Conscious) produces and consumes BrainResult instances.

Key types:
  - BrainType:  Identifies which cognitive layer handled a request
  - IntentType: 20-level priority enum for classifying user intent
  - BrainResult: Universal result object returned by all brains
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class BrainType(Enum):
    """Identifies which cognitive brain processed a request.

    Each brain has different speed and capability characteristics:

    REFLEX (target <100ms):
        Instant execution with zero LLM involvement. Handles app
        launches, device controls, calls, alarms, timers, and any
        command that has a deterministic, known action.

    SUBCONSCIOUS (target ~200ms):
        Pattern learning and habit detection. Tracks user actions
        over time and suggests automated routines based on
        time-of-day and sequential patterns.

    CONSCIOUS (target ~1-5s):
        Full LLM reasoning and planning. Handles open-ended chat,
        web search, goal management, code generation, and any
        task that requires understanding context and generating
        novel responses.
    """
    REFLEX = "reflex"
    SUBCONSCIOUS = "subconscious"
    CONSCIOUS = "conscious"


class IntentType(Enum):
    """All supported intents, ordered by descending priority.

    Priority is 1 (highest — emergency) through 21 (lowest — chat).
    The priority router checks intents in this exact order so that
    critical actions like emergency and calls always take precedence
    over entertainment or informational queries.

    Priority order:
      Emergency → Call → Message → Open App → Camera → Flashlight →
      Bluetooth → WiFi → Airplane Mode → Volume → YouTube → Music →
      Alarm → Reminder → Timer → Time → Goal → Home → Automation →
      Search → Chat
    """
    EMERGENCY = "emergency"         # Priority 1 —  SOS, danger, accident
    CALL = "call"                   # Priority 2 —  Phone calls, dial
    MESSAGE = "message"             # Priority 3 —  SMS, text, WhatsApp message
    OPEN_APP = "open_app"           # Priority 4 —  Launch any Android app
    CAMERA = "camera"               # Priority 5 —  Open camera, take photo
    FLASHLIGHT = "flashlight"       # Priority 6 —  Toggle flashlight/torch
    BLUETOOTH = "bluetooth"         # Priority 7 —  Bluetooth on/off
    WIFI = "wifi"                   # Priority 8 —  WiFi on/off
    AIRPLANE_MODE = "airplane_mode" # Priority 9 —  Airplane/flight mode
    VOLUME = "volume"               # Priority 10 — Volume up/down/mute
    YOUTUBE = "youtube"             # Priority 11 — YouTube search/play
    MUSIC = "music"                 # Priority 12 — Play music/songs
    CLOSE_APP = "close_app"         # Priority 4b — Close an app
    PLAY_MUSIC = "play_music"       # Priority 12a — Play specific music
    PAUSE_MUSIC = "pause_music"     # Priority 12b — Pause music
    SET_ALARM = "set_alarm"         # Priority 13 — Set an alarm
    SET_REMINDER = "set_reminder"   # Priority 14 — Set a reminder
    SET_TIMER = "set_timer"         # Priority 15 — Set a countdown timer
    TIME = "time"                   # Priority 16 — Generic time query
    DATE = "date"                   # Priority 16b — Date query
    VOLUME_UP = "volume_up"         # Priority 10a — Volume up
    VOLUME_DOWN = "volume_down"     # Priority 10b — Volume down
    GO_HOME = "go_home"             # Priority 18 — Go to home screen
    GO_BACK = "go_back"             # Priority 18b — Go back
    OPEN_SETTINGS = "open_settings" # Priority 18c — Open settings
    GOAL = "goal"                   # Priority 17 — Goal/project management
    HOME = "home"                   # Priority 18 — Go to home screen
    AUTOMATION = "automation"       # Priority 19 — Automation/routines
    SEARCH = "search"               # Priority 20 — Web search, lookup
    CHAT = "chat"                   # Priority 21 — General conversation, LLM

    @property
    def priority(self) -> int:
        """Return the numeric priority level (1 = highest)."""
        priorities = {
            IntentType.EMERGENCY: 1,
            IntentType.CALL: 2,
            IntentType.MESSAGE: 3,
            IntentType.OPEN_APP: 4,
            IntentType.CLOSE_APP: 4,
            IntentType.CAMERA: 5,
            IntentType.FLASHLIGHT: 6,
            IntentType.BLUETOOTH: 7,
            IntentType.WIFI: 8,
            IntentType.AIRPLANE_MODE: 9,
            IntentType.VOLUME: 10,
            IntentType.VOLUME_UP: 10,
            IntentType.VOLUME_DOWN: 10,
            IntentType.YOUTUBE: 11,
            IntentType.MUSIC: 12,
            IntentType.PLAY_MUSIC: 12,
            IntentType.PAUSE_MUSIC: 12,
            IntentType.SET_ALARM: 13,
            IntentType.SET_REMINDER: 14,
            IntentType.SET_TIMER: 15,
            IntentType.TIME: 16,
            IntentType.DATE: 16,
            IntentType.GOAL: 17,
            IntentType.HOME: 18,
            IntentType.GO_HOME: 18,
            IntentType.GO_BACK: 18,
            IntentType.OPEN_SETTINGS: 18,
            IntentType.AUTOMATION: 19,
            IntentType.SEARCH: 20,
            IntentType.CHAT: 21,
        }
        return priorities[self]


@dataclass
class BrainResult:
    """Universal result object produced by every AND9 brain.

    This is the single output format across all three brains.
    It carries the natural language response, the Android intent
    action/payload for device execution, timing information, and
    metadata for frontend rendering.

    Attributes:
        response:  Human-readable reply in Hinglish/English.
        action:    Action type constant (e.g., "LAUNCH_APP", "CALL",
                   "SET_ALARM"). None when no device action is needed.
        payload:   Android Intent dict or action data for the device
                   to execute. Structure varies by action type.
        brain:     Which BrainType handled this request.
        intent:    Detected IntentType.
        parameters: Structured parameters extracted from the query
                    (e.g., {"hour": 7, "minute": 0, "label": "Meeting"}).
        execution_time_ms: Wall-clock time in milliseconds.
        success:   Whether execution completed successfully.
        metadata:  Extra data for frontend (YouTube URL, image URL,
                   sources, contact info, etc.).
    """
    response: str = ""
    action: Optional[str] = None
    payload: Any = None
    brain: BrainType = BrainType.CONSCIOUS
    intent: Optional[IntentType] = None
    parameters: dict = field(default_factory=dict)
    execution_time_ms: float = 0.0
    success: bool = True
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize to a JSON-safe dict for the API response."""
        return {
            "response": self.response,
            "action": self.action,
            "payload": self.payload,
            "brain": self.brain.value,
            "intent": self.intent.value if self.intent else None,
            "parameters": self.parameters,
            "time_ms": self.execution_time_ms,
            "success": self.success,
            "metadata": self.metadata,
        }
