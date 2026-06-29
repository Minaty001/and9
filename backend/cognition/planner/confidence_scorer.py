"""
AND9 — Confidence Scorer.
Evaluates classification quality based on matching type, parameters, and trigger words.
"""
import re
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Trigger words per intent type for semantic scoring
INTENT_TRIGGERS = {
    "call": ["call", "phone", "dial", "milao", "lagao", "baat", "call-out"],
    "message": ["message", "sms", "text", "send", "bhejo", "likho"],
    "open_app": ["open", "kholo", "launch", "chalao", "start", "run"],
    "flashlight": ["flashlight", "torch", "light", "flash", "jalao", "strobe", "blink"],
    "volume": ["volume", "sound", "aawaz", "mute", "unmute", "up", "down", "loud"],
    "wifi": ["wifi", "wi-fi", "internet", "net"],
    "bluetooth": ["bluetooth", "bt"],
    "alarm": ["alarm", "wake", "uthana", "jagana", "alarm-clock"],
    "timer": ["timer", "stopwatch", "seconds", "minutes", "hours"],
    "reminder": ["remind", "reminder", "yaad"],
    "camera": ["camera", "photo", "pic", "khencho", "snap"],
    "youtube": ["youtube", "yt", "video", "play"],
    "home": ["home", "back", "recents", "screen"],
    "time": ["time", "samay", "baje", "clock", "ghadi", "date", "tarikh", "calendar"],
    "city_time": ["time", "samay", "baje", "clock", "ghadi", "date", "tarikh", "calendar"],
    "list_contacts": ["contacts", "phonebook", "sabhi"],
    "add_contact": ["add", "save", "new", "naya"],
    "delete_contact": ["delete", "remove", "hatao"],
    "search_contacts": ["search", "find", "dhundo", "khojo"],
    "assistant_info": ["who", "what", "name", "kaun", "tum", "version", "about", "creator", "made"],
    "help": ["help", "guide", "commands", "capabilities", "kya kar", "features", "skills"],
    "system_status": ["battery", "network", "status", "device", "system", "info", "uptime"],
    "screenshot": ["screenshot", "capture", "screen shot"],
    "lock_screen": ["lock", "taala", "band"],
    "calculator": ["calculate", "plus", "minus", "multiply", "divide", "what is", "kitna hoga"],
    "joke": ["joke", "funny", "hasao", "hansao", "laugh"],
    "quote": ["motivate", "inspire", "quote", "prerit", "protsahan"],
}

def score_intent(intent: str, query: str, params: Dict[str, Any], action: str = "") -> float:
    """Calculate the confidence score for a given intent and query.

    Args:
        intent: The matched intent name (e.g., 'call', 'open_app', 'chat')
        query: Normalized query string.
        params: Extracted parameters dictionary.

    Returns:
        Confidence score float between 0.0 and 1.0.
    """
    q = query.lower().strip()
    
    # Chat and search are safe defaults
    if intent in ("chat", "search"):
        return 1.0

    # Emergency is always immediate execution if classified
    if intent == "emergency":
        return 1.0

    # Get standard trigger words for the intent
    triggers = INTENT_TRIGGERS.get(intent, [])
    has_trigger_word = any(t in q for t in triggers)

    # ── Intent-Specific Confidence Rules ─────────────────────────────────────
    
    if intent == "call":
        has_number = bool(params.get("phone_number"))
        has_contact = bool(params.get("contact_name"))
        
        if (has_number or has_contact) and has_trigger_word:
            return 0.98
        elif (has_number or has_contact):
            # Implicit call (e.g., just saying a name or number)
            return 0.85
        else:
            # Call intent matched but no number/contact extracted
            return 0.50

    elif intent == "message":
        has_contact = bool(params.get("contact_name")) or bool(params.get("phone_number"))
        has_body = bool(params.get("message_body"))
        
        if has_contact and has_body and has_trigger_word:
            return 0.98
        elif has_contact or has_body:
            return 0.80
        else:
            return 0.50

    elif intent == "open_app":
        has_app = bool(params.get("app_name")) or bool(params.get("package_name"))
        
        if has_app and has_trigger_word:
            return 0.98
        elif has_app:
            # Just saying the app name "WhatsApp"
            return 0.88
        else:
            return 0.45

    elif intent == "flashlight":
        # Check if state/mode is defined
        has_state = params.get("state") is not None or "strobe" in q or "blink" in q
        if has_state and has_trigger_word:
            return 0.98
        elif has_trigger_word:
            return 0.90
        else:
            return 0.60

    elif intent == "volume":
        # Volume intent usually contains direct actions
        if any(w in q for w in ["up", "down", "mute", "unmute", "max", "silent"]):
            return 0.98
        return 0.85

    elif intent in ("wifi", "bluetooth"):
        if any(w in q for w in ["on", "off", "enable", "disable", "toggle"]):
            return 0.98
        return 0.85

    elif intent == "alarm":
        has_time = params.get("hour") is not None or params.get("time") is not None
        if has_time and has_trigger_word:
            return 0.98
        elif has_time:
            return 0.88
        else:
            return 0.55

    elif intent == "timer":
        # entity_extractor returns duration_seconds; also check legacy keys for compat
        has_duration = (params.get("duration_seconds") is not None
                        or params.get("length") is not None
                        or params.get("duration") is not None)
        if has_duration and has_trigger_word:
            return 0.98
        elif has_duration:
            return 0.88
        else:
            return 0.55

    elif intent == "reminder":
        # Reminder management actions get high confidence if they are matched by the router
        if action in ("list_reminders", "show_completed_reminders", "clear_all_reminders",
                      "delete_reminder", "pause_reminder", "resume_reminder", "snooze_reminder"):
            return 0.98

        has_title = bool(params.get("title")) or bool(params.get("label"))
        if has_title and has_trigger_word:
            return 0.98
        elif has_title:
            return 0.85
        else:
            return 0.50

    elif intent == "youtube":
        has_query = bool(params.get("query")) or bool(params.get("video_title"))
        if has_query and has_trigger_word:
            return 0.98
        elif has_trigger_word:
            return 0.90
        else:
            return 0.60

    elif intent == "time":
        if has_trigger_word:
            return 0.98
        return 0.90

    elif intent == "city_time":
        has_city = bool(params.get("city"))
        if has_city and has_trigger_word:
            return 0.98
        elif has_city:
            return 0.88
        else:
            return 0.55

    # ── Contacts Management ────────────────────────────────────────
    elif intent in ("list_contacts", "add_contact", "delete_contact", "search_contacts"):
        # These are pattern-matched specifically in the router – high confidence
        if has_trigger_word:
            return 0.98
        return 0.90

    # ── Assistant Features ─────────────────────────────────────────
    elif intent in ("assistant_info", "help", "system_status", "screenshot", "lock_screen"):
        # Pattern-matched in router – high confidence
        if has_trigger_word:
            return 0.98
        return 0.90

    elif intent == "calculator":
        # Pattern-matched with math expression
        has_expr = bool(params.get("expression"))
        if has_expr and has_trigger_word:
            return 0.98
        elif has_expr:
            return 0.92
        return 0.85

    elif intent in ("joke", "quote"):
        # Pattern-matched – high confidence
        if has_trigger_word:
            return 0.98
        return 0.90

    # Default fallback calculation: ratio of matched words
    query_words = set(q.split())
    trigger_words = set(triggers)
    matching = query_words.intersection(trigger_words)
    
    if matching:
        return min(0.70 + (len(matching) * 0.1), 0.95)
    
    return 0.50
