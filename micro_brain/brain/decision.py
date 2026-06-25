"""
╔══════════════════════════════════════════════════╗
║           BRAIN 4: DECISION BRAIN               ║
║   Choose actions based on intent + memory + ctx  ║
╚══════════════════════════════════════════════════╝

Purpose:
    Select the best action given:
    - Intent from Neural/Reflex Brain
    - Context from Memory Brain
    - Current state and history

Architecture:
    Input (Intent + Memory + Context)
    → Decision Engine
    → Confidence Scoring
    → Action Plan Output
"""

import re
import time
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass, field

from config import DECISION_CONFIG, INTENTS
from utils.logger import get_logger

logger = get_logger()


@dataclass
class ActionPlan:
    """A decided action plan."""
    intent: str
    action: str
    confidence: float
    params: Dict[str, Any] = field(default_factory=dict)
    fallback_action: Optional[str] = None
    requires_confirmation: bool = False
    reasoning: List[str] = field(default_factory=list)


class DecisionBrain:
    """
    Decision Brain - Chooses the best action.

    Uses intent, context, memory, and confidence scoring
    to decide what action to take.
    """

    def __init__(self):
        self.min_confidence = DECISION_CONFIG["min_confidence_to_act"]
        self._decision_history: List[Dict] = []
        self._init_decision_map()

    def _init_decision_map(self):
        """Initialize the intent-to-decision mapping."""
        self.decision_map = {
            "OPEN_APP": {
                "action": "launch_app",
                "description": "Launch the requested application",
                "requires_entity": True,
                "fallback": "search_play_store",
                "confirmation_required": False,
            },
            "CLOSE_APP": {
                "action": "close_current_app",
                "description": "Close the current application",
                "requires_entity": False,
                "fallback": "go_home",
                "confirmation_required": False,
            },
            "PLAY_MUSIC": {
                "action": "play_music",
                "description": "Play music",
                "requires_entity": False,
                "fallback": "open_music_player",
                "confirmation_required": False,
            },
            "PAUSE_MUSIC": {
                "action": "pause_music",
                "description": "Pause music playback",
                "requires_entity": False,
                "fallback": None,
                "confirmation_required": False,
            },
            "SEARCH_WEB": {
                "action": "web_search",
                "description": "Search the internet",
                "requires_entity": True,
                "fallback": "open_browser",
                "confirmation_required": False,
            },
            "WEATHER": {
                "action": "get_weather",
                "description": "Get weather information",
                "requires_entity": False,
                "fallback": "search_weather_online",
                "confirmation_required": False,
            },
            "TIME": {
                "action": "tell_time",
                "description": "Tell the current time",
                "requires_entity": False,
                "fallback": None,
                "confirmation_required": False,
            },
            "DATE": {
                "action": "tell_date",
                "description": "Tell the current date",
                "requires_entity": False,
                "fallback": None,
                "confirmation_required": False,
            },
            "REMINDER": {
                "action": "set_reminder",
                "description": "Set a reminder",
                "requires_entity": True,
                "fallback": "ask_for_details",
                "confirmation_required": True,
            },
            "CALL": {
                "action": "make_call",
                "description": "Make a phone call",
                "requires_entity": True,
                "fallback": "open_dialer",
                "confirmation_required": True,
            },
            "MESSAGE": {
                "action": "send_message",
                "description": "Send a message",
                "requires_entity": True,
                "fallback": "open_messaging",
                "confirmation_required": True,
            },
            "CAMERA": {
                "action": "open_camera",
                "description": "Open the camera",
                "requires_entity": False,
                "fallback": None,
                "confirmation_required": False,
            },
            "FLASHLIGHT_ON": {
                "action": "flashlight_on",
                "description": "Turn flashlight on",
                "requires_entity": False,
                "fallback": None,
                "confirmation_required": False,
            },
            "FLASHLIGHT_OFF": {
                "action": "flashlight_off",
                "description": "Turn flashlight off",
                "requires_entity": False,
                "fallback": None,
                "confirmation_required": False,
            },
            "VOLUME_UP": {
                "action": "volume_up",
                "description": "Increase volume",
                "requires_entity": False,
                "fallback": None,
                "confirmation_required": False,
            },
            "VOLUME_DOWN": {
                "action": "volume_down",
                "description": "Decrease volume",
                "requires_entity": False,
                "fallback": None,
                "confirmation_required": False,
            },
            "HOME": {
                "action": "go_home",
                "description": "Go to home screen",
                "requires_entity": False,
                "fallback": None,
                "confirmation_required": False,
            },
            "BACK": {
                "action": "go_back",
                "description": "Go to previous screen",
                "requires_entity": False,
                "fallback": None,
                "confirmation_required": False,
            },
            "SETTING": {
                "action": "open_settings",
                "description": "Open system settings",
                "requires_entity": False,
                "fallback": None,
                "confirmation_required": False,
            },
            "UNKNOWN": {
                "action": "ask_clarification",
                "description": "Ask user for clarification",
                "requires_entity": False,
                "fallback": "respond_with_help",
                "confirmation_required": False,
            },
        }

    def decide(self, intent: str, confidence: float,
               context: Optional[Dict] = None,
               memory_hints: Optional[List] = None,
               query: str = "") -> ActionPlan:
        """
        Make a decision based on intent and context.

        Args:
            intent: Recognized intent
            confidence: Confidence score (0-1)
            context: Current context dict
            memory_hints: Relevant memories
            query: Original user query

        Returns:
            ActionPlan with the decided action
        """
        start = time.time()

        decision = self.decision_map.get(intent, self.decision_map["UNKNOWN"])
        reasoning = []

        # ── Step 1: Check confidence threshold ──────────
        if confidence < self.min_confidence and intent != "UNKNOWN":
            reasoning.append(f"Low confidence ({confidence:.2f}) for intent {intent}")
            # If we have reflex backup, use it
            if context and context.get("reflex_intent"):
                alt_intent = context["reflex_intent"]
                alt_conf = context.get("reflex_confidence", 0.0)
                if alt_conf > confidence:
                    reasoning.append(f"Using reflex intent: {alt_intent} ({alt_conf:.2f})")
                    intent = alt_intent
                    confidence = alt_conf
                    decision = self.decision_map.get(intent, decision)
                else:
                    reasoning.append("Confidence too low, asking clarification")
                    return ActionPlan(
                        intent="UNKNOWN",
                        action="ask_clarification",
                        confidence=confidence,
                        reasoning=reasoning,
                        requires_confirmation=False,
                    )
            else:
                reasoning.append("Confidence too low, asking clarification")
                return ActionPlan(
                    intent="UNKNOWN",
                    action="ask_clarification",
                    confidence=confidence,
                    reasoning=reasoning,
                    requires_confirmation=False,
                )

        # ── Step 2: Check memory for context ────────────
        entities = self._extract_entities(query, intent)
        reasoning.append(f"Extracted entities: {entities}")

        if decision["requires_entity"] and not entities:
            reasoning.append(f"Intent {intent} requires entity but none found")
            if decision["fallback"] and confidence > 0.8:
                reasoning.append(f"Using fallback: {decision['fallback']}")
                return ActionPlan(
                    intent=intent,
                    action=decision["fallback"],
                    confidence=confidence * 0.8,
                    params={"original_intent": intent, "query": query},
                    reasoning=reasoning,
                    requires_confirmation=False,
                )
            else:
                reasoning.append("Missing entity, asking for details")
                return ActionPlan(
                    intent=intent,
                    action="ask_for_details",
                    confidence=confidence,
                    params={"original_intent": intent, "query": query},
                    reasoning=reasoning,
                    requires_confirmation=True,
                )

        # ── Step 3: Check memory hints for preferences ──
        if memory_hints:
            for hint in memory_hints:
                if isinstance(hint, dict):
                    pref = hint.get("pref_value") or hint.get("value", "")
                    if pref:
                        reasoning.append(f"Memory hint: {pref}")
                        entities["preference"] = pref

        # ── Step 4: Build final action plan ────────────
        action_plan = ActionPlan(
            intent=intent,
            action=decision["action"],
            confidence=confidence,
            params={
                "original_query": query,
                "entities": entities,
                "description": decision["description"],
            },
            fallback_action=decision.get("fallback"),
            requires_confirmation=decision["confirmation_required"],
            reasoning=reasoning,
        )

        duration_ms = (time.time() - start) * 1000
        logger.info(
            f"DecisionBrain: {intent} → {action_plan.action} "
            f"(conf={confidence:.2f}, {duration_ms:.1f}ms)"
        )

        # Log decision
        self._decision_history.append({
            "timestamp": time.time(),
            "intent": intent,
            "action": action_plan.action,
            "confidence": confidence,
            "entities": entities,
            "duration_ms": round(duration_ms, 2),
        })

        # Trim history
        if len(self._decision_history) > DECISION_CONFIG["max_action_history"]:
            self._decision_history = self._decision_history[-DECISION_CONFIG["max_action_history"]:]

        return action_plan

    def _extract_entities(self, query: str, intent: str) -> Dict[str, str]:
        """
        Extract entities from query based on intent context.

        Simple keyword-based entity extraction.
        """
        entities = {}
        if not query:
            return entities

        query_lower = query.lower()

        # APP name extraction
        if intent == "OPEN_APP":
            app_names = [
                "whatsapp", "youtube", "chrome", "telegram", "instagram",
                "gmail", "maps", "camera", "phone", "contacts", "gallery",
                "settings", "calculator", "calendar", "clock", "playstore",
                "spotify", "files", "messages", "twitter", "facebook",
                "linkedin", "netflix", "prime", "hotstar", "zomato",
                "swiggy", "amazon", "flipkart",
            ]
            for app in app_names:
                if app in query_lower:
                    entities["app"] = app
                    break

        # Contact extraction
        elif intent in ("CALL", "MESSAGE"):
            # Try to find a name after "call" or "message"
            words = query_lower.split()
            for i, word in enumerate(words):
                if word in ("call", "message", "text", "phone", "dial"):
                    if i + 1 < len(words):
                        name = " ".join(words[i + 1:])
                        # Remove common filler words
                        for filler in ["karo", "kar", "karna", "please", "pls"]:
                            name = name.replace(filler, "").strip()
                        if name:
                            entities["contact"] = name
                            break

        # Number/quantity extraction
        if any(intent == s for s in ["VOLUME_UP", "VOLUME_DOWN"]):
            numbers = re.findall(r'\d+', query)
            if numbers:
                entities["value"] = numbers[0]

        return entities

    def get_decision_history(self, limit: int = 10) -> List[Dict]:
        """Get recent decision history."""
        return self._decision_history[-limit:]

    def get_confident_decisions(self, threshold: float = 0.8) -> List[Dict]:
        """Get high-confidence decisions for learning."""
        return [
            d for d in self._decision_history
            if d["confidence"] >= threshold
        ]

    def get_stats(self) -> dict:
        """Get decision brain statistics."""
        if not self._decision_history:
            return {"decisions_made": 0}
        
        recent = self._decision_history[-50:]
        avg_confidence = sum(d["confidence"] for d in recent) / len(recent) if recent else 0
        avg_duration = sum(d["duration_ms"] for d in recent) / len(recent) if recent else 0

        intent_counts = {}
        for d in self._decision_history:
            intent_counts[d["intent"]] = intent_counts.get(d["intent"], 0) + 1

        return {
            "decisions_made": len(self._decision_history),
            "avg_confidence": round(avg_confidence, 3),
            "avg_duration_ms": round(avg_duration, 2),
            "intent_distribution": intent_counts,
            "unique_intents": len(intent_counts),
        }
