"""
╔══════════════════════════════════════════════════╗
║           BRAIN 1: REFLEX BRAIN                  ║
║   Instant actions. No reasoning. <50ms.          ║
╚══════════════════════════════════════════════════╝

Purpose:
    Instant pattern-match to action execution.
    No neural network, no reasoning.

Architecture:
    Input Command → Pattern Match → Action Execution

Response Time:
    <50ms target
"""

import os
import re
import json
import time
import subprocess
from typing import Optional, Callable, Dict, List, Tuple
from dataclasses import dataclass, field

from config import REFLEX_CONFIG, INTENTS
from utils.logger import get_logger
from utils.timezone_utils import detect_city_time_query, format_city_time_response

logger = get_logger()


@dataclass
class Action:
    """An executable action registered in the reflex brain."""
    name: str
    intent: str
    description: str
    handler: Optional[Callable] = None
    keywords: List[str] = field(default_factory=list)
    android_action: Optional[str] = None
    requires_termux: bool = False


class ReflexBrain:
    """
    Reflex Brain - Instant action execution via pattern matching.

    This brain does NOT use neural networks.
    It uses fast keyword/pattern matching to execute actions instantly.
    """

    def __init__(self):
        self.actions: Dict[str, Action] = {}
        self.intent_cache: Dict[str, str] = {}  # query → intent
        self._action_registry: Dict[str, List[Action]] = {}  # intent → actions
        self._is_android = self._detect_android()
        self._setup_default_actions()

    def _detect_android(self) -> bool:
        """Detect if running on Android Termux."""
        try:
            return "TERMUX_VERSION" in os.environ
        except Exception:
            return False

    def _setup_default_actions(self):
        """Register default action mappings."""
        # ── APP ACTIONS ────────────────────────────────────
        apps = {
            "whatsapp": "com.whatsapp",
            "youtube": "com.google.android.youtube",
            "chrome": "com.android.chrome",
            "telegram": "org.telegram.messenger",
            "instagram": "com.instagram.android",
            "gmail": "com.google.android.gm",
            "maps": "com.google.android.apps.maps",
            "camera": "com.android.camera2",
            "phone": "com.android.dialer",
            "contacts": "com.android.contacts",
            "gallery": "com.android.gallery3d",
            "settings": "com.android.settings",
            "calculator": "com.android.calculator2",
            "calendar": "com.android.calendar",
            "clock": "com.android.deskclock",
            "playstore": "com.android.vending",
            "spotify": "com.spotify.music",
            "files": "com.android.documentsui",
            "messages": "com.android.messaging",
            "twitter": "com.twitter.android",
        }

        for app_name, pkg in apps.items():
            keywords = [
                f"open {app_name}",
                f"open {app_name} app",
                f"{app_name} kholo",
                f"{app_name} open kar",
                f"{app_name} open karo",
                f"{app_name} khol do",
                f"{app_name} kholo",
                f"launch {app_name}",
                f"start {app_name}",
                f"khole {app_name}",
                f"{app_name} chalao",
                f"{app_name} chalao",
            ]
            self.register_action(Action(
                name=f"open_{app_name}",
                intent="OPEN_APP",
                description=f"Open {app_name}",
                keywords=keywords,
                android_action=pkg,
                requires_termux=self._is_android,
            ))

        # ── CLOSE APP ──────────────────────────────────────
        close_keywords = [
            "close app", "close", "exit", "band karo", "band kar",
            "close karo", "exit karo", "close this app",
        ]
        self.register_action(Action(
            name="close_app",
            intent="CLOSE_APP",
            description="Close current application",
            keywords=close_keywords,
            requires_termux=True,
        ))

        # ── MEDIA ACTIONS ─────────────────────────────────
        self.register_action(Action(
            name="play_music",
            intent="PLAY_MUSIC",
            description="Play music",
            keywords=[
                "play music", "play song", "play some music",
                "music play karo", "gaana chalao", "song play karo",
                "music on karo", "music start karo", "bajao kuch",
                "music play", "play gaana", "song chalao",
            ],
        ))
        self.register_action(Action(
            name="pause_music",
            intent="PAUSE_MUSIC",
            description="Pause music",
            keywords=[
                "pause music", "pause song", "stop music",
                "music rok do", "song rok do", "gaana band kar",
                "pause karo", "stop karo", "music off karo",
                "music band kar", "song pause karo",
            ],
        ))

        # ── SEARCH / WEB ──────────────────────────────────
        self.register_action(Action(
            name="search_web",
            intent="SEARCH_WEB",
            description="Search the web",
            keywords=[
                "search", "search web", "google search",
                "search internet", "search karo", "dhoondho",
                "google karo", "search online", "find",
                "look for", "search google", "web search",
                "internet pe search karo", "google pe search karo",
                "search kar", "dhundh",
            ],
        ))

        # ── WEATHER ───────────────────────────────────────
        self.register_action(Action(
            name="weather",
            intent="WEATHER",
            description="Check weather",
            keywords=[
                "weather", "weather kaisa hai", "mausam",
                "temperature", "mausam kaisa hai", "aaj kya mausam hai",
                "weather report", "weather today", "weather update",
                "mausam ki jaankari", "aaj kaisa mausam hai",
                "outside temperature",
            ],
        ))

        # ── TIME ──────────────────────────────────────────
        self.register_action(Action(
            name="time",
            intent="TIME",
            description="Tell current time",
            keywords=[
                "time", "what time is it", "current time",
                "time batao", "samay batao", "kitna bajaa",
                "kitne baje", "time kya hai", "current time batao",
                "what's the time", "samay kya hai",
                "ghanti batao", "time do",
                "kolkata time", "delhi time", "mumbai time",
                "kolkata ka time", "delhi ka time", "mumbai ka time",
                "kolkata ka samay", "delhi ka samay",
                "india time", "india ka time",
            ],
        ))

        # ── DATE ──────────────────────────────────────────
        self.register_action(Action(
            name="date",
            intent="DATE",
            description="Tell current date",
            keywords=[
                "date", "what is today's date", "today's date",
                "date batao", "tareekh batao", "aaj ki tareekh",
                "aaj kya date hai", "current date", "what day is it",
                "aaj konsa din hai", "tareekh kya hai",
                "date do", "din batao",
            ],
        ))

        # ── FLASHLIGHT ────────────────────────────────────
        self.register_action(Action(
            name="flashlight_on",
            intent="FLASHLIGHT_ON",
            description="Turn flashlight on",
            keywords=[
                "flashlight on", "torch on", "flash on",
                "flashlight chalu kar", "torch chalu kar",
                "light on karo", "flashlight on karo",
                "torch on karo", "flash on karo",
                "light chalu karo", "flashlight jalao",
                "torch jalao",
            ],
            requires_termux=True,
        ))
        self.register_action(Action(
            name="flashlight_off",
            intent="FLASHLIGHT_OFF",
            description="Turn flashlight off",
            keywords=[
                "flashlight off", "torch off", "flash off",
                "flashlight band kar", "torch band kar",
                "light off karo", "flashlight off karo",
                "torch off karo", "flash off karo",
                "light band karo", "flashlight bujhao",
                "torch bujhao",
            ],
            requires_termux=True,
        ))

        # ── VOLUME ────────────────────────────────────────
        self.register_action(Action(
            name="volume_up",
            intent="VOLUME_UP",
            description="Increase volume",
            keywords=[
                "volume up", "increase volume", "volume increase karo",
                "volume badhao", "aawaz badhao", "sound badhao",
                "volume up karo", "louder", "tez karo",
                "volume plus", "aawaz tez karo",
            ],
            requires_termux=True,
        ))
        self.register_action(Action(
            name="volume_down",
            intent="VOLUME_DOWN",
            description="Decrease volume",
            keywords=[
                "volume down", "decrease volume", "volume kam karo",
                "aawaz kam karo", "sound kam karo", "volume low karo",
                "quieter", "halka karo", "volume minus",
                "aawaz halki karo", "dheere karo",
            ],
            requires_termux=True,
        ))

        # ── NAVIGATION ────────────────────────────────────
        self.register_action(Action(
            name="go_home",
            intent="HOME",
            description="Go to home screen",
            keywords=[
                "go home", "home screen", "home", "home par jao",
                "home pe jao", "home screen dikhao",
                "main screen", "desktop dikhao",
            ],
            requires_termux=True,
        ))
        self.register_action(Action(
            name="go_back",
            intent="BACK",
            description="Go back",
            keywords=[
                "go back", "back", "back karo", "peeche jao",
                "wapis jao", "back button", "pichhle page",
                "pichhe jao",
            ],
            requires_termux=True,
        ))

        # ── SETTINGS ──────────────────────────────────────
        self.register_action(Action(
            name="open_settings",
            intent="SETTING",
            description="Open settings",
            keywords=[
                "open settings", "settings", "setting",
                "settings kholo", "setting kholo",
                "settings open karo", "setting open kar",
                "settings dikhao",
            ],
        ))

        # ── REMINDER ──────────────────────────────────────
        self.register_action(Action(
            name="reminder",
            intent="REMINDER",
            description="Set a reminder",
            keywords=[
                "remind me", "set reminder", "reminder",
                "mujhe yaad dilao", "yaad dila", "reminder set karo",
                "reminder lagao", "yaad rakhna",
            ],
        ))

        # ── CALL ──────────────────────────────────────────
        self.register_action(Action(
            name="call",
            intent="CALL",
            description="Make a phone call",
            keywords=[
                "call", "phone call", "call karo",
                "phone karo", "call kar", "fone karo",
                "dial", "phone lagao",
            ],
        ))

        # ── MESSAGE ───────────────────────────────────────
        self.register_action(Action(
            name="message",
            intent="MESSAGE",
            description="Send a message",
            keywords=[
                "message", "send message", "text",
                "message bhejo", "text karo", "message kar",
                "sms bhejo", "msg bhejo", "text bhejo",
            ],
        ))

        # ── CAMERA ────────────────────────────────────────
        self.register_action(Action(
            name="camera",
            intent="CAMERA",
            description="Open camera",
            keywords=[
                "camera", "open camera", "camera kholo",
                "photo lena hai", "picture lena hai",
                "selfie lena hai", "photo khinch",
                "camera open karo", "camera chalao",
                "picture khinch",
            ],
        ))

        logger.info(f"ReflexBrain: Registered {len(self.actions)} actions")

    def register_action(self, action: Action):
        """Register a new action."""
        self.actions[action.name] = action
        if action.intent not in self._action_registry:
            self._action_registry[action.intent] = []
        self._action_registry[action.intent].append(action)

    def match_intent(self, query: str) -> Tuple[str, float, Optional[Action]]:
        """
        Match a query to an intent using fast pattern matching.
        Returns (intent, confidence, matched_action).
        """
        if not query:
            return "UNKNOWN", 0.0, None

        # Check cache first
        query_lower = query.lower().strip()
        if query_lower in self.intent_cache:
            cached_intent = self.intent_cache[query_lower]
            action = self._find_action_for_intent(cached_intent, query_lower)
            return cached_intent, 0.95, action

        # Score each action's keywords against the query
        best_score = 0.0
        best_intent = "UNKNOWN"
        best_action = None

        for action in self.actions.values():
            for keyword in action.keywords:
                score = self._match_score(query_lower, keyword.lower())
                if score > best_score:
                    best_score = score
                    best_intent = action.intent
                    best_action = action
                if best_score >= 1.0:
                    break
            if best_score >= 1.0:
                break

        # Cache the result for fast lookup
        if best_score >= 0.5 and len(self.intent_cache) < REFLEX_CONFIG["cache_size"]:
            self.intent_cache[query_lower] = best_intent

        confidence = min(1.0, best_score)
        return best_intent, confidence, best_action

    def _match_score(self, query: str, keyword: str) -> float:
        """Calculate how well a query matches a keyword."""
        if keyword == query:
            return 1.0
        if keyword in query:
            return 0.9
        # Check word overlap
        query_words = set(query.split())
        keyword_words = set(keyword.split())
        if not keyword_words:
            return 0.0
        overlap = len(query_words & keyword_words)
        if overlap == len(keyword_words):
            return 0.85
        # Partial overlap
        jaccard = overlap / len(keyword_words | query_words)
        return jaccard * 0.7

    def _find_action_for_intent(self, intent: str, query: str) -> Optional[Action]:
        """Find the best action for a given intent and query."""
        actions = self._action_registry.get(intent, [])
        if not actions:
            return None
        if len(actions) == 1:
            return actions[0]
        # Find best matching action by keywords
        best_score = 0.0
        best_action = actions[0]
        for action in actions:
            for kw in action.keywords:
                score = self._match_score(query, kw)
                if score > best_score:
                    best_score = score
                    best_action = action
        return best_action

    def execute_action(self, action: Action, query: str = "") -> dict:
        """Execute an action and return the result."""
        start_time = time.time()
        result = {"success": False, "message": "", "action": action.name, "duration_ms": 0}

        try:
            if self._is_android and action.requires_termux:
                result = self._execute_termux(action, query)
            else:
                result = self._execute_fallback(action, query)

            duration_ms = (time.time() - start_time) * 1000
            result["duration_ms"] = round(duration_ms, 2)

            if result["success"]:
                logger.info(f"Reflex: Executed {action.name} in {duration_ms:.1f}ms")
            else:
                logger.warning(f"Reflex: Failed {action.name}: {result['message']}")

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            result["duration_ms"] = round(duration_ms, 2)
            result["success"] = False
            result["message"] = str(e)
            logger.error(f"Reflex: Error executing {action.name}: {e}")

        return result

    def _execute_termux(self, action: Action, query: str) -> dict:
        """Execute action via Termux API."""
        try:
            pkg = action.android_action
            if pkg:
                # Open app via Termux
                result = subprocess.run(
                    ["am", "start", "-n", f"{pkg}/.MainActivity"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    return {"success": True, "message": f"Opened {action.name.replace('open_', '')}"}
                else:
                    return {"success": False, "message": result.stderr.strip()}

            action_map = {
                "flashlight_on": "termux-torch on",
                "flashlight_off": "termux-torch off",
                "go_home": "input keyevent 3",
                "go_back": "input keyevent 4",
                "volume_up": "input keyevent 24",
                "volume_down": "input keyevent 25",
                "close_app": "input keyevent 3",
            }

            if action.name in action_map:
                cmd = action_map[action.name]
                result = subprocess.run(
                    cmd.split(), capture_output=True, text=True, timeout=3
                )
                if result.returncode == 0:
                    return {"success": True, "message": f"Executed {action.name}"}
                else:
                    return {"success": False, "message": result.stderr.strip()}

            return {"success": True, "message": f"Action {action.name} noted (Termux)"}

        except Exception as e:
            return {"success": False, "message": str(e)}

    def _execute_fallback(self, action: Action, query: str) -> dict:
        """Fallback execution when not on Android."""
        if action.name == "time" and query:
            from utils.timezone_utils import detect_city_time_query, get_time_in_city, format_city_time_response
            city = detect_city_time_query(query)
            if city:
                info = get_time_in_city(city)
                if info:
                    msg = format_city_time_response(city)
                    logger.info(f"Reflex: City time for {city} → {msg}")
                    return {"success": True, "message": msg}

            # Default: current local time
            from datetime import datetime
            now = datetime.now()
            msg = now.strftime("Current time is %I:%M:%S %p (%A, %B %d, %Y)")
            return {"success": True, "message": msg}

        logger.info(f"Reflex (Desktop): Would execute {action.name}")
        return {
            "success": True,
            "message": f"[Desktop Sim] {action.description}",
        }

    def get_intent_from_reflex(self, query: str) -> Tuple[str, float, Optional[Action]]:
        """Public interface: match query to intent via reflex."""
        return self.match_intent(query)

    def get_stats(self) -> dict:
        """Get reflex brain statistics."""
        return {
            "actions_registered": len(self.actions),
            "cache_size": len(self.intent_cache),
            "android_mode": self._is_android,
            "intents_covered": len(self._action_registry),
        }
