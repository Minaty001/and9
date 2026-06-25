"""
app/core/proactive.py — Proactive Intelligence Engine.

Generates smart, context-aware suggestions, motivational nudges,
weather/news briefs, and mood-based recommendations WITHOUT being asked.
Designed for Android push-notification style delivery.
"""
import logging
import time
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# ── Suggestion Templates ────────────────────────────────────────

_MORNING_TIPS = [
    "Aaj ka din fresh start karo — ek chhota goal set karo!",
    "Good morning! Kya aaj kuch naya seekhna hai?",
    "Subah ka 5 min journaling aaj ki clarity improve karta hai.",
    "Hydration reminder: Pani pee lo! 💧",
]

_EVENING_TIPS = [
    "Aaj kya achieve kiya? Ek quick daily review karo.",
    "Evening wind-down: Koi relaxing music lagao?",
    "Kal ke liye koi goal set karna hai?",
    "Din ka summary bana lo — yaadaasht badhti hai.",
]

_FOCUS_TIPS = [
    "Pomodoro try karo: 25 min work, 5 min break.",
    "Phone notifications band karo for next 30 min.",
    "Deep work tip: Ek hi task focus karo abhi.",
]

_MOTIVATION = [
    "Har bada kaam chhote steps se bana hai. Chalo!",
    "Tu kar sakta hai — sirf shuru karna hai.",
    "Progress > Perfection. Bas aage badho.",
    "Consistency beats talent, always.",
]

_HEALTH_TIPS = [
    "Pani pee lo! 💧 Hydration = brain power.",
    "5 min stretching break lo — body refresh hogi.",
    "Screen se aankhen hata ke door dekho 20 sec.",
    "Posture check karo! Seedha baitho.",
]


class ProactiveEngine:
    """Generates smart, time-aware suggestions and recommendations."""

    def __init__(self, memory=None):
        self.memory = memory
        self._last_suggestion_ts: float = 0
        self._suggestion_cooldown = 1800  # 30 min between auto suggestions

    def get_time_context(self) -> dict:
        """Get current time context for adaptive behavior."""
        now = datetime.now()
        hour = now.hour
        weekday = now.weekday()  # 0=Mon, 6=Sun
        is_weekend = weekday >= 5

        if 5 <= hour < 12:
            period = "morning"
        elif 12 <= hour < 17:
            period = "afternoon"
        elif 17 <= hour < 21:
            period = "evening"
        else:
            period = "night"

        return {
            "hour": hour,
            "period": period,
            "is_weekend": is_weekend,
            "weekday_name": now.strftime("%A"),
            "date_str": now.strftime("%d %B %Y"),
            "time_str": now.strftime("%I:%M %p"),
        }

    def get_smart_greeting(self, user_profile: dict = None) -> str:
        """Generate a personalized greeting based on time and user profile."""
        ctx = self.get_time_context()
        name = ""
        if user_profile:
            # Flatten nested profile
            for cat_vals in user_profile.values():
                if isinstance(cat_vals, dict):
                    name = cat_vals.get("name", "")
                    if name:
                        break
                elif isinstance(cat_vals, str):
                    pass

        period = ctx["period"]
        greetings = {
            "morning": f"Good morning{' ' + name if name else ''}! ☀️ Aaj ka din kaisa rahega?",
            "afternoon": f"Hey{' ' + name if name else ''}! 🌤 Afternoon session mein kya plan hai?",
            "evening": f"Evening{' ' + name if name else ''}! 🌙 Din kaisa gaya?",
            "night": f"Late night session{' ' + name if name else ''}? 🌙 Kya chal raha hai?",
        }
        return greetings.get(period, f"Hey{' ' + name if name else ''}! Kya haal hai?")

    def get_proactive_suggestion(self, emotion: str = "neutral",
                                  topic: str = "general") -> Optional[str]:
        """Return a context-aware suggestion if cooldown has passed."""
        now = time.time()
        if now - self._last_suggestion_ts < self._suggestion_cooldown:
            return None

        self._last_suggestion_ts = now
        ctx = self.get_time_context()
        import random

        # Mood-based suggestions
        if emotion in ("sad", "anxious", "angry"):
            tips = _MOTIVATION + _HEALTH_TIPS
        elif topic in ("coding/programming", "work", "project"):
            tips = _FOCUS_TIPS
        elif ctx["period"] == "morning":
            tips = _MORNING_TIPS
        elif ctx["period"] == "evening":
            tips = _EVENING_TIPS
        else:
            tips = _HEALTH_TIPS + _MOTIVATION

        return random.choice(tips)

    def get_daily_briefing(self) -> dict:
        """Generate a morning briefing with time, goals summary, and a tip."""
        ctx = self.get_time_context()
        import random
        tip = random.choice(_MORNING_TIPS + _MOTIVATION)

        return {
            "time": ctx["time_str"],
            "date": ctx["date_str"],
            "weekday": ctx["weekday_name"],
            "is_weekend": ctx["is_weekend"],
            "tip": tip,
            "greeting": self.get_smart_greeting(),
        }

    def analyze_productivity_streak(self, episodes: list) -> dict:
        """Analyze conversation frequency to estimate productivity streak."""
        if not episodes:
            return {"streak_days": 0, "total_sessions": 0, "message": "Ab shuru karo!"}

        total = len(episodes)
        # Estimate daily usage from episode timestamps
        dates = set()
        for ep in episodes:
            ts = ep.get("timestamp", "")
            if ts:
                try:
                    dt = datetime.fromisoformat(str(ts)[:10])
                    dates.add(dt.date())
                except Exception:
                    logger.debug("Failed to parse timestamp: %s", ts)

        streak = len(dates)
        msg = (
            f"🔥 {streak} din ka streak! Zabardast consistency!"
            if streak >= 3
            else "Roz use karo — streak banao!"
        )
        return {
            "streak_days": streak,
            "total_sessions": total,
            "message": msg,
        }

    def get_android_quick_actions(self, user_profile: dict = None) -> list:
        """Return context-aware quick action chips for Android UI."""
        ctx = self.get_time_context()
        actions = []

        if ctx["period"] == "morning":
            actions += [
                {"label": "📋 Daily Briefing", "msg": "Aaj ka daily review do"},
                {"label": "🎯 Set Goal", "msg": "Mera goal list batao"},
                {"label": "📰 News", "msg": "Today's top news"},
            ]
        elif ctx["period"] == "evening":
            actions += [
                {"label": "🌙 Evening Review", "msg": "Din ka summary bana do"},
                {"label": "🎵 Chill Music", "msg": "Koi relaxing song laga do"},
                {"label": "📝 Journal", "msg": "Aaj ki highlights note karo"},
            ]
        else:
            actions += [
                {"label": "🔔 Reminders", "msg": "Upcoming reminders batao"},
                {"label": "🎵 Music", "msg": "Koi achha song laga do"},
                {"label": "💡 Focus Tip", "msg": "Focus improve karne ka tip do"},
            ]

        # Always include these
        actions += [
            {"label": "🧠 Memory Recall", "msg": "Humne kya baat ki thi"},
            {"label": "🌐 Search", "msg": "Search "},
        ]
        return actions[:6]  # Max 6 chips for mobile
