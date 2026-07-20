"""
app/brain/planner.py — Multi-step task planner for AND9

Handles complex requests that require multiple steps.
Breaks down requests into a sequence of actions and executes them.

Example:
  "Order a pizza and set a timer for 30 minutes"
  -> [order_pizza, set_timer(30)]

  "Research AI trends, write a summary, and email it to dad"
  -> [search(ai_trends), summarize(results), email(dad)]
"""

import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


class Planner:
    """
    Decomposes multi-step requests into ordered action plans.
    Uses the LLM to parse complex requests when needed.
    """

    def plan(self, text: str, analysis) -> List[Dict]:
        """
        Break a request into steps.
        Returns list of {"intent": str, "params": dict, "priority": int}.

        Currently returns a single-step plan; multi-step decomposition
        is added in v5.1.
        """
        return [
            {"intent": analysis.intent, "params": analysis.entities, "priority": 2}
        ]

    def describe(self, steps: List[Dict]) -> str:
        """Return a human-readable summary of a plan."""
        descriptions = []
        for step in steps:
            intent = step.get("intent", "unknown")
            params = step.get("params", {})
            desc = intent.replace("_", " ").title()
            if params:
                param_str = ", ".join(f"{k}={v}" for k, v in params.items())
                desc += f" ({param_str})"
            descriptions.append(desc)
        return " -> ".join(descriptions) if descriptions else "No steps."