"""
Phase 45 — Workflow Engine.

Creates, executes, and manages multi-step workflows
with support for pausing, resuming, and step approval.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .models import Workflow, WorkflowStep
from .config import RoadmapConfig

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """Manages workflow lifecycle — creation, execution, and status tracking.

    Usage:
        we = WorkflowEngine()
        step = WorkflowStep(id='s1', name='Step 1', action='greet', params={})
        wf = we.create_workflow('test', 'Test workflow', [step])
        wf = we.execute_workflow(wf.id)
        status = we.get_workflow_status(wf.id)
    """

    def __init__(self, config: Optional[RoadmapConfig] = None):
        self.config = config or RoadmapConfig()
        self._workflows: Dict[str, Workflow] = {}

    def create_workflow(
        self,
        name: str,
        description: str = "",
        steps: Optional[List[WorkflowStep]] = None,
    ) -> Workflow:
        """Create a new workflow.

        Args:
            name: Workflow name.
            description: Workflow description.
            steps: List of workflow steps.

        Returns:
            The created Workflow.
        """
        wf_id = uuid.uuid4().hex[:12]
        now = datetime.now(timezone.utc)
        workflow = Workflow(
            id=wf_id,
            name=name,
            description=description,
            steps=steps or [],
            status="pending",
            created_at=now,
            updated_at=now,
        )
        self._workflows[wf_id] = workflow
        logger.info("Created workflow '%s' (id=%s, steps=%d)", name, wf_id, len(workflow.steps))
        return workflow

    def execute_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Execute a workflow.

        Args:
            workflow_id: Workflow identifier.

        Returns:
            The updated Workflow, or None if not found.
        """
        wf = self._workflows.get(workflow_id)
        if not wf:
            logger.warning("Workflow not found: %s", workflow_id)
            return None

        if wf.status == "running":
            logger.warning("Workflow '%s' is already running", workflow_id)
            return wf

        wf.status = "running"
        wf.updated_at = datetime.now(timezone.utc)

        # Simulate step execution
        for step in wf.steps:
            if step.status in ("completed", "running"):
                continue

            # Check dependencies
            deps_met = all(
                any(s.id == dep and s.status == "completed" for s in wf.steps)
                for dep in step.depends_on
            )
            if not deps_met:
                step.status = "pending"
                continue

            step.status = "completed"
            step.result = {"action": step.action, "status": "success"}

        # Check if all steps completed
        if all(s.status == "completed" for s in wf.steps):
            wf.status = "completed"
            logger.info("Workflow '%s' completed", workflow_id)

        return wf

    def pause_workflow(self, workflow_id: str) -> bool:
        """Pause a running workflow.

        Args:
            workflow_id: Workflow identifier.

        Returns:
            True if paused, False if not found.
        """
        wf = self._workflows.get(workflow_id)
        if not wf:
            return False
        if wf.status != "running":
            return False
        wf.status = "paused"
        wf.updated_at = datetime.now(timezone.utc)
        logger.info("Paused workflow '%s'", workflow_id)
        return True

    def resume_workflow(self, workflow_id: str) -> bool:
        """Resume a paused workflow.

        Args:
            workflow_id: Workflow identifier.

        Returns:
            True if resumed, False if not found or not paused.
        """
        wf = self._workflows.get(workflow_id)
        if not wf:
            return False
        if wf.status != "paused":
            return False
        wf.status = "running"
        wf.updated_at = datetime.now(timezone.utc)
        logger.info("Resumed workflow '%s'", workflow_id)
        return True

    def approve_step(self, workflow_id: str, step_id: str) -> bool:
        """Approve a step that requires approval.

        Args:
            workflow_id: Workflow identifier.
            step_id: Step identifier.

        Returns:
            True if approved, False if not found.
        """
        wf = self._workflows.get(workflow_id)
        if not wf:
            return False
        for step in wf.steps:
            if step.id == step_id and step.status == "pending":
                step.status = "running"
                wf.updated_at = datetime.now(timezone.utc)
                logger.info("Approved step '%s' in workflow '%s'", step_id, workflow_id)
                return True
        return False

    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a workflow.

        Args:
            workflow_id: Workflow identifier.

        Returns:
            Dict with workflow status details, or None if not found.
        """
        wf = self._workflows.get(workflow_id)
        if not wf:
            return None
        return {
            "id": wf.id,
            "name": wf.name,
            "status": wf.status,
            "steps_total": len(wf.steps),
            "steps_completed": sum(1 for s in wf.steps if s.status == "completed"),
            "steps_failed": sum(1 for s in wf.steps if s.status == "failed"),
            "steps_pending": sum(1 for s in wf.steps if s.status == "pending"),
            "created_at": wf.created_at.isoformat(),
            "updated_at": wf.updated_at.isoformat(),
        }

    def list_workflows(self) -> List[Workflow]:
        """List all workflows."""
        return list(self._workflows.values())
