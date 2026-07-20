"""
AND9 — Intent Definitions with Slot Specifications.

Every intent that requires multi-turn conversation defines its required
and optional slots here. Each slot has a human-readable question that
the assistant asks when the value is missing.

Slot-first architecture:
  - Required slots: MUST be filled before execution
  - Optional slots: NICE-TO-HAVE, may be filled if user provides them
  - Auto-fill: Slots that can be derived from context (e.g., from memory)
  - Validation: Per-slot validation functions (optional)

Design rules:
  - One question per turn (ask for exactly one missing slot)
  - Never ask for the same slot twice
  - Natural, short, context-aware questions
  - Questions should feel like a human assistant, not a form
"""

from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class SlotDefinition:
    """Definition of a single slot within an intent.

    Attributes:
        name: Machine-readable slot name (e.g., "search_query").
        required: Whether this slot must be filled before execution.
        question: Natural language question to ask when this slot is missing.
        validation_fn: Optional callable(value) -> (is_valid, error_msg).
        auto_fill_fn: Optional callable(context) -> value or None.
        examples: Example values for documentation/testing.
        description: Human-readable description of what this slot holds.
    """
    name: str
    required: bool = True
    question: str = ""
    validation_fn: Optional[Callable[[str], tuple[bool, str]]] = None
    auto_fill_fn: Optional[Callable[[dict], Optional[str]]] = None
    examples: list[str] = field(default_factory=list)
    description: str = ""


@dataclass
class IntentDefinition:
    """Complete definition of an intent with its slot requirements.

    Attributes:
        name: Intent name matching AND9 intent_router output.
        display_name: User-facing name.
        description: What this intent does.
        required_slots: Ordered list of required SlotDefinitions.
        optional_slots: Ordered list of optional SlotDefinitions.
        success_message: Message template when all slots filled and action executed.
                         Use {slot_name} placeholders for dynamic values.
        failure_message: Message template on execution failure.
        completion_actions: List of action types this intent maps to.
    """
    name: str
    display_name: str = ""
    description: str = ""
    required_slots: list[SlotDefinition] = field(default_factory=list)
    optional_slots: list[SlotDefinition] = field(default_factory=list)
    success_message: str = "Done! ✅"
    failure_message: str = "Kuch gadbad ho gayi. Phir se try karo! 😅"
    completion_actions: list[str] = field(default_factory=list)


# ── Validation Helpers ─────────────────────────────────────────────

def _validate_phone_number(value: str) -> tuple[bool, str]:
    """Validate a phone number (7-15 digits, optional + prefix)."""
    import re
    cleaned = re.sub(r'[\s\-\(\)]', '', value)
    if re.match(r'^\+?\d{7,15}$', cleaned):
        return True, ""
    return False, "Yeh phone number sahi nahi lag raha. 7-15 digits ka number dijiye."


def _validate_time(value: str) -> tuple[bool, str]:
    """Validate a time expression."""
    import re
    if re.match(r'^\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM)?$', value.strip()):
        return True, ""
    if re.match(r'^\d{1,2}\s*baje?$', value.strip()):
        return True, ""
    return False, "Time sahi format mein dijiye (e.g., 7 AM, 14:30)."


def _validate_duration(value: str) -> tuple[bool, str]:
    """Validate a duration expression."""
    import re
    if re.match(r'^\d+\s*(?:second|sec|minute|min|hour|hr|ghanta|ghante)s?$', value.strip(), re.IGNORECASE):
        return True, ""
    if re.match(r'^\d+\s*$', value.strip()):
        return True, ""
    return False, "Duration sahi format mein dijiye (e.g., 5 minutes, 1 hour)."


def _validate_not_empty(value: str) -> tuple[bool, str]:
    """Validate that a value is non-empty."""
    if value and value.strip():
        return True, ""
    return False, "Kuch to batao! Main kya karun?"


# ── Intent Definitions ─────────────────────────────────────────────

INTENT_DEFINITIONS: dict[str, IntentDefinition] = {
    # ── YouTube ─────────────────────────────────────────────────
    "youtube": IntentDefinition(
        name="youtube",
        display_name="YouTube",
        description="Search and play content on YouTube",
        required_slots=[
            SlotDefinition(
                name="content_type",
                required=True,
                question="Kya chahiye? Song, video, playlist ya kuch aur?",
                description="Type of content (song, video, playlist)",
                examples=["song", "video", "playlist", "gaana", "music"],
            ),
            SlotDefinition(
                name="search_query",
                required=True,
                question="Kaunsa song/video chahiye? Naam batao!",
                description="Search query for the content",
                examples=["Tum Hi Ho", "Shape of You", "cooking video"],
            ),
        ],
        optional_slots=[
            SlotDefinition(
                name="artist",
                required=False,
                question="Kis artist ka gaana chahiye?",
                description="Artist or singer name",
                examples=["Arijit Singh", "Ed Sheeran"],
            ),
            SlotDefinition(
                name="language",
                required=False,
                question="Kaunsi bhasha mein gaana chahiye?",
                description="Preferred language",
                examples=["Hindi", "English", "Punjabi"],
            ),
        ],
        success_message="Baja raha hoon '{search_query}' YouTube pe! 🎵",
        failure_message="YouTube pe '{search_query}' dhundhne mein problem aa gayi. 😅",
        completion_actions=["youtube_search", "youtube_play"],
    ),

    # ── Open App ────────────────────────────────────────────────
    "open_app": IntentDefinition(
        name="open_app",
        display_name="Open App",
        description="Open an Android application",
        required_slots=[
            SlotDefinition(
                name="app_name",
                required=True,
                question="Kaunsa app kholna chahte ho?",
                description="Name of the app to open",
                examples=["WhatsApp", "YouTube", "Chrome", "Instagram"],
                validation_fn=_validate_not_empty,
            ),
        ],
        optional_slots=[],
        success_message="{app_name} khol raha hoon... 📱",
        failure_message="'{app_name}' app nahi mila. Kripya sahi naam batao!",
        completion_actions=["open_app"],
    ),

    # ── Call ────────────────────────────────────────────────────
    "call": IntentDefinition(
        name="call",
        display_name="Phone Call",
        description="Make a phone call to a contact or number",
        required_slots=[
            SlotDefinition(
                name="contact_name",
                required=True,
                question="Kise call karna chahte ho?",
                description="Contact name or phone number",
                examples=["Mummy", "Papa", "9876543210"],
                validation_fn=_validate_not_empty,
            ),
        ],
        optional_slots=[
            SlotDefinition(
                name="number",
                required=False,
                question="Phone number kya hai?",
                description="Phone number (if contact name not found)",
            ),
        ],
        success_message="Call kar raha hoon {contact_name} ko... 📞",
        failure_message="Call nahi ho saka. Number sahi hai?",
        completion_actions=["call"],
    ),

    # ── Message ─────────────────────────────────────────────────
    "message": IntentDefinition(
        name="message",
        display_name="Send Message",
        description="Send an SMS or text message",
        required_slots=[
            SlotDefinition(
                name="contact_name",
                required=True,
                question="Kise message bhejna chahte ho?",
                description="Contact name or number",
                examples=["Mummy", "Bhai", "9876543210"],
            ),
            SlotDefinition(
                name="message_text",
                required=True,
                question="Kya likhna hai message mein?",
                description="Message content",
                examples=["Mein ghar aa raha hoon", "Kal milte hain"],
            ),
        ],
        optional_slots=[],
        success_message="Message bhej raha hoon {contact_name} ko... 💬",
        failure_message="Message nahi bhej paaya. Kripya phir se try karo!",
        completion_actions=["send_sms"],
    ),

    # ── Alarm ───────────────────────────────────────────────────
    "alarm": IntentDefinition(
        name="alarm",
        display_name="Set Alarm",
        description="Set an alarm for a specific time",
        required_slots=[
            SlotDefinition(
                name="hour",
                required=True,
                question="Kitne baje alarm set karun?",
                description="Hour for the alarm",
                examples=["7", "6", "12"],
                validation_fn=_validate_time,
            ),
            SlotDefinition(
                name="minute",
                required=True,
                question="Kitne minute par?",
                description="Minute for the alarm",
                examples=["0", "30", "15"],
            ),
        ],
        optional_slots=[
            SlotDefinition(
                name="label",
                required=False,
                question="Alarm ka kya naam rakhein?",
                description="Label for the alarm",
                examples=["Morning Alarm", "Meeting Reminder"],
            ),
        ],
        success_message="Alarm {hour}:{minute:02d} ke liye set kar diya! ⏰",
        failure_message="Alarm set nahi ho saka. Time sahi hai?",
        completion_actions=["set_alarm"],
    ),

    # ── Timer ───────────────────────────────────────────────────
    "timer": IntentDefinition(
        name="timer",
        display_name="Set Timer",
        description="Set a countdown timer",
        required_slots=[
            SlotDefinition(
                name="duration_seconds",
                required=True,
                question="Kitne der ka timer chahiye?",
                description="Duration for the timer",
                examples=["5 minutes", "10 seconds", "1 hour"],
                validation_fn=_validate_duration,
            ),
        ],
        optional_slots=[
            SlotDefinition(
                name="label",
                required=False,
                question="Timer ka naam kya hai?",
                description="Label for the timer",
                examples=["Pasta", "Exercise", "Break"],
            ),
        ],
        success_message="Timer set kar diya! {display_duration} ka ⏲️",
        failure_message="Timer set nahi ho saka.",
        completion_actions=["set_timer"],
    ),

    # ── Set Reminder ────────────────────────────────────────────
    "reminder": IntentDefinition(
        name="reminder",
        display_name="Set Reminder",
        description="Set a reminder for a task or event",
        required_slots=[
            SlotDefinition(
                name="label",
                required=True,
                question="Kya yaad dilana hai?",
                description="What to remind about",
                examples=["Meeting at 3 PM", "Buy groceries", "Call doctor"],
            ),
            SlotDefinition(
                name="trigger_at",
                required=True,
                question="Kab yaad dilana hai? Time batao!",
                description="When to trigger the reminder",
                examples=["after 10 minutes", "tomorrow 9 AM", "Monday 8 AM"],
            ),
        ],
        optional_slots=[],
        success_message="Reminder set kar diya! '{label}' ke liye ⏰",
        failure_message="Reminder set nahi ho saka. Time sahi format mein batao!",
        completion_actions=["set_reminder"],
    ),

    # ── Play Music ──────────────────────────────────────────────
    "music": IntentDefinition(
        name="music",
        display_name="Play Music",
        description="Play a song or music",
        required_slots=[
            SlotDefinition(
                name="song_name",
                required=True,
                question="Kaunsa gaana bajau?",
                description="Name of the song to play",
                examples=["Tum Hi Ho", "Kesariya", "Shape of You"],
                validation_fn=_validate_not_empty,
            ),
        ],
        optional_slots=[
            SlotDefinition(
                name="artist",
                required=False,
                question="Kis artist ka gaana chahiye?",
                description="Artist name",
                examples=["Arijit Singh", "Neha Kakkar"],
            ),
        ],
        success_message="Baja raha hoon '{song_name}'! 🎶",
        failure_message="'{song_name}' nahi mila. Kuch aur batao?",
        completion_actions=["youtube_play"],
    ),

    # ── Web Search ──────────────────────────────────────────────
    "search": IntentDefinition(
        name="search",
        display_name="Web Search",
        description="Search the web for information",
        required_slots=[
            SlotDefinition(
                name="query",
                required=True,
                question="Kya search karun?",
                description="Search query",
                examples=["weather today", "Python tutorial", "news"],
                validation_fn=_validate_not_empty,
            ),
        ],
        optional_slots=[],
        success_message="Web pe '{query}' search kar raha hoon 🔍",
        failure_message="Search nahi ho saka. Internet check karo!",
        completion_actions=["search"],
    ),

    # ── Device Control ──────────────────────────────────────────
    "flashlight": IntentDefinition(
        name="flashlight",
        display_name="Flashlight",
        description="Turn flashlight on or off",
        required_slots=[
            SlotDefinition(
                name="state",
                required=True,
                question="Flashlight on karna hai ya off?",
                description="On/off state",
                examples=["on", "off"],
            ),
        ],
        optional_slots=[],
        success_message="Flashlight {state} kar diya! 💡",
        failure_message="Flashlight control nahi ho saka.",
        completion_actions=["flashlight"],
    ),

    "volume": IntentDefinition(
        name="volume",
        display_name="Volume Control",
        description="Adjust device volume",
        required_slots=[
            SlotDefinition(
                name="action",
                required=True,
                question="Volume kya karna hai? Up, down ya mute?",
                description="Volume action",
                examples=["up", "down", "mute", "max"],
            ),
        ],
        optional_slots=[],
        success_message="Volume {action} kar diya! 🔊",
        failure_message="Volume control nahi ho saka.",
        completion_actions=["volume_up", "volume_down", "volume_mute", "volume_max"],
    ),

    "wifi": IntentDefinition(
        name="wifi",
        display_name="WiFi",
        description="Toggle WiFi on or off",
        required_slots=[
            SlotDefinition(
                name="state",
                required=True,
                question="WiFi on karna hai ya off?",
                description="On/off state",
                examples=["on", "off"],
            ),
        ],
        optional_slots=[],
        success_message="WiFi {state} kar diya! 🌐",
        failure_message="WiFi control nahi ho saka.",
        completion_actions=["wifi"],
    ),

    "bluetooth": IntentDefinition(
        name="bluetooth",
        display_name="Bluetooth",
        description="Toggle Bluetooth on or off",
        required_slots=[
            SlotDefinition(
                name="state",
                required=True,
                question="Bluetooth on karna hai ya off?",
                description="On/off state",
                examples=["on", "off"],
            ),
        ],
        optional_slots=[],
        success_message="Bluetooth {state} kar diya! 🔵",
        failure_message="Bluetooth control nahi ho saka.",
        completion_actions=["bluetooth"],
    ),

    "bluetooth_scan": IntentDefinition(
        name="bluetooth_scan",
        display_name="Bluetooth Scan",
        description="Scan for nearby Bluetooth devices",
        required_slots=[],
        optional_slots=[],
        success_message="Bluetooth devices scan kar raha hoon... 🔍🔵",
        failure_message="Bluetooth scan nahi ho saka.",
        completion_actions=["bluetooth_scan"],
    ),

    "bluetooth_paired": IntentDefinition(
        name="bluetooth_paired",
        display_name="Bluetooth Paired",
        description="List paired Bluetooth devices",
        required_slots=[],
        optional_slots=[],
        success_message="Paired Bluetooth devices dikha raha hoon... 📋🔵",
        failure_message="Paired devices list nahi dikha saka.",
        completion_actions=["bluetooth_paired"],
    ),

    # ── Chat (no required slots — goes to LLM) ──────────────────
    "chat": IntentDefinition(
        name="chat",
        display_name="Chat",
        description="General conversation with the AI",
        required_slots=[
            SlotDefinition(
                name="query",
                required=True,
                question="Kya kehna chahte ho?",
                description="The chat message",
            ),
        ],
        optional_slots=[],
        success_message="",
        failure_message="Mujhe samajhne mein problem aa rahi hai. 😅",
        completion_actions=["chat"],
    ),
}


# ── Helpers ────────────────────────────────────────────────────────

def get_intent_definition(intent_name: str) -> Optional[IntentDefinition]:
    """Get the intent definition for a given intent name.

    Args:
        intent_name: The intent name (e.g., "youtube", "call", "open_app").

    Returns:
        IntentDefinition if found, None otherwise.
    """
    return INTENT_DEFINITIONS.get(intent_name)


def get_required_slot_names(intent_name: str) -> list[str]:
    """Get list of required slot names for an intent."""
    intent_def = get_intent_definition(intent_name)
    if not intent_def:
        return []
    return [s.name for s in intent_def.required_slots]


def get_optional_slot_names(intent_name: str) -> list[str]:
    """Get list of optional slot names for an intent."""
    intent_def = get_intent_definition(intent_name)
    if not intent_def:
        return []
    return [s.name for s in intent_def.optional_slots]


def get_all_slot_names(intent_name: str) -> list[str]:
    """Get all slot names (required + optional) for an intent."""
    return get_required_slot_names(intent_name) + get_optional_slot_names(intent_name)
