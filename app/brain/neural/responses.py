"""
AND9 — Predefined Response Templates (Dataset-Trained).

Each micro_brain intent maps to a template response string.
No LLM calls — responses are selected based on intent classification.

Maps micro_brain INTENT names → (action, response_template_or_fn)
"""

import logging
from datetime import datetime
from typing import Callable, Dict, Tuple, Union

logger = logging.getLogger(__name__)

# ── Simple string templates ────────────────────────────────────
RESPONSES: Dict[str, Union[str, Callable]] = {
    # ── General ──
    "CHAT":             "Bolo {name}! Kya help chahiye? 😊",
    "GENERAL_KNOWLEDGE": "Yeh sawaal hai? Mujhe iska jawab dataset mein nahi mila. Kuch aur poocho? 🤔",
    "CAPABILITIES":     "Main AND9 hoon — {name} ka AI assistant! Main apps khol sakta hoon, music chala sakta hoon, reminders set kar sakta hoon, web search kar sakta hoon, aur bhi bahut kuch! 🚀",

    # ── Apps & Device ──
    "OPEN_APP":         lambda q: f"{q.replace('open ','').replace('kholo','').strip()} khol raha hoon! 📱",
    "CLOSE_APP":        lambda q: f"App band kar raha hoon! 📱",
    "HOME":             "Home screen pe ja raha hoon! 🏠",
    "BACK":             "Back ja raha hoon! ↩️",
    "SETTING":          "Settings khol raha hoon! ⚙️",

    # ── Media ──
    "PLAY_MUSIC":       lambda q: f"Music chala raha hoon! 🎵",
    "PAUSE_MUSIC":      "Music rok diya! ⏸️",

    # ── Camera & Flash ──
    "CAMERA":           "Camera khol raha hoon! 📸",
    "FLASHLIGHT_ON":    "Flashlight on kar diya! 💡",
    "FLASHLIGHT_OFF":   "Flashlight off kar diya! 💡",

    # ── Volume ──
    "VOLUME_UP":        "Volume badha diya! 🔊",
    "VOLUME_DOWN":      "Volume kam kar diya! 🔉",

    # ── Communication ──
    "CALL":             lambda q: f"Call kar raha hoon... 📞",
    "MESSAGE":          lambda q: f"Message bhej raha hoon... 💬",

    # ── Utilities ──
    "TIME":             lambda q: f"Abhi waqt hai: {datetime.now().strftime('%I:%M %p')} 🕐",
    "DATE":             lambda q: f"Aaj ki tarikh: {datetime.now().strftime('%d %B %Y')} 📅",
    "WEATHER":          "Weather check kar raha hoon... 🌤️ Iske liye internet search use karein.",
    "SEARCH_WEB":       None,  # Handled separately — returns DuckDuckGo results
    "REMINDER":         None,  # Handled separately — creates reminder via events system

    # ── Coding / Knowledge ──
    "PYTHON_CODING":    "Coding help chahiye? Aap {coding_language} mein kaam karte hain. Kya bana na hai {name}? Mera neural model basic guidance de sakta hai! 💻",
    "WEB_CODING":       "Web development query? Aap {preferred_stack} use karte hain. Main basic HTML/CSS/JS guidance de sakta hoon {name}! 🌐",
    "AI_NEWS_MODELS":   "AI ke baare mein baat karte hain! Main ek neural network hoon jo dataset par trained hai. 🧠",
    "MEDICINE_KNOWLEDGE": "Medical query ke liye main doctor nahi hoon. Kripya kisi professional se salah karein! ⚕️",
    "MOVIE_KNOWLEDGE":  "Movie ke baare mein baat karte hain! Kya dekhna chahte hain? 🎬",

    # ── Fallback ──
    "UNKNOWN":          "Mujhe samajh nahi aaya. Kya kar sakta hoon aapke liye? 😊",
}


def get_response(intent: str, query: str = "") -> str:
    """Get the response template for a given intent.

    Args:
        intent: Intent string from micro_brain (e.g. "OPEN_APP", "CHAT").
        query: Original user query (used for lambda templates).

    Returns:
        Response string.
    """
    template = RESPONSES.get(intent, RESPONSES["UNKNOWN"])
    if template is None:
        return ""  # Caller should handle specially
    if callable(template):
        try:
            return template(query)
        except Exception as e:
            logger.warning("Response template failed for %s: %s", intent, e)
            return RESPONSES["UNKNOWN"]
    return template


# ── Intent → Action Type mapping ───────────────────────────────
INTENT_TO_ACTION: Dict[str, str] = {
    "OPEN_APP":           "open_app",
    "CLOSE_APP":          "close_app",
    "PLAY_MUSIC":         "play_music",
    "PAUSE_MUSIC":        "pause_music",
    "SEARCH_WEB":         "search",
    "WEATHER":            "search",
    "TIME":               "get_time",
    "DATE":               "get_date",
    "REMINDER":           "set_reminder",
    "CALL":               "make_call",
    "MESSAGE":            "send_message",
    "CAMERA":             "open_camera",
    "FLASHLIGHT_ON":      "flashlight_on",
    "FLASHLIGHT_OFF":     "flashlight_off",
    "VOLUME_UP":          "volume_up",
    "VOLUME_DOWN":        "volume_down",
    "HOME":               "go_home",
    "BACK":               "go_back",
    "SETTING":            "open_settings",
    "CHAT":               "chat",
    "CAPABILITIES":       "chat",
    "PYTHON_CODING":      "chat",
    "WEB_CODING":         "chat",
    "AI_NEWS_MODELS":     "chat",
    "GENERAL_KNOWLEDGE":  "chat",
    "MEDICINE_KNOWLEDGE": "chat",
    "MOVIE_KNOWLEDGE":    "chat",
    "UNKNOWN":            "chat",
}

# ── Intent → IntentType enum value mapping ─────────────────────
INTENT_TO_TYPE: Dict[str, str] = {
    "OPEN_APP":           "OPEN_APP",
    "CLOSE_APP":          "CLOSE_APP",
    "PLAY_MUSIC":         "PLAY_MUSIC",
    "PAUSE_MUSIC":        "PAUSE_MUSIC",
    "SEARCH_WEB":         "SEARCH",
    "WEATHER":            "SEARCH",
    "TIME":               "TIME",
    "DATE":               "DATE",
    "REMINDER":           "SET_REMINDER",
    "CALL":               "CALL",
    "MESSAGE":            "MESSAGE",
    "CAMERA":             "CAMERA",
    "FLASHLIGHT_ON":      "FLASHLIGHT",
    "FLASHLIGHT_OFF":     "FLASHLIGHT",
    "VOLUME_UP":          "VOLUME_UP",
    "VOLUME_DOWN":        "VOLUME_DOWN",
    "HOME":               "GO_HOME",
    "BACK":               "GO_BACK",
    "SETTING":            "OPEN_SETTINGS",
    "CHAT":               "CHAT",
    "CAPABILITIES":       "CHAT",
    "PYTHON_CODING":      "CHAT",
    "WEB_CODING":         "CHAT",
    "AI_NEWS_MODELS":     "CHAT",
    "GENERAL_KNOWLEDGE":  "CHAT",
    "MEDICINE_KNOWLEDGE": "CHAT",
    "MOVIE_KNOWLEDGE":    "CHAT",
    "UNKNOWN":            "CHAT",
}
