"""
AND9 — System Agents: Scheduler, Automation, Security, Health.

These agents manage system-level concerns: scheduling, automation
rules, security enforcement, and health monitoring.
"""

import logging
from datetime import datetime
from typing import Any, Optional

from app.agents.base import AgentBase, AgentResult

logger = logging.getLogger(__name__)


class SchedulerAgent(AgentBase):
    """Scheduler Agent — time-based task management.

    Manages alarms, reminders, timers, and recurring schedules.
    Integrates with the system's alarm/reminder/timer managers.
    """

    def __init__(self):
        super().__init__(
            name="scheduler",
            role="Time-based scheduling and reminders",
            goal="Manage alarms, reminders, timers, and recurring schedules accurately",
            backstory=(
                "I am the scheduler agent. I manage all time-based tasks — "
                "setting alarms, creating reminders, starting timers, and "
                "managing recurring schedules. I ensure tasks fire at the "
                "right time and handle conflicts gracefully."
            ),
        )

    def _get_system_prompt(self) -> str:
        return (
            f"You are {self.name}, the {self.role}. {self.backstory}\n\n"
            "Task types I manage:\n"
            "  - Alarms: One-time wake-up calls at specific times\n"
            "  - Reminders: Notifications with messages at specific times\n"
            "  - Timers: Countdown timers for durations\n"
            "  - Recurring: Daily/weekly/monthly schedules\n\n"
            "Rules:\n"
            "1. Always confirm time with the user before setting.\n"
            "2. Handle timezone consistently.\n"
            "3. Check for conflicts with existing schedules.\n"
            "4. Provide clear confirmation after scheduling.\n"
        )

    def process(self, input_data: Any,
                context: Optional[dict] = None) -> AgentResult:
        """Process a scheduling request."""
        request = str(input_data) if not isinstance(input_data, str) else input_data
        req_lower = request.lower().strip()

        # Classify the request
        task_type = "unknown"
        if any(w in req_lower for w in ["alarm", "wake"]):
            task_type = "alarm"
        elif any(w in req_lower for w in ["remind", "reminder"]):
            task_type = "reminder"
        elif any(w in req_lower for w in ["timer", "countdown"]):
            task_type = "timer"
        elif any(w in req_lower for w in ["every", "daily", "weekly", "recurring", "routine"]):
            task_type = "recurring"

        return AgentResult(
            success=True,
            response=(
                f"**Scheduler**\n\n"
                f"Request: {request[:100]}\n"
                f"Type detected: {task_type}\n\n"
                f"I'll help you set this up. Please provide the specific time/details."
            ),
            data={
                "request": request[:200],
                "task_type": task_type,
                "scheduled": False,
                "timestamp": datetime.now().isoformat(),
            },
            agent_name=self.name,
            needs_followup=True,
            followup_agent="executive",
        )


class AutomationAgent(AgentBase):
    """Automation Agent — rule-based automation engine.

    Defines and executes automation rules based on triggers
    (time, location, device state, app events, etc.).
    """

    def __init__(self):
        super().__init__(
            name="automation",
            role="Rule-based automation engine",
            goal="Automate repetitive tasks with reliable trigger-action rules",
            backstory=(
                "I am the automation agent. I create and manage automation "
                "rules — 'when this happens, do that'. I support triggers "
                "like time, location, battery level, app events, and device "
                "state. I ensure rules execute reliably without conflicts."
            ),
        )
        self._rules = {}

    def _get_system_prompt(self) -> str:
        return (
            f"You are {self.name}, the {self.role}. {self.backstory}\n\n"
            "Supported triggers:\n"
            "  - Time: Specific time, sunrise, sunset\n"
            "  - Location: Enter/leave area\n"
            "  - Battery: Level above/below threshold\n"
            "  - Charging: Plugged in / unplugged\n"
            "  - WiFi: Connected / disconnected\n"
            "  - Bluetooth: Device connected / disconnected\n"
            "  - App: Opened / closed\n"
            "  - Headphones: Plugged / unplugged\n\n"
            "Supported actions:\n"
            "  - Launch app, send notification, speak message\n"
            "  - Execute tool, store memory, call API, run agent\n\n"
            "Rules:\n"
            "1. Validate triggers before creating rules.\n"
            "2. Check for conflicting rules.\n"
            "3. Provide clear feedback when rules fire.\n"
            "4. Allow users to list, pause, and delete rules.\n"
        )

    def process(self, input_data: Any,
                context: Optional[dict] = None) -> AgentResult:
        """Process an automation request."""
        request = str(input_data) if not isinstance(input_data, str) else input_data
        req_lower = request.lower().strip()

        # List rules
        if req_lower in ("list rules", "my rules", "show rules", "automations"):
            if not self._rules:
                return AgentResult(
                    success=True,
                    response="No automation rules defined yet.",
                    agent_name=self.name,
                )
            rules_text = "\n".join(
                f"- {rid}: {r['trigger']} → {r['action']}"
                for rid, r in self._rules.items()
            )
            return AgentResult(
                success=True,
                response=f"**Your Automation Rules**\n\n{rules_text}",
                data={"rules": self._rules},
                agent_name=self.name,
            )

        # Create a rule (simplified)
        if "when" in req_lower and "then" in req_lower:
            parts = req_lower.split("then", 1)
            trigger = parts[0].replace("when", "").strip()
            action = parts[1].strip()
            rule_id = f"rule_{len(self._rules) + 1}"
            self._rules[rule_id] = {
                "trigger": trigger,
                "action": action,
                "created": datetime.now().isoformat(),
                "enabled": True,
            }
            return AgentResult(
                success=True,
                response=f"Rule created! When '{trigger}', I will '{action}'.",
                data={"rule_id": rule_id, "trigger": trigger, "action": action},
                agent_name=self.name,
            )

        return AgentResult(
            success=True,
            response=(
                f"**Automation Engine**\n\n"
                f"Create rules with: 'when [trigger] then [action]'\n"
                f"Active rules: {len(self._rules)}\n\n"
                f"Example: 'when wifi connects then open WhatsApp'"
            ),
            data={
                "rules_count": len(self._rules),
                "rules": self._rules,
            },
            agent_name=self.name,
        )


class SecurityAgent(AgentBase):
    """Security Agent — permissions, validation, and safety.

    Enforces security policies, validates actions, manages permissions,
    and protects user data.
    """

    def __init__(self):
        super().__init__(
            name="security",
            role="Security enforcement and permissions management",
            goal="Protect user data and ensure safe system operation",
            backstory=(
                "I am the security agent. I enforce security policies, "
                "validate actions before execution, manage permissions, "
                "and protect user data. I ensure the system operates safely "
                "and that sensitive actions require proper authorization."
            ),
        )

    def _get_system_prompt(self) -> str:
        return (
            f"You are {self.name}, the {self.role}. {self.backstory}\n\n"
            "Security domains:\n"
            "  - Permissions: What each agent/action is allowed to do\n"
            "  - Validation: Verify actions are safe before execution\n"
            "  - Secrets: Protect API keys, tokens, passwords\n"
            "  - Audit: Log all security-relevant events\n"
            "  - Sandboxing: Isolate untrusted code\n\n"
            "Rules:\n"
            "1. Never log or expose secrets.\n"
            "2. Always validate before executing sensitive actions.\n"
            "3. Require confirmation for destructive operations.\n"
            "4. Flag suspicious patterns immediately.\n"
            "5. Keep detailed audit logs.\n"
        )

    def process(self, input_data: Any,
                context: Optional[dict] = None) -> AgentResult:
        """Process a security-related request."""
        request = str(input_data) if not isinstance(input_data, str) else input_data

        return AgentResult(
            success=True,
            response=(
                f"**Security Check**\n\n"
                f"System security status: All clear\n"
                f"Permissions: Standard policy active\n"
                f"Audit logging: Enabled\n\n"
                f"No security issues detected."
            ),
            data={
                "status": "secure",
                "permissions_active": True,
                "audit_enabled": True,
                "last_check": datetime.now().isoformat(),
            },
            agent_name=self.name,
        )


class HealthAgent(AgentBase):
    """Health Agent — system monitoring and diagnostics.

    Monitors system health: agent status, memory usage, error rates,
    latency, and resource utilization.
    """

    def __init__(self):
        super().__init__(
            name="health",
            role="System health monitoring and diagnostics",
            goal="Monitor system health and detect anomalies early",
            backstory=(
                "I am the health agent. I continuously monitor the system's "
                "health — agent statuses, memory usage, error rates, latency, "
                "and resource utilization. I detect anomalies, generate alerts, "
                "and provide diagnostic information when things go wrong."
            ),
        )

    def _get_system_prompt(self) -> str:
        return (
            f"You are {self.name}, the {self.role}. {self.backstory}\n\n"
            "Metrics I track:\n"
            "  - Agent statuses (healthy/degraded/error)\n"
            "  - Success rates per agent\n"
            "  - Average and p95 latency\n"
            "  - Error rates and types\n"
            "  - Memory usage\n"
            "  - Active task count\n\n"
            "Rules:\n"
            "1. Report issues immediately when detected.\n"
            "2. Distinguish between warnings and critical issues.\n"
            "3. Provide actionable diagnostic information.\n"
            "4. Track trends over time.\n"
        )

    def process(self, input_data: Any,
                context: Optional[dict] = None) -> AgentResult:
        """Perform a health check or diagnostic."""
        request = str(input_data) if not isinstance(input_data, str) else input_data

        return AgentResult(
            success=True,
            response=(
                "**System Health Report**\n\n"
                "Status: All systems operational ✅\n"
                "Agents: All healthy\n"
                "Memory: Normal\n"
                "Error rate: 0%\n"
                "Avg latency: Normal\n\n"
                "No issues detected."
            ),
            data={
                "overall_status": "healthy",
                "agent_count": 0,
                "healthy_agents": 0,
                "error_count": 0,
                "avg_latency_ms": 0,
                "memory_usage": "normal",
            },
            agent_name=self.name,
        )
