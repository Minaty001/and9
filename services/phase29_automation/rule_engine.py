"""
Phase 29 — Rule Engine.

Evaluates automation rules, executes actions, and manages
execution history with rollback support.
"""

from __future__ import annotations

import time
import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .config import AutomationConfig
from .models import AutomationRule, Action, RuleExecution

logger = logging.getLogger(__name__)


class RuleEngine:
    """Evaluates rules and executes actions with rollback support.

    Usage:
        engine = RuleEngine()
        rule = AutomationRule(...)
        result = engine.evaluate_and_execute(rule, context)
    """

    def __init__(self, config: Optional[AutomationConfig] = None):
        self.config = config or AutomationConfig()
        self._rules: Dict[str, AutomationRule] = {}
        self._history: List[RuleExecution] = []
        self._cooldowns: Dict[str, float] = {}

    def add_rule(self, rule: AutomationRule) -> str:
        """Add a rule to the engine.

        Args:
            rule: AutomationRule to add.

        Returns:
            Rule ID.
        """
        if len(self._rules) >= self.config.max_rules:
            # Remove lowest-priority inactive rule
            inactive = [r for r in self._rules.values() if not r.is_active]
            if inactive:
                lowest = min(inactive, key=lambda r: r.priority)
                del self._rules[lowest.id]
            else:
                raise RuntimeError(f"Max rules ({self.config.max_rules}) reached")

        self._rules[rule.id] = rule
        return rule.id

    def update_rule(self, rule_id: str, **updates) -> Optional[AutomationRule]:
        """Update a rule's fields.

        Args:
            rule_id: Rule identifier.
            **updates: Fields to update.

        Returns:
            Updated rule or None if not found.
        """
        rule = self._rules.get(rule_id)
        if not rule:
            return None

        for key, value in updates.items():
            if hasattr(rule, key):
                setattr(rule, key, value)

        return rule

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule by ID."""
        if rule_id in self._rules:
            del self._rules[rule_id]
            return True
        return False

    def get_rule(self, rule_id: str) -> Optional[AutomationRule]:
        """Get a rule by ID."""
        return self._rules.get(rule_id)

    def list_rules(self) -> List[AutomationRule]:
        """List all rules."""
        return list(self._rules.values())

    def enable_rule(self, rule_id: str) -> bool:
        """Enable a rule."""
        rule = self._rules.get(rule_id)
        if not rule:
            return False
        rule.is_active = True
        rule.isenabled = True
        return True

    def disable_rule(self, rule_id: str) -> bool:
        """Disable a rule."""
        rule = self._rules.get(rule_id)
        if not rule:
            return False
        rule.is_active = False
        rule.isenabled = False
        return True

    def evaluate_rule(self, rule: AutomationRule, context: Dict[str, Any]) -> bool:
        """Evaluate whether a rule should fire given context.

        Args:
            rule: The rule to evaluate.
            context: Current context for evaluation.

        Returns:
            True if rule should fire.
        """
        if not rule.is_active or not rule.isenabled:
            return False

        # Check cooldown
        if rule.id in self._cooldowns:
            elapsed = time.time() - self._cooldowns[rule.id]
            if elapsed < rule.cooldown_seconds:
                return False

        # Evaluate trigger conditions
        trigger = rule.trigger
        trigger_type = trigger.get("type", "")
        trigger_params = trigger.get("params", {})

        if trigger_type == "time":
            # Match against context time
            return self._evaluate_time_trigger(trigger_params, context)
        elif trigger_type == "schedule":
            return self._evaluate_schedule_trigger(trigger_params, context)
        elif trigger_type == "event":
            return self._evaluate_event_trigger(trigger_params, context)
        elif trigger_type == "context":
            return self._evaluate_context_trigger(trigger_params, context)
        elif trigger_type == "system":
            return self._evaluate_system_trigger(trigger_params, context)

        return False

    def evaluate_and_execute(self, rule: AutomationRule, context: Dict[str, Any]) -> Tuple[bool, RuleExecution]:
        """Evaluate and execute a rule in one step.

        Args:
            rule: The rule to evaluate and execute.
            context: Current context.

        Returns:
            Tuple of (success, RuleExecution record).
        """
        t0 = time.perf_counter()

        if not self.evaluate_rule(rule, context):
            return False, RuleExecution(
                rule_id=rule.id, rule_name=rule.name,
                trigger_type=rule.trigger.get("type", "unknown"),
                success=False, error="Rule conditions not met",
                duration_ms=0.0,
            )

        actions_taken = []
        success = True
        error_msg = ""
        rollback_performed = False

        for action_config in rule.actions:
            action_type = action_config.get("type", "")
            action_params = action_config.get("params", {})

            try:
                action_result = self._execute_action(action_type, action_params, context)
                taken = {"type": action_type, "params": action_params, "success": action_result}
                actions_taken.append(taken)

                if not action_result:
                    success = False
                    if self.config.enable_rollback:
                        self._rollback(actions_taken[:-1])
                        rollback_performed = True
                    break
            except Exception as e:
                success = False
                error_msg = str(e)
                actions_taken.append({"type": action_type, "params": action_params, "success": False, "error": str(e)})
                if self.config.enable_rollback:
                    self._rollback(actions_taken[:-1])
                    rollback_performed = True
                break

        elapsed = (time.perf_counter() - t0) * 1000

        # Update rule state
        rule.last_triggered = datetime.now(timezone.utc)
        rule.execution_count += 1

        # Set cooldown
        self._cooldowns[rule.id] = time.time()

        execution = RuleExecution(
            rule_id=rule.id,
            rule_name=rule.name,
            trigger_type=rule.trigger.get("type", "unknown"),
            actions_taken=actions_taken,
            success=success,
            duration_ms=round(elapsed, 2),
            error=error_msg,
            rollback_performed=rollback_performed,
        )

        self._add_to_history(execution)
        return success, execution

    def get_execution_history(self, limit: int = 50) -> List[RuleExecution]:
        """Get execution history.

        Args:
            limit: Max entries to return.

        Returns:
            List of RuleExecution, most recent first.
        """
        return sorted(self._history, key=lambda e: e.triggered_at, reverse=True)[:limit]

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        active_rules = sum(1 for r in self._rules.values() if r.is_active)
        total_executions = sum(r.execution_count for r in self._rules.values())
        successful = sum(1 for e in self._history if e.success)
        failed = sum(1 for e in self._history if not e.success)

        return {
            "total_rules": len(self._rules),
            "active_rules": active_rules,
            "total_executions": total_executions,
            "history_entries": len(self._history),
            "successful_executions": successful,
            "failed_executions": failed,
        }

    def clear(self) -> None:
        """Clear all rules, history, and cooldowns."""
        self._rules.clear()
        self._history.clear()
        self._cooldowns.clear()

    # ── Internal ──────────────────────────────────────────────────

    def _evaluate_time_trigger(self, params: Dict, context: Dict) -> bool:
        """Evaluate a time-based trigger."""
        hour = params.get("hour")
        minute = params.get("minute")
        if hour is not None:
            ctx_hour = context.get("hour", datetime.now(timezone.utc).hour)
            if ctx_hour != hour:
                return False
        if minute is not None:
            ctx_minute = context.get("minute", datetime.now(timezone.utc).minute)
            if ctx_minute != minute:
                return False
        return True

    def _evaluate_schedule_trigger(self, params: Dict, context: Dict) -> bool:
        """Evaluate a schedule-based trigger."""
        days = params.get("days", [])
        if days:
            ctx_day = context.get("day_of_week", datetime.now(timezone.utc).weekday())
            if ctx_day not in days:
                return False
        return self._evaluate_time_trigger(params, context)

    def _evaluate_event_trigger(self, params: Dict, context: Dict) -> bool:
        """Evaluate an event-based trigger."""
        event_name = params.get("event", "")
        ctx_event = context.get("event", "")
        return event_name == ctx_event

    def _evaluate_context_trigger(self, params: Dict, context: Dict) -> bool:
        """Evaluate a context-based trigger."""
        key = params.get("key", "")
        value = params.get("value")
        ctx_value = context.get(key)
        if value is not None:
            return ctx_value == value
        return ctx_value is not None

    def _evaluate_system_trigger(self, params: Dict, context: Dict) -> bool:
        """Evaluate a system-based trigger."""
        state = params.get("state", "")
        ctx_state = context.get("system_state", "")
        return state == ctx_state

    def _execute_action(self, action_type: str, params: Dict, context: Dict) -> bool:
        """Execute a single action.

        Args:
            action_type: Type of action to execute.
            params: Action parameters.
            context: Execution context.

        Returns:
            True if action succeeded.
        """
        if action_type == "notify":
            # Notification action - always succeeds in simulation
            logger.info("NOTIFY: %s", params.get("message", ""))
            return True
        elif action_type == "command":
            # Command action - execute as subprocess
            import subprocess
            cmd = params.get("command", "")
            if not cmd:
                return False
            try:
                # Simulate - just log in test mode
                logger.info("COMMAND: %s", cmd)
                return True
            except Exception as e:
                logger.error("Command failed: %s", e)
                return False
        elif action_type == "system":
            # System action
            logger.info("SYSTEM: %s", params.get("action", ""))
            return True
        elif action_type == "message":
            # Message action
            logger.info("MESSAGE: %s", params.get("text", ""))
            return True
        elif action_type == "api":
            # API action - simulate
            logger.info("API: %s %s", params.get("method", "GET"), params.get("url", ""))
            return True
        return False

    def _rollback(self, actions_taken: List[Dict]) -> None:
        """Roll back a list of actions that were taken.

        Args:
            actions_taken: List of action dicts that succeeded.
        """
        if not self.config.enable_rollback:
            return

        # Reverse the actions list
        for action in reversed(actions_taken):
            action_type = action.get("type", "")
            logger.info("ROLLBACK: %s", action_type)

    def _add_to_history(self, execution: RuleExecution) -> None:
        """Add execution to history, trimming if needed."""
        if not self.config.enable_execution_history:
            return
        self._history.append(execution)
        if len(self._history) > self.config.max_history_entries:
            self._history = self._history[-self.config.max_history_entries:]
