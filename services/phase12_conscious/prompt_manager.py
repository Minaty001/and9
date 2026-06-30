"""
Phase 12 — Prompt Manager.

Template-based prompt construction with variables, versioning, and
pre-built system prompts for reasoning, planning, coding, and
summarization.
"""

from __future__ import annotations

import re
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from string import Formatter

from .models import Conversation, Role

logger = logging.getLogger(__name__)


# ── Prompt Template ─────────────────────────────────────────────────


@dataclass
class PromptTemplate:
    """A reusable prompt template with variable substitution."""
    name: str
    system_template: str
    user_template: str
    version: str = "1.0.0"
    description: str = ""
    expected_variables: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    def format_system(self, **variables: Any) -> str:
        """Format the system template with variables."""
        try:
            return _safe_format(self.system_template, **variables)
        except KeyError as e:
            logger.warning("Prompt '%s': missing system variable %s", self.name, e)
            return self.system_template

    def format_user(self, **variables: Any) -> str:
        """Format the user template with variables."""
        try:
            return _safe_format(self.user_template, **variables)
        except KeyError as e:
            logger.warning("Prompt '%s': missing user variable %s", self.name, e)
            return self.user_template

    def build_conversation(self, **variables: Any) -> Conversation:
        """Build a complete Conversation from this template."""
        conv = Conversation(system_prompt=self.format_system(**variables))
        conv.add_message(Role.USER, self.format_user(**variables))
        return conv

    def validate(self) -> List[str]:
        """Check that expected variables appear in templates."""
        missing: List[str] = []
        if not self.system_template and not self.user_template:
            missing.append("both templates are empty")
        for var in self.expected_variables:
            if var not in self.system_template + self.user_template:
                missing.append(f"expected variable '{{{var}}}' not found in templates")
        return missing


# ── Built-in templates ──────────────────────────────────────────────


SYSTEM_REASONING = """You are JARVIS, an AI assistant with structured reasoning capabilities.

Guidelines:
1. Break down complex tasks into steps.
2. Think step by step before answering.
3. Cite sources when referencing specific information.
4. Be concise and direct.
5. If you don't know something, say so.
6. Use tools when appropriate; track their provenance.

Context:
- Current time: {current_time}
- User context: {user_context}"""

USER_REASONING = """{query}"""

SYSTEM_PLANNING = """You are JARVIS's planning subsystem. Your job is to decompose
goals into executable steps.

For each step specify:
- Step name and description
- Dependencies on other steps
- Required tools or data
- Success criteria

Output a structured plan. Use parallel steps where possible."""

USER_PLANNING = """Goal: {goal}

Available tools: {available_tools}
Context: {context}"""

SYSTEM_CODING = """You are JARVIS's coding subsystem. Generate production-quality code.

Guidelines:
- Follow the project's existing patterns and style.
- Include type hints and docstrings.
- Handle errors appropriately.
- Be secure and efficient.
- Output only the code unless asked for explanation."""

USER_CODING = """Task: {task}

Language: {language}
Constraints: {constraints}
Existing code context: {code_context}"""

SYSTEM_SUMMARIZATION = """You are JARVIS's summarization subsystem.
Condense the provided content while preserving key information, entities,
and actionable items. Be concise."""

USER_SUMMARIZATION = """Content to summarize:

{content}

Focus: {focus}
Max length: {max_length} words"""


# ── Prompt Manager ──────────────────────────────────────────────────


class PromptManager:
    """Manages prompt templates and builds conversations."""

    def __init__(self):
        self._templates: Dict[str, PromptTemplate] = {}
        self._register_defaults()

    # ── Registration ──────────────────────────────────────────────

    def register(self, template: PromptTemplate) -> None:
        """Register a prompt template."""
        issues = template.validate()
        if issues:
            logger.warning("Prompt '%s' has issues: %s", template.name, issues)
        self._templates[template.name] = template
        logger.debug("Registered prompt template '%s' v%s", template.name, template.version)

    def get(self, name: str) -> Optional[PromptTemplate]:
        """Get a template by name."""
        return self._templates.get(name)

    def list_templates(self) -> List[Dict[str, Any]]:
        """List all registered templates."""
        return [
            {
                "name": t.name,
                "version": t.version,
                "description": t.description,
                "variables": t.expected_variables,
                "tags": t.tags,
            }
            for t in self._templates.values()
        ]

    # ── Conversation building ─────────────────────────────────────

    def build(
        self,
        template_name: str,
        **variables: Any,
    ) -> Optional[Conversation]:
        """Build a conversation from a named template."""
        template = self._templates.get(template_name)
        if not template:
            logger.error("Unknown prompt template '%s'", template_name)
            return None
        return template.build_conversation(**variables)

    def build_reasoning(self, query: str, user_context: str = "") -> Conversation:
        """Build a reasoning conversation."""
        return self.build(
            "reasoning",
            query=query,
            user_context=user_context or "general query",
            current_time=self._get_time_str(),
        )

    def build_planning(
        self,
        goal: str,
        available_tools: List[str],
        context: str = "",
    ) -> Conversation:
        """Build a planning conversation."""
        return self.build(
            "planning",
            goal=goal,
            available_tools=json.dumps(available_tools, indent=2),
            context=context or "No additional context",
        )

    def build_coding(
        self,
        task: str,
        language: str = "python",
        constraints: str = "",
        code_context: str = "",
    ) -> Conversation:
        """Build a coding conversation."""
        return self.build(
            "coding",
            task=task,
            language=language,
            constraints=constraints or "None",
            code_context=code_context or "No existing code",
        )

    def build_summarization(
        self,
        content: str,
        focus: str = "key points",
        max_length: int = 200,
    ) -> Conversation:
        """Build a summarization conversation."""
        return self.build(
            "summarization",
            content=content,
            focus=focus,
            max_length=str(max_length),
        )

    # ── Private ───────────────────────────────────────────────────

    def _register_defaults(self) -> None:
        """Register built-in default templates."""
        defaults = [
            PromptTemplate(
                name="reasoning",
                system_template=SYSTEM_REASONING,
                user_template=USER_REASONING,
                description="General query reasoning",
                expected_variables=["query", "user_context", "current_time"],
                tags=["reasoning", "general"],
            ),
            PromptTemplate(
                name="planning",
                system_template=SYSTEM_PLANNING,
                user_template=USER_PLANNING,
                description="Goal decomposition planning",
                expected_variables=["goal", "available_tools", "context"],
                tags=["planning"],
            ),
            PromptTemplate(
                name="coding",
                system_template=SYSTEM_CODING,
                user_template=USER_CODING,
                description="Code generation",
                expected_variables=["task", "language", "constraints", "code_context"],
                tags=["coding"],
            ),
            PromptTemplate(
                name="summarization",
                system_template=SYSTEM_SUMMARIZATION,
                user_template=USER_SUMMARIZATION,
                description="Content summarization",
                expected_variables=["content", "focus", "max_length"],
                tags=["summarization"],
            ),
        ]
        for tpl in defaults:
            self.register(tpl)

    @staticmethod
    def _get_time_str() -> str:
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _safe_format(template: str, **variables: Any) -> str:
    """Format a string, allowing missing variables to pass through."""
    result = template
    for key, value in variables.items():
        result = result.replace(f"{{{key}}}", str(value))
    return result
