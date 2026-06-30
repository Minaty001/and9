"""
Phase 12 — Conscious Brain
===========================

LLM-powered reasoning, planning, coding, and summarization. Invokes
external language models via configurable providers (OpenAI, Anthropic,
local) with structured prompt templates, citation tracking, tool
provenance, retry logic, and cost estimation.

Components:
    - LLMClient: Provider-agnostic LLM invocation with retries
    - ReasoningEngine: Structured reasoning steps with chain-of-thought
    - PromptManager: Template-based prompt construction
    - ConsciousBrainService: ServiceBase wrapper
"""

from .llm_client import LLMClient, LLMResponse
from .reasoning_engine import ReasoningEngine, ReasoningStep
from .prompt_manager import PromptManager, PromptTemplate
from .service import ConsciousBrainService
from .config import ConsciousConfig
from .models import Citation, ToolCall, Provenance, UsageStats

__all__ = [
    "LLMClient",
    "LLMResponse",
    "ReasoningEngine",
    "ReasoningStep",
    "PromptManager",
    "PromptTemplate",
    "ConsciousBrainService",
    "ConsciousConfig",
    "Citation",
    "ToolCall",
    "Provenance",
    "UsageStats",
]
