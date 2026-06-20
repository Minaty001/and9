"""
app/core/reflection.py — Reflection Engine.

Part of JARVIS Cognitive Architecture (Subconscious Brain layer).
Runs at session end or on demand to:
  1. Summarize what was discussed
  2. Extract key insights / facts from the session
  3. Tag emotional arc of the session
  4. Generate a daily review (on request)
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


class ReflectionEngine:
    """Generates session summaries and daily reviews using LLM + memory."""

    def __init__(self, memory):
        self._mem = memory

    def reflect_on_session(self, session_id: int, ask_llm_fn) -> str:
        """Summarize a session using the LLM.

        Args:
            session_id: ID of the session to reflect on.
            ask_llm_fn: Callable(messages) → str  (e.g. brain.ask_llm)

        Returns:
            Summary string.
        """
        episodes = self._mem.get_session_history(session_id)
        if not episodes:
            return "Koi conversation nahi mili is session mein."

        # Build transcript
        transcript_lines = []
        for ep in episodes:
            role = "Tu" if ep["role"] == "user" else "JARVIS"
            transcript_lines.append(f"{role}: {ep['content'][:300]}")
        transcript = "\n".join(transcript_lines[:30])  # cap at 30 turns

        prompt = f"""Yeh ek conversation session ka transcript hai:

{transcript}

Is session ka ek concise summary do (3-5 lines mein, Hinglish mein):
- Kya discuss hua
- Koi important decisions ya facts
- User ka mood / emotional state
- Koi unresolved questions ya next steps"""

        try:
            messages = [{"role": "user", "content": prompt}]
            summary = ask_llm_fn(messages, max_tokens=300) or "Summary generate nahi ho saki."
        except Exception as e:
            logger.warning(f"Reflection LLM call failed: {e}")
            summary = f"Session mein {len(episodes)} exchanges hue."

        # Store summary in session
        try:
            self._mem.end_session(session_id, summary=summary[:500])
        except Exception:
            pass

        return summary

    def daily_review(self, ask_llm_fn) -> str:
        """Generate a daily review of what happened today.

        Pulls episodes from last 24 hours and summarizes them.
        """
        recent = self._mem.get_recent_episodes(limit=50)
        if not recent:
            return "Aaj koi conversation nahi hui boss."

        # Filter last 24h
        cutoff = datetime.utcnow() - timedelta(hours=24)
        today_eps = []
        for ep in recent:
            ts = ep.get("timestamp", "")
            try:
                ep_dt = datetime.fromisoformat(str(ts).replace("Z", ""))
                if ep_dt >= cutoff:
                    today_eps.append(ep)
            except Exception:
                today_eps.append(ep)  # include if can't parse

        if not today_eps:
            return "Aaj koi activity nahi thi boss."

        transcript = "\n".join(
            f"{'Tu' if e['role']=='user' else 'JARVIS'}: {e['content'][:200]}"
            for e in today_eps[:40]
        )

        prompt = f"""Aaj ki JARVIS activity ka summary do (Hinglish mein, friendly tone):

{transcript}

Include karo:
1. Kya kiya aaj saath mein
2. Koi important decisions / facts
3. Pending tasks / goals jo aaj mention hue
4. Kal ke liye suggestions"""

        try:
            messages = [{"role": "user", "content": prompt}]
            review = ask_llm_fn(messages, max_tokens=400) or "Aaj ka review generate nahi ho saka."
        except Exception as e:
            logger.warning(f"Daily review failed: {e}")
            review = f"Aaj {len(today_eps)} conversations hue."

        return review

    def extract_key_facts(self, session_id: int, ask_llm_fn) -> list[dict]:
        """Extract important facts from a session and store them in semantic memory.

        Returns list of extracted facts.
        """
        episodes = self._mem.get_session_history(session_id)
        if not episodes:
            return []

        user_turns = [ep["content"] for ep in episodes if ep["role"] == "user"]
        text = "\n".join(user_turns[:20])

        prompt = f"""Extract important personal facts from this conversation (JSON array):

Text: {text}

Return ONLY a JSON array like:
[
  {{"category": "identity", "key": "name", "value": "Karan"}},
  {{"category": "preference", "key": "favorite_song", "value": "Tum Hi Ho"}}
]

Only return facts about the USER. Return empty array [] if no facts found."""

        try:
            import json
            messages = [{"role": "user", "content": prompt}]
            raw = ask_llm_fn(messages, max_tokens=300) or "[]"
            # Extract JSON from response
            start = raw.find("[")
            end   = raw.rfind("]") + 1
            if start >= 0 and end > start:
                facts = json.loads(raw[start:end])
                for f in facts:
                    if all(k in f for k in ("category", "key", "value")):
                        self._mem.store_fact(f["category"], f["key"], str(f["value"]), confidence=0.85)
                        self._mem.learn_fact(f["key"], str(f["value"]), f["category"])
                return facts
        except Exception as e:
            logger.warning(f"Fact extraction failed: {e}")
        return []
