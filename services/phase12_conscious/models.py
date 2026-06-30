"""
Phase 12 — Conscious Brain Data Models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


# ── Enums ───────────────────────────────────────────────────────────


class Role(str, Enum):
    """Message role in a conversation."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ReasoningStrategy(str, Enum):
    """Strategy for structuring reasoning."""
    CHAIN_OF_THOUGHT = "chain_of_thought"
    PLAN_THEN_EXECUTE = "plan_then_execute"
    REACT = "react"
    DIRECT = "direct"


class CitationType(str, Enum):
    """Type of citation source."""
    MEMORY = "memory"
    WEB = "web"
    DOCUMENT = "document"
    TOOL_OUTPUT = "tool_output"
    USER_INPUT = "user_input"
    SYSTEM = "system"


# ── Message / Conversation ──────────────────────────────────────────


@dataclass
class Message:
    """A single message in the conversation."""
    role: Role
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None


@dataclass
class Conversation:
    """A conversation history."""
    messages: List[Message] = field(default_factory=list)
    system_prompt: str = ""

    def add_message(self, role: Role, content: str, **kwargs) -> None:
        self.messages.append(Message(role=role, content=content, **kwargs))

    def total_tokens_estimate(self) -> int:
        """Rough token estimate: ~4 chars per token."""
        total = len(self.system_prompt)
        for msg in self.messages:
            total += len(msg.content)
        return total // 4


# ── Citations / Provenance ──────────────────────────────────────────


@dataclass
class Citation:
    """A citation to a source used in a response."""
    source_id: str
    source_type: CitationType
    excerpt: str
    relevance: float = 1.0
    url: Optional[str] = None
    timestamp: Optional[str] = None


@dataclass
class ToolCall:
    """A tool invocation record for provenance."""
    tool_name: str
    arguments: Dict[str, Any] = field(default_factory=dict)
    result_summary: str = ""
    duration_ms: float = 0.0
    success: bool = True


@dataclass
class Provenance:
    """Full provenance for a conscious brain response."""
    tool_calls: List[ToolCall] = field(default_factory=list)
    citations: List[Citation] = field(default_factory=list)
    reasoning_steps: List[str] = field(default_factory=list)


# ── Usage / Cost ────────────────────────────────────────────────────


@dataclass
class UsageStats:
    """Token usage and cost estimation."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    provider: str = ""
    model: str = ""

    # Cost per 1K tokens (approximate) — class-level constants
    _PROMPT_RATES: Dict[str, float] = field(default_factory=lambda: {
        "gpt-4o": 0.0025,
        "gpt-4o-mini": 0.00015,
        "claude-3-5-sonnet": 0.0030,
        "claude-3-haiku": 0.00025,
        "local": 0.0,
    })
    _COMPLETION_RATES: Dict[str, float] = field(default_factory=lambda: {
        "gpt-4o": 0.0100,
        "gpt-4o-mini": 0.00060,
        "claude-3-5-sonnet": 0.0150,
        "claude-3-haiku": 0.00125,
        "local": 0.0,
    })

    def calculate_cost(self) -> float:
        """Estimate cost based on token usage."""
        prompt_rate = self._PROMPT_RATES.get(self.model, 0.005)
        completion_rate = self._COMPLETION_RATES.get(self.model, 0.015)
        self.estimated_cost_usd = (
            (self.prompt_tokens / 1000) * prompt_rate
            + (self.completion_tokens / 1000) * completion_rate
        )
        return round(self.estimated_cost_usd, 6)
