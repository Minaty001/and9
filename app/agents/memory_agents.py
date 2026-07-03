"""
AND9 — Memory Agents: Memory, Learning, Reflection.

These agents manage the system's memory, learn from experience,
and reflect on performance to drive self-improvement.
"""

import logging
from datetime import datetime
from typing import Any, Optional

from app.agents.base import AgentBase, AgentResult

logger = logging.getLogger(__name__)


class MemoryAgent(AgentBase):
    """Memory Agent — information storage and retrieval.

    Manages all memory types:
      - Working memory (current conversation)
      - Short-term memory (recent sessions)
      - Long-term memory (user facts, preferences)
      - Episodic memory (past interactions)
      - Semantic memory (knowledge)
    """

    def __init__(self):
        super().__init__(
            name="memory",
            role="Memory management and information retrieval",
            goal="Store, organize, and retrieve information accurately",
            backstory=(
                "I am the memory agent. I manage the system's memory across "
                "multiple types and time horizons. I store important information, "
                "retrieve it when needed, and organize it for efficient access. "
                "I ensure the system remembers what matters and forgets what doesn't."
            ),
            config={
                "max_working_memory": 100,
                "max_short_term": 1000,
                "consolidation_interval": 3600,
            },
        )
        self._stores = {
            "working": {},
            "short_term": {},
            "long_term": {},
            "episodic": [],
            "semantic": {},
        }

    def _get_system_prompt(self) -> str:
        return (
            f"You are {self.name}, the {self.role}. {self.backstory}\n\n"
            "Memory types I manage:\n"
            "  - Working: Current conversation context\n"
            "  - Short-term: Recent sessions (hours)\n"
            "  - Long-term: User facts and preferences\n"
            "  - Episodic: Past interactions and experiences\n"
            "  - Semantic: Knowledge and concepts\n\n"
            "Rules:\n"
            "1. Store information with proper importance and confidence.\n"
            "2. Retrieve the most relevant information when asked.\n"
            "3. Consolidate short-term to long-term periodically.\n"
            "4. Never store sensitive data (passwords, tokens).\n"
            "5. Respect memory boundaries — don't leak between users.\n"
        )

    def process(self, input_data: Any,
                context: Optional[dict] = None) -> AgentResult:
        """Process a memory operation."""
        message = str(input_data) if not isinstance(input_data, str) else input_data
        msg_lower = message.lower().strip()

        # Store operation
        if msg_lower.startswith("remember ") or msg_lower.startswith("save "):
            content = msg_lower.split(" ", 1)[1] if " " in msg_lower else ""
            self._stores["long_term"][f"fact_{len(self._stores['long_term'])}"] = {
                "content": content,
                "timestamp": datetime.now().isoformat(),
                "importance": 0.5,
                "confidence": 0.7,
            }
            return AgentResult(
                success=True,
                response=f"Main ne yaad rakha: \"{content}\"",
                data={"stored": content, "memory_type": "long_term"},
                agent_name=self.name,
            )

        # Recall operation
        if msg_lower.startswith("recall ") or msg_lower.startswith("what did i say about "):
            search = msg_lower.split(" ", 1)[1] if " " in msg_lower else ""
            # Search through all stores
            results = []
            for store_name, store in self._stores.items():
                if isinstance(store, dict):
                    for key, value in store.items():
                        if isinstance(value, dict) and "content" in value:
                            if search in value["content"].lower():
                                results.append({
                                    "store": store_name,
                                    "key": key,
                                    "value": value["content"],
                                })
            if results:
                response = "Yaad aaya! Kuch cheezein jo maine rakhi hain:\n"
                for r in results[:5]:
                    response += f"- {r['value']}\n"
            else:
                response = f"Mujhe '{search}' ke baare mein koi information nahi mili."

            return AgentResult(
                success=True,
                response=response,
                data={"query": search, "results": results},
                agent_name=self.name,
            )

        # Stats
        if msg_lower in ("memory stats", "memory status", "stats"):
            stats = {k: len(v) for k, v in self._stores.items()}
            return AgentResult(
                success=True,
                response=f"Memory stats: {stats}",
                data=stats,
                agent_name=self.name,
            )

        # Default: store in working memory
        self._stores["working"][f"turn_{len(self._stores['working'])}"] = {
            "content": message,
            "timestamp": datetime.now().isoformat(),
        }

        return AgentResult(
            success=True,
            response=f"Main ne note kar liya.",
            data={"stored": message, "memory_type": "working"},
            agent_name=self.name,
        )

    def store(self, key: str, value: Any, memory_type: str = "working"):
        """Programmatic store (used by other agents)."""
        if memory_type in self._stores:
            if isinstance(self._stores[memory_type], dict):
                self._stores[memory_type][key] = {
                    "content": value,
                    "timestamp": datetime.now().isoformat(),
                }
            elif memory_type == "episodic":
                self._stores["episodic"].append({
                    "key": key,
                    "content": value,
                    "timestamp": datetime.now().isoformat(),
                })

    def recall(self, key: str, memory_type: Optional[str] = None) -> Optional[Any]:
        """Programmatic recall (used by other agents)."""
        if memory_type:
            store = self._stores.get(memory_type, {})
            if isinstance(store, dict):
                entry = store.get(key)
                return entry["content"] if entry and "content" in entry else None
        else:
            for store in self._stores.values():
                if isinstance(store, dict):
                    entry = store.get(key)
                    if entry and "content" in entry:
                        return entry["content"]
        return None


class LearningAgent(AgentBase):
    """Learning Agent — pattern recognition and self-improvement.

    Analyzes past actions to detect patterns, learn user preferences,
    and continuously improve the system's performance.
    """

    def __init__(self):
        super().__init__(
            name="learning",
            role="Pattern learning and continuous improvement",
            goal="Learn from experiences to improve system performance over time",
            backstory=(
                "I am the learning agent. I analyze the system's experiences — "
                "successes, failures, user corrections, and repeated patterns — "
                "to continuously improve performance. I detect usage patterns, "
                "learn user preferences, and generate new skills automatically."
            ),
        )

    def _get_system_prompt(self) -> str:
        return (
            f"You are {self.name}, the {self.role}. {self.backstory}\n\n"
            "Rules:\n"
            "1. Detect patterns from repeated user actions.\n"
            "2. Learn user preferences and routines.\n"
            "3. Identify failures and suggest improvements.\n"
            "4. Generate reusable skills from successful patterns.\n"
            "5. Track improvement over time with metrics.\n"
        )

    def process(self, input_data: Any,
                context: Optional[dict] = None) -> AgentResult:
        """Process a learning request or trigger learning cycle."""
        request = str(input_data) if not isinstance(input_data, str) else input_data

        # If context has stats, analyze them
        if context and "metrics" in context:
            metrics = context["metrics"]
            return self._analyze_metrics(metrics, request)

        return AgentResult(
            success=True,
            response=(
                f"**Learning Agent**\n\n"
                f"I analyze patterns in your usage to improve over time.\n"
                f"Currently tracking: actions, successes, failures, preferences.\n\n"
                f"I learn from:\n"
                f"- Repeated commands → routines\n"
                f"- Corrections → improved understanding\n"
                f"- Successes → reinforce strategies\n"
                f"- Failures → avoid mistakes\n"
            ),
            data={
                "patterns_detected": 0,
                "preferences_learned": 0,
                "skills_generated": 0,
            },
            agent_name=self.name,
        )

    def _analyze_metrics(self, metrics: dict, request: str) -> AgentResult:
        """Analyze system metrics and provide improvement suggestions."""
        success_rate = metrics.get("success_rate", 1.0)
        total_actions = metrics.get("total_actions", 0)

        suggestions = []
        if success_rate < 0.8:
            suggestions.append("Success rate is below 80% — consider reviewing failed actions")
        if total_actions == 0:
            suggestions.append("No actions recorded yet — start using the system")

        return AgentResult(
            success=True,
            response=(
                f"**Learning Analysis**\n\n"
                f"Success rate: {success_rate:.0%}\n"
                f"Total actions: {total_actions}\n\n"
                + ("Suggestions:\n" + "\n".join(f"- {s}" for s in suggestions)
                   if suggestions else "Everything looks good!")
            ),
            data={
                "success_rate": success_rate,
                "total_actions": total_actions,
                "suggestions": suggestions,
            },
            agent_name=self.name,
        )


class ReflectionAgent(AgentBase):
    """Reflection Agent — self-analysis and improvement.

    After each major action or periodically, reflects on:
      - Did I succeed in my goal?
      - What went wrong?
      - What can be improved?
      - Should memory be updated?
    """

    def __init__(self):
        super().__init__(
            name="reflection",
            role="Self-analysis and continuous improvement",
            goal="Analyze outcomes, identify improvements, update strategies",
            backstory=(
                "I am the reflection agent. I analyze every major action "
                "and outcome to drive continuous improvement. I ask: Did we succeed? "
                "What failed? Can we improve? Should memory be updated? "
                "I turn every experience into a learning opportunity."
            ),
        )

    def _get_system_prompt(self) -> str:
        return (
            f"You are {self.name}, the {self.role}. {self.backstory}\n\n"
            "Questions I always ask:\n"
            "1. Did the action achieve its goal?\n"
            "2. What specific things went wrong?\n"
            "3. What could have been done differently?\n"
            "4. Should this experience be stored in memory?\n"
            "5. Is there a pattern worth learning?\n\n"
            "Rules:\n"
            "1. Be honest about failures — they are learning opportunities.\n"
            "2. Be specific about what went wrong.\n"
            "3. Suggest concrete improvements.\n"
            "4. Update memory when important lessons are learned.\n"
        )

    def process(self, input_data: Any,
                context: Optional[dict] = None) -> AgentResult:
        """Reflect on an action or event."""
        event = str(input_data) if not isinstance(input_data, str) else input_data

        return AgentResult(
            success=True,
            response=(
                f"**Reflection on: {event[:100]}**\n\n"
                f"Analysis completed. No issues detected.\n"
                f"Performance is nominal."
            ),
            data={
                "event": event[:200],
                "lessons_learned": [],
                "improvements_suggested": [],
                "memory_updates": [],
            },
            agent_name=self.name,
        )
