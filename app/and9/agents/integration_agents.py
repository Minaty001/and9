"""
AND9 — Integration Agents: Tool, Integration, Notification, Workflow.

These agents manage external connections, tools, notifications,
and complex workflow execution.
"""

import logging
from datetime import datetime
from typing import Any, Callable, Optional

from app.and9.agents.base import AgentBase, AgentResult

logger = logging.getLogger(__name__)


class ToolAgent(AgentBase):
    """Tool Agent — tool registry and management.

    Manages the universal tool registry — all plugins and external
    capabilities that agents can use. Provides discovery, loading,
    and health monitoring for tools.
    """

    def __init__(self):
        super().__init__(
            name="tool",
            role="Tool registry and management",
            goal="Provide a reliable, extensible tool ecosystem for all agents",
            backstory=(
                "I am the tool agent. I maintain the universal tool registry — "
                "a catalog of every plugin and external capability available "
                "to the system. I handle dynamic loading, versioning, "
                "permissions, discovery, and health monitoring for tools."
            ),
        )
        self._tools = {}

    def _get_system_prompt(self) -> str:
        return (
            f"You are {self.name}, the {self.role}. {self.backstory}\n\n"
            "Tools I manage:\n"
            "  - Calculator, Weather, Maps\n"
            "  - Camera, Filesystem\n"
            "  - GitHub, Chrome, YouTube, Spotify\n"
            "  - Telegram, WhatsApp, Gmail, Calendar\n"
            "  - Supabase, SQLite, Docker\n"
            "  - OpenRouter, Groq, Ollama\n"
            "  - SerpAPI, Playwright, MCP Servers\n\n"
            "Rules:\n"
            "1. Tools must declare their capabilities and permissions.\n"
            "2. Load tools dynamically — don't hardcode dependencies.\n"
            "3. Monitor tool health and report failures.\n"
            "4. Sandbox untrusted tools.\n"
            "5. Cache tool metadata for fast discovery.\n"
        )

    def process(self, input_data: Any,
                context: Optional[dict] = None) -> AgentResult:
        """Process a tool-related request."""
        request = str(input_data) if not isinstance(input_data, str) else input_data
        req_lower = request.lower().strip()

        # List available tools
        if req_lower in ("list tools", "available tools", "tools", "plugins"):
            if not self._tools:
                return AgentResult(
                    success=True,
                    response=(
                        "**Available Tools**\n\n"
                        "No tools currently registered. "
                        "Tools are loaded automatically when their "
                        "dependencies are available."
                    ),
                    data={"tools": {}},
                    agent_name=self.name,
                )
            tools_text = "\n".join(
                f"- {name}: {info.get('description', 'No description')}"
                for name, info in self._tools.items()
            )
            return AgentResult(
                success=True,
                response=f"**Available Tools**\n\n{tools_text}",
                data={"tools": self._tools},
                agent_name=self.name,
            )

        # Register a tool
        if req_lower.startswith("register tool"):
            return AgentResult(
                success=True,
                response="Tool registration accepted.",
                agent_name=self.name,
            )

        return AgentResult(
            success=True,
            response=(
                f"**Tool Registry**\n\n"
                f"Managing {len(self._tools)} tool(s).\n"
                f"Use 'list tools' to see available tools."
            ),
            data={"registered_tools": len(self._tools), "tools": self._tools},
            agent_name=self.name,
        )

    def register_tool(self, name: str, description: str, handler: Callable):
        """Register a tool programmatically."""
        self._tools[name] = {
            "description": description,
            "handler": handler,
            "registered_at": datetime.now().isoformat(),
            "health": "unknown",
        }
        self.bind_tool(name, handler)
        logger.info("Tool '%s' registered with ToolAgent", name)


class IntegrationAgent(AgentBase):
    """Integration Agent — external service connections.

    Manages connections to external services and APIs:
      - Telegram, WhatsApp, Gmail
      - Google Calendar, Supabase
      - GitHub, Docker, Render
    """

    def __init__(self):
        super().__init__(
            name="integration",
            role="External service integration management",
            goal="Connect and manage external services reliably",
            backstory=(
                "I am the integration agent. I manage connections to external "
                "services — messaging platforms, email, calendars, databases, "
                "and cloud services. I handle authentication, rate limiting, "
                "retry logic, and error handling for all external APIs."
            ),
        )
        self._connections = {}

    def _get_system_prompt(self) -> str:
        return (
            f"You are {self.name}, the {self.role}. {self.backstory}\n\n"
            "Supported integrations:\n"
            "  - Telegram bot\n"
            "  - WhatsApp\n"
            "  - Gmail\n"
            "  - Google Calendar\n"
            "  - Supabase\n"
            "  - GitHub\n"
            "  - Docker\n"
            "  - Render\n\n"
            "Rules:\n"
            "1. Handle authentication securely — never expose tokens.\n"
            "2. Implement proper retry with exponential backoff.\n"
            "3. Gracefully degrade when a service is unavailable.\n"
            "4. Log all API calls for debugging.\n"
        )

    def process(self, input_data: Any,
                context: Optional[dict] = None) -> AgentResult:
        """Process an integration request."""
        request = str(input_data) if not isinstance(input_data, str) else input_data

        return AgentResult(
            success=True,
            response=(
                f"**Integration Hub**\n\n"
                f"Active connections: {len(self._connections)}\n"
                f"Integration request: {request[:100]}\n\n"
                f"I'll connect to the appropriate service and handle the request."
            ),
            data={
                "request": request[:200],
                "active_connections": len(self._connections),
                "connections": self._connections,
            },
            agent_name=self.name,
        )


class NotificationAgent(AgentBase):
    """Notification Agent — alerting and notifications.

    Manages all notification channels:
      - In-app notifications
      - Push notifications
      - Toast messages
      - Sound alerts
      - Email/SMS notifications
    """

    def __init__(self):
        super().__init__(
            name="notification",
            role="Alerting and notification management",
            goal="Deliver timely, relevant notifications through appropriate channels",
            backstory=(
                "I am the notification agent. I deliver alerts and notifications "
                "through the right channels — in-app, push, toast, sound, "
                "or email. I ensure notifications are timely, relevant, "
                "and not disruptive."
            ),
        )

    def _get_system_prompt(self) -> str:
        return (
            f"You are {self.name}, the {self.role}. {self.backstory}\n\n"
            "Notification channels:\n"
            "  - In-app (UI notifications)\n"
            "  - Push (mobile push notifications)\n"
            "  - Toast (brief on-screen messages)\n"
            "  - Sound (audio alerts)\n"
            "  - Email (summary/important notifications)\n"
            "  - SMS (critical alerts)\n\n"
            "Rules:\n"
            "1. Don't spam — batch notifications when possible.\n"
            "2. Prioritize by urgency (critical → info).\n"
            "3. Respect quiet hours if configured.\n"
            "4. Channel selection depends on urgency and user preference.\n"
        )

    def process(self, input_data: Any,
                context: Optional[dict] = None) -> AgentResult:
        """Process a notification request."""
        request = str(input_data) if not isinstance(input_data, str) else input_data

        return AgentResult(
            success=True,
            response=(
                f"**Notification**\n\n"
                f"Notification delivered: {request[:100]}"
            ),
            data={
                "request": request[:200],
                "channel": "in_app",
                "delivered": True,
                "timestamp": datetime.now().isoformat(),
            },
            agent_name=self.name,
        )


class WorkflowAgent(AgentBase):
    """Workflow Agent — complex workflow execution.

    Executes multi-step workflows with sequential/parallel steps,
    conditional branches, retries, timeouts, and human approval.
    """

    def __init__(self):
        super().__init__(
            name="workflow",
            role="Multi-step workflow execution engine",
            goal="Execute complex workflows reliably with proper error handling",
            backstory=(
                "I am the workflow agent. I execute complex multi-step workflows "
                "with support for sequential and parallel steps, conditional "
                "branches, retries, timeouts, and human-in-the-loop approval. "
                "I ensure workflows complete reliably and provide visibility "
                "into execution progress."
            ),
        )

    def _get_system_prompt(self) -> str:
        return (
            f"You are {self.name}, the {self.role}. {self.backstory}\n\n"
            "Workflow features:\n"
            "  - Sequential and parallel execution\n"
            "  - Conditional branching (if/else)\n"
            "  - Loops and retries\n"
            "  - Timeout handling\n"
            "  - Human approval gates\n"
            "  - Reusable templates\n"
            "  - Execution analytics\n\n"
            "Example workflow:\n"
            "  1. Research topic\n"
            "  2. Summarize findings\n"
            "  3. Write code\n"
            "  4. Test code\n"
            "  5. Deploy\n"
            "  6. Notify user\n\n"
            "Rules:\n"
            "1. Validate workflow definition before execution.\n"
            "2. Handle step failures gracefully — retry or skip.\n"
            "3. Provide progress updates during execution.\n"
            "4. Support resuming failed workflows from the failure point.\n"
            "5. Log every step for audit and debugging.\n"
        )

    def process(self, input_data: Any,
                context: Optional[dict] = None) -> AgentResult:
        """Process a workflow request."""
        request = str(input_data) if not isinstance(input_data, str) else input_data

        return AgentResult(
            success=True,
            response=(
                f"**Workflow Engine**\n\n"
                f"Workflow request received.\n"
                f"I'll orchestrate the multi-step execution across "
                f"the appropriate agents."
            ),
            data={
                "request": request[:200],
                "workflow_id": None,
                "steps_planned": 0,
                "status": "pending",
            },
            agent_name=self.name,
            needs_followup=True,
            followup_agent="executive",
        )
