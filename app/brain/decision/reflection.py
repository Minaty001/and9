"""
app/core/reflection.py — Reflection Engine.

Part of JARVIS Cognitive Architecture (Subconscious Brain layer).
Runs at session end or on demand to:
  1. Summarize what was discussed (only from actual data)
  2. Extract key insights / facts from the session (regex-only, no LLM)
  3. Tag emotional arc of the session
  4. Generate a daily review (on request, only from actual data)

Constitution V3:
   Rule 5 — No LLM-inferred facts stored as memory
   Rule 6 — Only store what data explicitly contains
   Rule 8 — Source tracking for all memory writes
"""
import logging
import re
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


class ReflectionEngine:
    """Generates session summaries and daily reviews using LLM + memory."""

    def __init__(self, memory):
        """Initialise the reflection engine with a reference to the memory system.

        Args:
            memory: The parent Memory instance used to fetch session history.
        """
        self._mem = memory

    def reflect_on_session(self, session_id: int, _ask_llm_fn=None) -> str:
        """Summarize a session using extractive transcript analysis (no LLM).

        Args:
            session_id: ID of the session to reflect on.
            _ask_llm_fn: Deprecated, kept for backward compatibility only.

        Returns:
            Summary string, faithful to the actual transcript.
        """
        episodes = self._mem.get_session_history(session_id)
        if not episodes:
            return "Koi conversation nahi mili is session mein."

        # Build simple extractive summary
        user_topics = []
        assistant_responses = []
        for ep in episodes:
            if ep["role"] == "user":
                user_topics.append(ep['content'][:150])
            else:
                assistant_responses.append(ep['content'][:150])

        num_turns = len(episodes)
        summary_parts = [f"Session mein {num_turns} exchanges hue."]
        if user_topics:
            summary_parts.append(f"User ne baat ki: {user_topics[0][:100]}...")
        if assistant_responses:
            summary_parts.append(f"JARVIS ne jawab diya.")

        summary = " | ".join(summary_parts)

        # Store summary in session
        try:
            self._mem.end_session(session_id, summary=summary[:500])
        except Exception as e:
            logger.warning("Failed to end session: %s", e)

        return summary

    def daily_review(self, _ask_llm_fn=None) -> str:
        """Generate a daily review of what happened today (no LLM).

        Pulls episodes from last 24 hours and returns a simple count-based summary.

        Returns:
            Review string with the number of conversations and basic stats.
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

        user_count = sum(1 for e in today_eps if e.get("role") == "user")
        assistant_count = sum(1 for e in today_eps if e.get("role") == "assistant")
        topics = set(e.get("topic", "") for e in today_eps if e.get("topic"))

        review = f"Aaj {len(today_eps)} conversations hue — {user_count} user, {assistant_count} JARVIS."
        if topics:
            topic_str = ", ".join(t for t in topics if t)
            if topic_str:
                review += f" Topics: {topic_str}"
        return review

    def extract_key_facts(self, session_id: int) -> list[dict]:
        """Extract important facts from a session using regex pattern matching only.

        Per Rule 5/6: NEVER use LLM for fact extraction. Only direct regex
        patterns from understanding.py are allowed.

        Returns list of extracted facts with confidence=0.3 and source=regex_extraction.
        """
        episodes = self._mem.get_session_history(session_id)
        if not episodes:
            return []

        user_turns = [ep.get("content", "") for ep in episodes if ep.get("role") == "user"]
        text = "\n".join(user_turns)

        facts = []

        # Pattern: mera naam X hai / my name is X / main X hoon / I am X
        name_match = re.search(
            r'(?:mera naam |my name is |i am |i\'m |main |call me )(\w+(?:\s+\w+)?)',
            text, re.IGNORECASE
        )
        if name_match:
            name = name_match.group(1).strip().capitalize()
            if name.lower() not in ("jarvis", "assistant", "there", "here", "ready"):
                facts.append({
                    "category": "identity",
                    "key": "name",
                    "value": name,
                    "source": "regex_extraction",
                    "confidence": 0.3,
                })

        # Pattern: main X mein rehta hoon / i live in X / from X
        location_match = re.search(
            r'(?:main |i )(?:\w+ )?(?:mein rehta|live in|from |rehta|rehti)(?:\w+ )?(.+?)(?:\.|,|$| hoon)',
            text, re.IGNORECASE
        )
        if location_match:
            loc = location_match.group(1).strip().capitalize()
            if len(loc) > 2 and loc.lower() not in ("here", "there", "somewhere"):
                facts.append({
                    "category": "location",
                    "key": "location",
                    "value": loc,
                    "source": "regex_extraction",
                    "confidence": 0.3,
                })

        # Pattern: mujhe X pasand hai / i like X / i love X
        preference_match = re.search(
            r'(?:(?:mujhe|main) (.+?) pasand|i (?:like|love|prefer) (.+?))(?:\.|,|$| hai)',
            text, re.IGNORECASE
        )
        if preference_match:
            pref = preference_match.group(1) or preference_match.group(2)
            if pref:
                facts.append({
                    "category": "preference",
                    "key": "preference",
                    "value": pref.strip(),
                    "source": "regex_extraction",
                    "confidence": 0.3,
                })

        # Pattern: profession detection
        prof_match = re.search(
            r'(?:i am a |main ek |i work as |my job is |profession |main |mein )(\w+(?:\s+\w+)?) (?:hoon|hun|hū)',
            text, re.IGNORECASE
        )
        if prof_match:
            prof = prof_match.group(1).strip()
            if prof.lower() not in ("there", "here", "ready", "fine", "good"):
                facts.append({
                    "category": "profession",
                    "key": "profession",
                    "value": prof,
                    "source": "regex_extraction",
                    "confidence": 0.3,
                })

        # Store extracted facts (regex-based, confidence 0.3)
        for f in facts:
            try:
                self._mem.store_fact(
                    category=f["category"],
                    key=f["key"],
                    value=f["value"],
                    confidence=f["confidence"],
                    source=f["source"],
                    verified=False,
                )
                self._mem.learn_fact(
                    key=f["key"],
                    value=f["value"],
                    fact_type=f["category"],
                    priority=1,
                    source=f["source"],
                    confidence=f["confidence"],
                    verified=False,
                )
                logger.info(f"Regex-extracted fact: {f['category']}:{f['key']}={f['value']}")
            except Exception as e:
                logger.warning(f"Failed to store extracted fact {f['key']}: {e}")

        return facts
