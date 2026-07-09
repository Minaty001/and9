"""app/plugins/calculator/plugin.py — Calculator plugin for AND9"""
import logging
import re

from app.plugins.base_plugin import BasePlugin

logger = logging.getLogger(__name__)


class Plugin(BasePlugin):
    name = "CalculatorPlugin"
    version = "1.0"
    intents = ["calculate", "math", "calculator"]
    ram_estimate_mb = 2

    def initialize(self):
        pass

    def handle(self, intent: str, entities: dict) -> dict:
        """Evaluate a mathematical expression."""
        expression = entities.get("expression", "")
        if not expression:
            return {"success": False, "response": "No expression provided."}

        # Sanitize: only allow safe math characters
        if not re.match(r'^[\d\s+\-*/().,%^]+$', expression):
            return {"success": False, "response": "Invalid expression."}

        try:
            result = eval(expression, {"__builtins__": {}}, {})
            return {
                "success": True,
                "response": f"{expression} = {result}",
                "result": result,
            }
        except Exception as e:
            return {"success": False, "response": f"Calculation error: {e}"}