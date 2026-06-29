"""
app/core/intent_router.py — Keyword-based intent router (zero LLM).

Extracted from the old Jarvis Orchestrator for the test suite. This is a
simple, fast keyword router used by legacy tests. The active pipeline
uses NeuralBridge from backend/cognition/neural/ instead.
"""


class IntentRouter:
    """Keyword-based intent router. Fast, zero LLM calls."""

    PATTERNS = {
        "search":   ["find", "look up", "google", "news", "weather", "who is", "what is"],
        "research": ["in-depth", "comprehensive", "tell me everything about", "deep dive", "history of"],
        "music":    ["song", "gaana", "music", "gana", "sunna", "laga do", "bajao",
                     "play", "baja do", "track", "playlist", "singer", "soft song",
                     "sad song", "romantic", "sunao", "ghazal", "bhajan"],
        "goal":     ["goal", "target", "aim", "objective", "lakshya", "mera goal",
                     "add goal", "new goal", "set goal", "complete goal", "goals kya hain",
                     "project", "kaam", "task", "todo", "to do", "meri list"],
        "reminder": ["remind", "reminder", "yaad dilana", "yaad dila", "mat bhoolna",
                     "event", "meeting", "schedule", "appointment", "alert"],
        "reflection":["daily review", "aaj kya kiya", "session summary", "reflect",
                      "din ka summary", "review karo", "kya kiya aaj"],
        "device":   ["turn on", "turn off", "enable", "disable", "wifi", "wi-fi",
                     "bluetooth", "torch", "flashlight", "volume", "brightness", "battery",
                     "camera", "photo", "youtube", "whatsapp", "chrome", "calculator",
                     "maps", "telegram", "spotify", "instagram", "alarm", "call", "dial",
                     "contact", "contacts", "file", "folder", "directory", "storage",
                     "open ", "launch ", "kholo", "band karo", "gmail", "settings",
                     "gallery", "netflix", "facebook", "twitter", "snapchat", "zoom",
                     "phonepe", "paytm", "gpay", "google pay", "amazon", "flipkart",
                     "clock", "timer", "set alarm", "set timer", "play store", "drive"],
    }

    def route(self, query: str) -> str:
        """Classify a user query into an intent category using keyword matching.

        Iterates through predefined patterns for image, reflection, device, goal,
        reminder, music, search, coding, and research intents. Falls back to "chat"
        when no keywords match. Prioritises higher-specificity patterns first.

        Args:
            query: The raw user input string.

        Returns:
            A string key identifying the intent category (e.g. "search", "music",
            "goal", "chat").
        """
        q = query.lower().strip()
        if not q:
            return "chat"

        if any(kw in q for kw in self.PATTERNS.get("image", [])):
            return "image"
        if any(kw in q for kw in self.PATTERNS["reflection"]):
            return "reflection"
        if any(kw in q for kw in self.PATTERNS["device"]):
            return "device"
        if any(kw in q for kw in self.PATTERNS["goal"]):
            return "goal"
        if any(kw in q for kw in self.PATTERNS["reminder"]):
            return "reminder"
        if any(kw in q for kw in self.PATTERNS["music"]):
            return "music"
        if q.startswith("search") or q.startswith("find ") or q.startswith("look up") or q.startswith("google"):
            return "search"
        if any(kw in q for kw in self.PATTERNS.get("coding", [])):
            return "coding"
        if q.startswith("research") or any(kw in q for kw in self.PATTERNS["research"]):
            return "research"
        if any(kw in q for kw in self.PATTERNS["search"]):
            return "search"

        return "chat"
