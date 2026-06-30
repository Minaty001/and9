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
        self._mem = memory

    def reflect_on_session(self, session_id: int, ask_llm_fn) -> str:
        """Summarize a session using the LLM.

        Args:
            session_id: ID of the session to reflect on.
            ask_llm_fn: Callable(messages) → str  (e.g. brain.ask_llm)

        Returns:
            Summary string, faithful to the actual transcript.
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
- Sirf wohi likho jo transcript mein hai
- Kya discuss hua
- Koi important decisions ya facts (sirf transcript se)
- User ka mood / emotional state
- Koi unresolved questions ya next steps

IMPORTANT: Sirf transcript mein di gayi information ka reference karo.
Kuch bhi invent mat karo. Agar kuch nahi hai toh mat likho."""

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

        Only from chat_history, activity_logs, episodic_memory, journal_entries.
        If no activity → 'No meaningful activity recorded.'

        Pulls episodes from last 24 hours and summarizes them faithfully.
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
1. Kya discuss hua (sirf transcript se)
2. Koi important decisions / facts (sirf jo transcript mein clearly hain)
3. Pending tasks / goals jo aaj mention hue
4. Kal ke liye suggestions

Data-faithfulness rules:
- ONLY include what is explicitly in the transcript above
- Agar koi section mein kuch nahi hai toh skip karo
- Kabhi bhi activities ya facts invent mat karo
- Sirf actual conversations ka reference do"""

        try:
            messages = [{"role": "user", "content": prompt}]
            review = ask_llm_fn(messages, max_tokens=400) or "Aaj ka review generate nahi ho saka."
        except Exception as e:
            logger.warning(f"Daily review failed: {e}")
            review = f"Aaj {len(today_eps)} conversations hue."

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
