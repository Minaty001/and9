"""
AND9 — Habit Brain.
Dedicated layer that wraps SubconsciousBrain to analyze daily routines (morning, evening, work)
and generate proactive recommendations.
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from backend.cognition.subconscious.subconscious_brain import SubconsciousBrain

logger = logging.getLogger(__name__)

class HabitBrain:
    """The Habit Brain wraps SubconsciousBrain, categorizes user routines,
    and generates context-aware predictions or proactive commands.
    """

    def __init__(self, subconscious_brain: Optional[SubconsciousBrain] = None):
        self.subconscious = subconscious_brain or SubconsciousBrain()

    def get_routine_suggestion(self) -> Optional[Dict[str, Any]]:
        """Identify if there is an active routine suggestion for the current time.

        E.g., Morning (6 AM - 11 AM), Work (11 AM - 5 PM), Evening (5 PM - 10 PM), Night (10 PM - 6 AM).
        """
        now = datetime.now()
        hour = now.hour
        prediction = self.subconscious.predict_next_action()

        if not prediction:
            return None

        action = prediction["action"]
        suggestion = prediction["suggestion"]
        
        # Categorize routine based on hour
        if 6 <= hour < 11:
            routine = "morning_routine"
            display_routine = "morning routine"
        elif 11 <= hour < 17:
            routine = "work_routine"
            display_routine = "work routine"
        elif 17 <= hour < 22:
            routine = "evening_routine"
            display_routine = "evening routine"
        else:
            routine = "night_routine"
            display_routine = "night routine"

        # Generate a premium localized suggestion
        action_display = action
        if action == "LAUNCH_APP" and prediction.get("app_name"):
            pkg = prediction.get("app_name", "")
            if "." in pkg:
                parts = pkg.split('.')
                action_display = f"open {parts[-2] if len(parts) >= 2 else parts[-1]}"
            else:
                action_display = f"open {pkg}"

        localized_suggestion = f"Aap generally is samay ({display_routine}) '{action_display}' karte hain. Kya main isse open/execute karu? ⚡"

        return {
            "predicted_action": action,
            "app_name": prediction.get("app_name"),
            "confidence": prediction["confidence"],
            "routine_type": routine,
            "suggestion": localized_suggestion,
            "raw_suggestion": suggestion,
            "source": prediction["source"]
        }

    def record_action(self, result: Any, query: str):
        """Record executed action into SubconsciousBrain."""
        self.subconscious.record_action(result, query)
