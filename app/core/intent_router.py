"""
app/core/intent_router.py — LLM-powered Intent Router.

Replaces the old keyword-based IntentRouter with an LLM that
understands natural language in Hinglish / English / Hindi.

Every command is classified into one intent with extracted parameters.
"""
import json
import re
import time
import logging
import hashlib

logger = logging.getLogger(__name__)

CLASSIFY_PROMPT = """You are JARVIS's intent classifier. Analyze the user's message and classify it into exactly ONE intent. Extract relevant parameters.

Respond ONLY with valid JSON: {"intent": "...", "parameters": {...}, "confidence": 0.0-1.0}

INTENTS:

1. music — Play a song, gaana, music
   Parameters: {"song": string|null, "artist": string|null, "mood": string|null}
   Examples: "Tum Hi Ho sunao", "song laga do", "Arijit Singh ka gaana bajao", "play Despacito", "soft music chalao", "party songs", "koi achha gaana sunao", "gaana chalao", "sunao kuch", "bajao koi song", "youtube pe gaana play karo", "sad song sunao", "bhajan bajao", "ghazal sunao"

2. device_app — Open/launch an app
   Parameters: {"app_name": string}
   Examples: "youtube open karo", "whatsapp kholo", "calculator chalao", "open chrome", "maps kholo", "instagram start karo", "telegram open karo", "camera kholo", "gmail kholo", "play store kholo", "settings kholo", "phone kholo", "spotify chalao", "app kholo", "calculator open karo", "camera app chalao"

3. device_call — Make a phone call
   Parameters: {"name": string|null, "number": string|null}
   Examples: "Mummy ko call karo", "phone karo", "dial +919876543210", "call karo", "Papa ko phone lagao", "call 9876543210", "mujhe ghar pe call karna hai", "contact karo"

4. device_control — Change device settings / system control
   Parameters: {"action": string, "target": string, "state": bool|null}
   Examples: "flashlight on karo", "torch off karo", "wifi on karo", "bluetooth enable karo", "volume up karo", "volume down karo", "brightness badhao", "battery status batao", "photo click karo", "wifi band karo", "flashlight off", "screenshot lo"

5. timer — Set a countdown / alarm
   Parameters: {"duration_seconds": int|null, "label": string}
   Examples: "5 minute ka timer laga do", "30 second ka alarm", "2 hour ka countdown", "timer set karo 10 minutes ka", "10 minute baad yaad dilana", "alarm laga do 1 minute ka", "countdown 20 seconds", "wake me up in 15 minutes"

6. reminder — Set or list reminders
   Parameters: {"action": "create"|"list", "title": string|null, "time": string|null}
   Examples: "remind me to buy groceries at 5pm", "kal subah 8 baje yaad dilana", "meri reminders dikhao", "meeting schedule karo", "yaad dilana dinner ka", "event add karo"

7. goal — Manage goals / tasks
   Parameters: {"action": "add"|"list"|"complete", "title": string|null}
   Examples: "goal add karo", "mera goal list dikhao", "goal complete karo", "task banao", "project add karo", "kaunse goals hain", "mera target dikhao", "add a goal", "show my goals", "meri list dikhao", "lakshya add karo"

8. search — Quick web search
   Parameters: {"query": string}
   Examples: "latest news batao", "weather kya hai", "google karo AI ke baare mein", "search karo", "who is Narendra Modi", "what is python", "iPhone 16 price", "today's news", "goggle karo", "ke baare mein batao", "find information about"

9. research — Deep multi-source research
   Parameters: {"query": string}
   Examples: "research karo climate change", "in-depth batao AI ke baare mein", "deep dive history of India", "comprehensive analysis", "tell me everything about"

10. image — Generate an AI image
    Parameters: {"prompt": string}
    Examples: "generate image of sunset mountain", "ek sher ka photo banao", "draw a cat wearing a hat", "AI se photo banwao", "create an image of", "make a picture of", "paint karo", "image generate karo"

11. coding — Code help / programming
    Parameters: {"query": string, "language": string|null}
    Examples: "python mein code likho calculator ka", "bug fix karo", "function banao", "javascript mein program likho", "debug karo", "code explain karo", "python mein sort function"

12. reflection — Daily review or session summary
    Parameters: {}
    Examples: "daily review karo", "aaj kya kiya", "din ka summary batao", "session summary", "review karo", "reflect karo", "aaj ka digest"

13. memory — Recall past conversations
    Parameters: {"query": string}
    Examples: "yaad hai tune kya kaha tha", "pehle kya hua", "humne kya baat ki thi", "memory check karo", "kya bola tha maine", "pehle wali baat yaad karo", "recall karo", "history batao"

14. chat — Default: general conversation, greetings, casual
    Parameters: {}
    Examples: "hello", "kaise ho", "kya haal hai", "what's up", "how are you", "general questions"

RULES:
- Choose ONLY ONE intent
- Set confidence >0.9 if clear match, <0.6 if unsure
- For device_app, extract app_name as spoken (youtube, calculator, etc.)
- For music, extract song name WITHOUT action words (remove "sunao", "bajao", "chalao", "play", "laga do")
- Respond ONLY with the JSON object, no other text"""


class LLMIntentRouter:
    """LLM-powered intent classifier with TTL cache and fallback."""

    def __init__(self, cache_ttl: int = 60):
        self._cache_ttl = cache_ttl
        self._cache: dict[str, tuple[float, dict]] = {}

    def classify(self, query: str) -> dict:
        """Classify a user query into intent + parameters.

        Returns:
            {"intent": str, "parameters": dict, "confidence": float}
        """
        query = query.strip()
        if not query:
            return {"intent": "chat", "parameters": {}, "confidence": 1.0}

        # Check cache
        cache_key = hashlib.md5(query.lower().encode()).hexdigest()
        cached = self._cache.get(cache_key)
        if cached and (time.time() - cached[0]) < self._cache_ttl:
            return cached[1]

        result = self._classify_via_llm(query)

        # Cache the result
        self._cache[cache_key] = (time.time(), result)
        return result

    def _classify_via_llm(self, query: str) -> dict:
        """Ask the LLM to classify the query."""
        from app.core.brain import ask_llm

        try:
            response = ask_llm(
                [
                    {"role": "system", "content": CLASSIFY_PROMPT},
                    {"role": "user", "content": f"Message: {query}"},
                ],
                temperature=0.1,
                max_tokens=300,
            )
            if response:
                cleaned = response.strip()
                match = re.search(r"\{.*\}", cleaned, re.DOTALL)
                if match:
                    result = json.loads(match.group(0))
                    intent = result.get("intent", "chat")
                    params = result.get("parameters", {})
                    confidence = result.get("confidence", 0.5)
                    return {
                        "intent": intent,
                        "parameters": params if isinstance(params, dict) else {},
                        "confidence": float(confidence),
                    }
        except Exception as e:
            logger.debug(f"LLM classify failed: {e}")

        return self._fallback_classify(query)

    def _fallback_classify(self, query: str) -> dict:
        """Fallback keyword-based classification when LLM fails."""
        q = query.lower()

        patterns: list[tuple[str, list[str]]] = [
            ("timer", ["timer", "countdown", "alarm", "seconds", "minutes",
                       "minute", "sec", "min", "wake me up"]),
            ("music", ["song", "gaana", "ga na", "sunao", "bajao", "chalao",
                       "laga do", "music", "play", "track", "singer", "mood",
                       "bhajan", "ghazal"]),
            ("memory", ["yaad hai", "yaad karo", "pehle kya", "recall",
                        "history batao", "kya bola tha", "memory check"]),
            ("reflection", ["daily review", "aaj kya kiya", "session summary",
                            "review karo", "din ka summary", "reflect"]),
            ("reminder", ["remind", "yaad dilana", "event", "meeting",
                          "schedule", "appointment"]),
            ("goal", ["goal", "target", "lakshya", "task", "todo",
                      "kaam", "project", "aim", "objective"]),
            ("device_app", ["open karo", "kholo", "chalao", "start karo",
                            "launch", "open ", "app kholo"]),
            ("device_call", ["call karo", "phone karo", "dial", "ko call",
                             "phone lagao", "contact karo"]),
            ("device_control", ["turn on", "turn off", "on karo", "off karo",
                                "flashlight", "wifi", "bluetooth", "volume",
                                "brightness", "battery", "screenshot"]),
            ("image", ["generate image", "create image", "draw", "photo banao",
                       "make a picture", "paint", "ai se"]),
            ("research", ["research", "in-depth", "deep dive", "comprehensive",
                          "tell me everything about"]),
            ("search", ["search", "google", "find", "look up", "news",
                        "weather", "ke baare mein batao"]),
            ("coding", ["code", "python", "javascript", "program", "function",
                        "bug", "debug", "algorithm"]),
        ]

        for intent, keywords in patterns:
            if any(kw in q for kw in keywords):
                params = self._extract_fallback_params(intent, q)
                return {"intent": intent, "parameters": params, "confidence": 0.7}

        return {"intent": "chat", "parameters": {}, "confidence": 0.6}

    @staticmethod
    def _extract_fallback_params(intent: str, q: str) -> dict:
        """Extract basic parameters from query for fallback mode."""
        if intent == "device_app":
            # English verb-noun: "open chrome", "launch youtube"
            match = re.search(r"\b(?:open|launch)\s+(\w+)", q)
            if match:
                return {"app_name": match.group(1)}
            # Hinglish verb-noun: "open karo calculator", "kholo youtube"
            match = re.search(r"\b(?:open\s+karo|kholo|chalao|start\s+karo|launch)\s+(\w+)", q)
            if match:
                return {"app_name": match.group(1)}
            # Hinglish noun-verb: "calculator kholo", "youtube chalao", "whatsapp open karo"
            match = re.search(r"(\w+)\s+(?:kholo|chalao|open\s+karo|start\s+karo)", q)
            if match:
                return {"app_name": match.group(1)}
            return {"app_name": q}

        if intent == "music":
            # Remove known action phrases
            cleaned = re.sub(
                r"\b(sunao|bajao|chalao|play|laga do|song|gaana|music|ga na|koi|achha)\b",
                "", q, flags=re.IGNORECASE
            ).strip()
            if cleaned:
                return {"song": cleaned}
            return {"song": q}

        if intent == "timer":
            match = re.search(r"(\d+)\s*(hour|ghante|minute|min|second|sec)", q)
            if match:
                num = int(match.group(1))
                unit = match.group(2)
                multipliers = {"hour": 3600, "ghante": 3600, "minute": 60, "min": 60,
                               "second": 1, "sec": 1}
                secs = num * multipliers.get(unit, 60)
                return {"duration_seconds": secs, "label": "Alarm"}
            return {"duration_seconds": None, "label": "Alarm"}

        if intent == "goal":
            if any(w in q for w in ["list", "show", "dikhao", "kya hain", "batao"]):
                return {"action": "list"}
            if any(w in q for w in ["complete", "done", "khatam", "finish"]):
                return {"action": "complete"}
            return {"action": "add", "title": q}

        if intent == "reminder":
            if any(w in q for w in ["list", "show", "dikhao", "kya hain", "upcoming"]):
                return {"action": "list"}
            return {"action": "create", "title": q}

        if intent == "device_call":
            match = re.search(r"(\w+)\s+ko\s+call", q)
            if match:
                return {"name": match.group(1)}
            match = re.search(r"call\s+(\w+)", q)
            if match:
                return {"name": match.group(1)}
            match = re.search(r"call\s+([\d\+\s]+)", q)
            if match:
                return {"number": match.group(1).strip()}
            return {"name": q.replace("call karo", "").replace("phone karo", "").strip()}

        if intent == "search":
            cleaned = re.sub(r"\b(search|google|find|look up|ke baare mein batao)\b",
                             "", q, flags=re.IGNORECASE).strip()
            return {"query": cleaned or q}

        if intent == "image":
            cleaned = re.sub(r"\b(generate image|create image|draw|photo banao|make a picture|paint|ai se)\b",
                             "", q, flags=re.IGNORECASE).strip()
            return {"prompt": cleaned or q}

        return {}
