"""
AND9 — Core Agents: Executive, Conversation, Planning.

These are the highest-level agents that coordinate the system,
handle natural conversation, and decompose complex tasks.
"""

import logging
from typing import TYPE_CHECKING, Any, Optional

from app.agents.base import AgentBase, AgentResult

if TYPE_CHECKING:
    from app.orchestrator import AgentOrchestrator
    from app.agents.base import AgentRegistry

logger = logging.getLogger(__name__)


class ExecutiveAgent(AgentBase):
    """Executive Agent — the CEO of the multi-agent system.

    Responsibilities:
      - Receive and analyze user goals
      - Decompose complex requests into subtasks
      - Route subtasks to appropriate agents
      - Merge results from multiple agents
      - Validate outputs and retry failures
      - Return final answer to the user

    This is the primary entry point for all non-trivial tasks.
    """

    def __init__(self):
        super().__init__(
            name="executive",
            role="Chief Executive Agent — orchestrates the agent swarm",
            goal="Decompose user requests, delegate to specialists, verify and merge results",
            backstory=(
                "I am the executive agent, the CEO of the AND9 multi-agent system. "
                "My job is to understand the user's goal, break it into clear subtasks, "
                "assign each to the right specialist agent, verify their work, and present "
                "a coherent final result. I handle delegation, conflict resolution, and "
                "quality control."
            ),
            config={
                "max_parallel_tasks": 5,
                "retry_attempts": 2,
                "require_verification": True,
            },
        )
        # Will be set by the registry/orchestrator after registration
        self._registry = None
        self._orchestrator = None

    def set_registry(self, registry: 'Any') -> None:
        """Set reference to the agent registry for delegation."""
        self._registry = registry

    def set_orchestrator(self, orchestrator: Any) -> None:
        """Set reference to the orchestrator for complex tasks."""
        self._orchestrator = orchestrator

    def _get_system_prompt(self) -> str:
        return (
            f"You are {self.name}, the {self.role}. {self.backstory}\n\n"
            f"Your goal: {self.goal}\n\n"
            "Rules:\n"
            "1. Always analyze the user's request before acting.\n"
            "2. Break complex tasks into clear, independent subtasks.\n"
            "3. Delegate each subtask to the most qualified agent.\n"
            "4. Never fabricate results — use available agents.\n"
            "5. If delegation fails, provide a clear fallback response.\n"
            "6. Merge results from multiple agents coherently.\n"
            "7. When in doubt, ask clarifying questions.\n"
        )

    def process(self, input_data: Any,
                context: Optional[dict] = None) -> AgentResult:
        """Process a user request by orchestrating the agent swarm.

        Routes simple requests to the appropriate specialist agent.
        For complex requests involving multiple domains, delegates
        to the orchestrator for full pipeline execution (decompose →
        parallel execute → validate → retry → merge).
        """
        task = str(input_data) if not isinstance(input_data, str) else input_data
        task_lower = task.lower().strip()

        # If no registry, handle as general conversation
        if not self._registry:
            return AgentResult(
                success=True,
                response=(
                    f"I understand you want to: {task}. "
                    f"I'll help you with that once my agent team is connected."
                ),
                agent_name=self.name,
                needs_followup=True,
                followup_agent="conversation",
        )

        # If orchestrator is available, use it for all non-trivial tasks
        if self._orchestrator:
            # Simple single-keyword tasks route directly for speed
            simple_routes = {
                "code": "coding",
                "write": "coding",
                "program": "coding",
                "debug": "debug",
                "fix": "debug",
                "research": "research",
                "search": "research",
                "remember": "memory",
                "plan": "planning",
                "schedule": "scheduler",
                "automate": "automation",
            }
            keywords_found = [k for k in simple_routes if k in task_lower]
            is_simple = len(keywords_found) <= 1

            if is_simple and keywords_found:
                agent_name = simple_routes[keywords_found[0]]
                if agent_name in self._registry.agents:
                    logger.info("Executive fast-path '%s' -> '%s'",
                                task[:40], agent_name)
                    return self._registry.delegate(agent_name, task, context)

            # Compound/complex → orchestrator
            logger.info("Executive delegating to orchestrator: %s", task[:60])
            return self._orchestrator.run(task, context)

        # Fallback: no orchestrator — route directly for simple tasks
        simple_routes = {
            "code": "coding",
            "write": "coding",
            "program": "coding",
            "debug": "debug",
            "fix": "debug",
            "research": "research",
            "search": "research",
            "remember": "memory",
            "plan": "planning",
            "schedule": "scheduler",
            "automate": "automation",
        }

        for keyword, agent_name in simple_routes.items():
            if keyword in task_lower and agent_name in self._registry.agents:
                logger.info("Executive routing '%s' -> '%s' (no orchestrator)",
                            task[:40], agent_name)
                return self._registry.delegate(agent_name, task, context)

        # Default: delegate to conversation agent for general chat
        if "conversation" in self._registry.agents:
            return self._registry.delegate("conversation", task, context)

        return AgentResult(
            success=True,
            response=task,
            agent_name=self.name,
        )


class ConversationAgent(AgentBase):
    """Conversation Agent — natural dialogue and general chat.

    Handles open-ended conversation, chitchat, and natural language
    understanding. This is the default agent for general chat when
    no specific intent is detected.
    """

    def __init__(self):
        super().__init__(
            name="conversation",
            role="Natural conversation and dialogue",
            goal="Engage in natural, context-aware conversation with the user",
            backstory=(
                "I am the conversation agent. I handle general dialogue, "
                "chitchat, and natural conversation with the user. I maintain "
                "context across turns and provide friendly, helpful responses. "
                "When the user needs a specialist, I route them appropriately."
            ),
        )

    def _get_system_prompt(self) -> str:
        return (
            f"You are {self.name}, the {self.role}. {self.backstory}\n\n"
            "Rules:\n"
            "1. Be helpful, friendly, and natural.\n"
            "2. Keep responses concise and relevant.\n"
            "3. Remember conversation context.\n"
            "4. If the user needs a specialist, suggest the right agent.\n"
            "5. Never pretend to execute actions — route to the correct agent.\n"
        )

    def process(self, input_data: Any,
                context: Optional[dict] = None) -> AgentResult:
        """Process a conversational input."""
        message = str(input_data) if not isinstance(input_data, str) else input_data

        # Update memory with the conversation
        self.memory.remember("last_user_message", message, ttl=600)

        # Build contextual response
        if context and "user_name" in context:
            greeting = f"Hey {context['user_name']}! "
        else:
            greeting = ""

        return AgentResult(
            success=True,
            response=f"{greeting}Main sun raha hoon. Aapne kaha: \"{message}\"",
            agent_name=self.name,
            data={"message": message},
            needs_followup=True,
            followup_agent="executive",
        )


class PlanningAgent(AgentBase):
    """Planning Agent — task decomposition and execution planning.

    Analyzes complex user requests and produces structured plans
    with milestones, dependencies, and resource estimates.
    """

    def __init__(self):
        super().__init__(
            name="planning",
            role="Task decomposition and execution planning",
            goal="Break complex tasks into actionable plans with milestones and dependencies",
            backstory=(
                "I am the planning agent. I analyze complex user requests and "
                "produce structured execution plans. I identify milestones, "
                "dependencies, resource requirements, and potential risks. "
                "My plans are actionable, realistic, and ordered for maximum efficiency."
            ),
            config={
                "max_milestones": 10,
                "include_risks": True,
                "estimate_effort": True,
            },
        )

    def _get_system_prompt(self) -> str:
        return (
            f"You are {self.name}, the {self.role}. {self.backstory}\n\n"
            "Rules:\n"
            "1. Always produce structured plans with clear steps.\n"
            "2. Identify dependencies between steps.\n"
            "3. Flag risks and suggest mitigations.\n"
            "4. Estimate effort where possible.\n"
            "5. Plans must be actionable by other agents.\n"
        )

    def process(self, input_data: Any,
                context: Optional[dict] = None) -> AgentResult:
        """Create a plan for a given task."""
        task = str(input_data) if not isinstance(input_data, str) else input_data

        # Simple plan generation logic
        lines = task.strip().split("\n")
        main_goal = lines[0] if lines else task

        plan = {
            "goal": main_goal,
            "milestones": [
                {"step": 1, "action": f"Analyze requirements for: {main_goal}",
                 "effort": "medium"},
                {"step": 2, "action": "Decompose into subtasks",
                 "effort": "medium", "depends_on": [1]},
                {"step": 3, "action": "Assign subtasks to specialist agents",
                 "effort": "low", "depends_on": [2]},
                {"step": 4, "action": "Execute and verify each subtask",
                 "effort": "high", "depends_on": [3]},
                {"step": 5, "action": "Merge results and present final output",
                 "effort": "low", "depends_on": [4]},
            ],
            "risks": [
                "Complex tasks may require clarification",
                "Some subtasks may depend on unavailable tools",
            ],
            "estimated_steps": 5,
        }

        plan_text = (
            f"**Plan for: {main_goal}**\n\n"
            f"Total steps: {plan['estimated_steps']}\n\n"
            "Steps:\n"
        )
        for m in plan["milestones"]:
            deps = f" (after step {', '.join(str(d) for d in m.get('depends_on', []))})" if m.get("depends_on") else ""
            plan_text += f"  {m['step']}. {m['action']} [{m['effort']}]{deps}\n"

        if plan.get("risks"):
            plan_text += "\nRisks:\n"
            for r in plan["risks"]:
                plan_text += f"  ⚠ {r}\n"

        return AgentResult(
            success=True,
            response=plan_text,
            data=plan,
            agent_name=self.name,
        )
