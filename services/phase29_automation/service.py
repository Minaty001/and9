"""
Phase 29 — Automation Engine Service.

ServiceBase wrapper for the Automation Engine.
"""

from __future__ import annotations

import time
import logging
from typing import Any, Dict, List, Optional, Tuple

from services.base.service_base import ServiceBase
from .config import AutomationConfig
from .models import AutomationRule, RuleExecution
from .rule_engine import RuleEngine

logger = logging.getLogger(__name__)


class AutomationService(ServiceBase):
    """Automation engine service for if-this-then-that rules.

    Usage:
        svc = AutomationService()
        await svc.initialize()
        rule = AutomationRule(id="1", name="...", trigger=..., actions=[...])
        await svc.create_rule(rule)
        success, execution = await svc.evaluate_and_execute(rule, context)
    """

    def __init__(self, config: Optional[AutomationConfig] = None):
        super().__init__(name="jarvis_automation", version="1.0.0")
        self.config = config or AutomationConfig()
        self.rule_engine: Optional[RuleEngine] = None
        self._start_time = 0.0

    async def initialize(self) -> bool:
        self._start_time = time.time()
        try:
            self.rule_engine = RuleEngine(self.config)
            self._metrics.reset()
            self._initialized = True
            logger.info("AutomationService initialized")
            return True
        except Exception as e:
            logger.error("AutomationService init failed: %s", e)
            return False

    async def shutdown(self) -> None:
        logger.info("AutomationService shutting down...")
        self._initialized = False

    async def create_rule(self, rule_or_name, **kwargs) -> AutomationRule:
        """Create a new automation rule.

        Accepts either an AutomationRule object or keyword args
        (name=..., trigger={...}, actions=[...], ...).

        Returns the created AutomationRule.
        """
        if not self.rule_engine:
            raise RuntimeError("AutomationService not initialized")
        self._metrics.counter("rules_created", 1)
        if isinstance(rule_or_name, AutomationRule):
            self.rule_engine.add_rule(rule_or_name)
            return rule_or_name
        # Construct an AutomationRule from keyword args
        import uuid
        rule = AutomationRule(
            id=kwargs.pop("id", uuid.uuid4().hex[:12]),
            name=rule_or_name,
            **kwargs,
        )
        self.rule_engine.add_rule(rule)
        return rule

    async def update_rule(self, rule_id: str, **updates) -> Optional[AutomationRule]:
        """Update an existing rule."""
        if not self.rule_engine:
            raise RuntimeError("AutomationService not initialized")
        return self.rule_engine.update_rule(rule_id, **updates)

    async def delete_rule(self, rule_id: str) -> bool:
        """Delete a rule."""
        if not self.rule_engine:
            raise RuntimeError("AutomationService not initialized")
        self._metrics.counter("rules_deleted", 1)
        return self.rule_engine.remove_rule(rule_id)

    async def get_rule(self, rule_id: str) -> Optional[AutomationRule]:
        """Get a rule by ID."""
        if not self.rule_engine:
            raise RuntimeError("AutomationService not initialized")
        return self.rule_engine.get_rule(rule_id)

    async def list_rules(self) -> List[AutomationRule]:
        """List all rules."""
        if not self.rule_engine:
            raise RuntimeError("AutomationService not initialized")
        return self.rule_engine.list_rules()

    async def enable_rule(self, rule_id: str) -> bool:
        """Enable a rule."""
        if not self.rule_engine:
            raise RuntimeError("AutomationService not initialized")
        return self.rule_engine.enable_rule(rule_id)

    async def disable_rule(self, rule_id: str) -> bool:
        """Disable a rule."""
        if not self.rule_engine:
            raise RuntimeError("AutomationService not initialized")
        return self.rule_engine.disable_rule(rule_id)

    async def evaluate_and_execute(self, rule: AutomationRule, context: Dict[str, Any]) -> Tuple[bool, RuleExecution]:
        """Evaluate and execute a rule."""
        if not self.rule_engine:
            raise RuntimeError("AutomationService not initialized")
        t0 = time.perf_counter()
        success, execution = self.rule_engine.evaluate_and_execute(rule, context)
        elapsed = (time.perf_counter() - t0) * 1000
        self._metrics.counter("rules_evaluated", 1)
        if success:
            self._metrics.counter("rules_executed", 1)
        self._metrics.histogram("evaluation_time_ms", elapsed)
        return success, execution

    async def get_execution_history(self, limit: int = 50) -> List[RuleExecution]:
        """Get execution history."""
        if not self.rule_engine:
            raise RuntimeError("AutomationService not initialized")
        return self.rule_engine.get_execution_history(limit)

    async def health(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        stats = self.rule_engine.get_stats() if self.rule_engine else {}
        return {
            "status": "healthy" if self._initialized else "unhealthy",
            "service_name": self.name,
            "version": self.version,
            "initialized": self._initialized,
            "uptime_seconds": round(uptime, 1),
            "total_rules": stats.get("total_rules", 0),
            "active_rules": stats.get("active_rules", 0),
        }

    async def stats(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time if self._start_time > 0 else 0
        engine_stats = self.rule_engine.get_stats() if self.rule_engine else {}
        return {
            "service": self.name,
            "version": self.version,
            "uptime_seconds": round(uptime, 1),
            **engine_stats,
            "metrics": self._metrics.snapshot(),
        }
