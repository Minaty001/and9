"""
Phase 30 — Template Engine.

Registers and renders notification templates with variable substitution.
"""

from __future__ import annotations

import uuid
import logging
from typing import Any, Dict, List, Optional, Tuple

from .config import NotificationConfig
from .models import NotificationTemplate

logger = logging.getLogger(__name__)


class TemplateEngine:
    """Registers and renders notification templates.

    Usage:
        engine = TemplateEngine()
        tid = engine.register_template(NotificationTemplate(...))
        title, message = engine.render("welcome", {"name": "User"})
    """

    def __init__(self, config: Optional[NotificationConfig] = None):
        self.config = config or NotificationConfig()
        self._templates: Dict[str, NotificationTemplate] = {}

    def register_template(self, template: NotificationTemplate) -> str:
        """Register a notification template.

        Args:
            template: NotificationTemplate to register.

        Returns:
            Template ID.
        """
        self._templates[template.name] = template
        return template.id

    def render(self, template_name: str, variables: Dict[str, Any]) -> Tuple[str, str]:
        """Render a template with variables.

        Args:
            template_name: Name of registered template.
            variables: Dict of variable values.

        Returns:
            Tuple of (title, message).

        Raises:
            ValueError: If template not found.
        """
        if not self.config.enable_templates:
            raise RuntimeError("Templates are disabled")

        template = self._templates.get(template_name)
        if not template:
            raise ValueError(f"Template '{template_name}' not found")

        # Simple variable substitution
        title = template.title_template
        message = template.message_template

        for var_name, var_value in variables.items():
            placeholder = "{" + var_name + "}"
            title = title.replace(placeholder, str(var_value))
            message = message.replace(placeholder, str(var_value))

        return title, message

    def list_templates(self) -> List[NotificationTemplate]:
        """List all registered templates."""
        return list(self._templates.values())

    def get_template(self, name: str) -> Optional[NotificationTemplate]:
        """Get a template by name."""
        return self._templates.get(name)

    def delete_template(self, name: str) -> bool:
        """Delete a template by name.

        Args:
            name: Template name.

        Returns:
            True if deleted, False otherwise.
        """
        if name in self._templates:
            del self._templates[name]
            return True
        return False

    def get_template_count(self) -> int:
        """Return template count."""
        return len(self._templates)

    def clear(self) -> None:
        """Clear all templates."""
        self._templates.clear()
