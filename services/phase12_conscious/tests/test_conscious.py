"""
Tests for Phase 12 — Conscious Brain.
"""

from __future__ import annotations

import pytest
import json
from typing import Any, Dict, List, Optional

from services.phase12_conscious.config import ConsciousConfig
from services.phase12_conscious.models import (
    Message, Role, Conversation, Citation, CitationType,
    ToolCall, Provenance, UsageStats, ReasoningStrategy,
)
from services.phase12_conscious.prompt_manager import (
    PromptManager, PromptTemplate,
)
from services.phase12_conscious.llm_client import (
    LLMClient, LLMResponse,
)
from services.phase12_conscious.reasoning_engine import (
    ReasoningEngine, ReasoningStep, ReasoningResult,
)
from services.phase12_conscious.service import ConsciousBrainService


# ── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def config() -> ConsciousConfig:
    return ConsciousConfig()


@pytest.fixture
def prompt_manager() -> PromptManager:
    return PromptManager()


# ── Models Tests ────────────────────────────────────────────────────


class TestModels:
    def test_message_creation(self):
        msg = Message(role=Role.USER, content="hello")
        assert msg.role == Role.USER
        assert msg.content == "hello"

    def test_conversation_basics(self):
        conv = Conversation(system_prompt="You are JARVIS.")
        conv.add_message(Role.USER, "Hello")
        conv.add_message(Role.ASSISTANT, "Hi")
        assert len(conv.messages) == 2
        assert conv.messages[0].content == "Hello"
        assert conv.messages[1].role == Role.ASSISTANT

    def test_token_estimate(self):
        conv = Conversation(system_prompt="test " * 100)
        conv.add_message(Role.USER, "hello world " * 50)
        est = conv.total_tokens_estimate()
        assert est > 0

    def test_usage_cost_calculation(self):
        usage = UsageStats(
            prompt_tokens=1000,
            completion_tokens=500,
            provider="openai",
            model="gpt-4o",
        )
        cost = usage.calculate_cost()
        # (1000/1000)*0.0025 + (500/1000)*0.01 = 0.0025 + 0.005 = 0.0075
        assert cost == 0.0075
        assert usage.estimated_cost_usd == 0.0075

    def test_usage_local_no_cost(self):
        usage = UsageStats(
            prompt_tokens=1000,
            completion_tokens=500,
            provider="local",
            model="local",
        )
        cost = usage.calculate_cost()
        assert cost == 0.0

    def test_citation_creation(self):
        cit = Citation(
            source_id="doc1",
            source_type=CitationType.MEMORY,
            excerpt="important info",
            relevance=0.95,
        )
        assert cit.source_id == "doc1"
        assert cit.relevance == 0.95

    def test_tool_call_provenance(self):
        tc = ToolCall(tool_name="search", arguments={"q": "test"}, duration_ms=150.0)
        assert tc.tool_name == "search"
        assert tc.arguments["q"] == "test"
        assert tc.success is True

    def test_provenance_accumulation(self):
        prov = Provenance()
        prov.tool_calls.append(ToolCall(tool_name="t1"))
        prov.citations.append(Citation(source_id="s1", source_type=CitationType.WEB, excerpt="e"))
        prov.reasoning_steps.append("Step 1")
        assert len(prov.tool_calls) == 1
        assert len(prov.citations) == 1
        assert len(prov.reasoning_steps) == 1

    def test_reasoning_strategy_enum(self):
        assert ReasoningStrategy.CHAIN_OF_THOUGHT.value == "chain_of_thought"
        assert ReasoningStrategy.DIRECT.value == "direct"


# ── Prompt Manager Tests ────────────────────────────────────────────


class TestPromptManager:
    def test_default_templates(self, prompt_manager):
        templates = prompt_manager.list_templates()
        names = {t["name"] for t in templates}
        assert "reasoning" in names
        assert "planning" in names
        assert "coding" in names
        assert "summarization" in names

    def test_build_reasoning(self, prompt_manager):
        conv = prompt_manager.build_reasoning("What is the weather?")
        assert conv is not None
        assert len(conv.messages) == 1
        assert conv.messages[0].role == Role.USER
        assert "weather" in conv.messages[0].content

    def test_build_planning(self, prompt_manager):
        conv = prompt_manager.build_planning(
            "Build a website",
            ["python", "flask"],
        )
        assert conv is not None
        assert "Build a website" in conv.messages[0].content
        assert "python" in conv.messages[0].content

    def test_build_coding(self, prompt_manager):
        conv = prompt_manager.build_coding(
            "Write a function",
            language="python",
            constraints="async only",
        )
        assert conv is not None
        assert "Write a function" in conv.messages[0].content
        assert "async" in conv.messages[0].content

    def test_build_summarization(self, prompt_manager):
        conv = prompt_manager.build_summarization("Long text here...", "key points", 100)
        assert conv is not None
        assert "Long text here" in conv.messages[0].content
        assert "100" in conv.messages[0].content

    def test_custom_template_registration(self, prompt_manager):
        tpl = PromptTemplate(
            name="custom_test",
            system_template="You are a {role}.",
            user_template="{query}",
            expected_variables=["role", "query"],
            tags=["test"],
        )
        prompt_manager.register(tpl)
        assert prompt_manager.get("custom_test") is not None

        conv = prompt_manager.build("custom_test", role="helper", query="hi")
        assert conv is not None
        assert "helper" in conv.system_prompt
        assert "hi" in conv.messages[0].content

    def test_unknown_template(self, prompt_manager):
        conv = prompt_manager.build("nonexistent")
        assert conv is None

    def test_template_validation_empty(self):
        tpl = PromptTemplate(name="empty", system_template="", user_template="")
        issues = tpl.validate()
        assert len(issues) > 0

    def test_fallback_on_missing_variable(self, prompt_manager):
        tpl = PromptTemplate(
            name="missing_var",
            system_template="Hello {name}!",
            user_template="Query: {query}",
        )
        prompt_manager.register(tpl)
        # Missing 'name' shouldn't crash
        conv = prompt_manager.build("missing_var", query="test")
        assert conv is not None
        assert "Hello {name}!" in conv.system_prompt  # Falls back to literal


# ── LLM Client Tests ────────────────────────────────────────────────


class TestLLMClient:
    def test_initialization(self, config):
        client = LLMClient(config)
        assert client.initialize() is True
        assert client.get_usage_summary()["total_cost_usd"] == 0.0

    def test_usage_tracking(self, config):
        client = LLMClient(config)
        client.initialize()

        usage = UsageStats(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            provider="openai",
            model="gpt-4o",
        )
        usage.calculate_cost()
        client._track_usage(usage)

        summary = client.get_usage_summary()
        assert summary["total_prompt_tokens"] == 100
        assert summary["total_completion_tokens"] == 50
        assert summary["total_cost_usd"] > 0

    def test_reset_usage(self, config):
        client = LLMClient(config)
        client.initialize()
        usage = UsageStats(
            prompt_tokens=50, completion_tokens=25, total_tokens=75,
        )
        client._track_usage(usage)
        assert client.get_usage_summary()["total_prompt_tokens"] == 50
        client.reset_usage()
        assert client.get_usage_summary()["total_prompt_tokens"] == 0

    def test_build_messages(self, config):
        client = LLMClient(config)
        conv = Conversation(system_prompt="You are JARVIS.")
        conv.add_message(Role.USER, "Hello")
        conv.add_message(Role.ASSISTANT, "Hi there")

        messages = client._build_messages(conv)
        assert len(messages) == 3
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are JARVIS."
        assert messages[1]["role"] == "user"
        assert messages[2]["role"] == "assistant"

    def test_parse_openai_401(self, config):
        client = LLMClient(config)
        with pytest.raises(Exception) as exc:
            client._parse_openai_response(401, '{"error": "unauthorized"}')
        assert "API key" in str(exc.value)

    def test_parse_openai_429(self, config):
        client = LLMClient(config)
        with pytest.raises(Exception):
            client._parse_openai_response(429, "rate limited")

    def test_parse_openai_400(self, config):
        client = LLMClient(config)
        with pytest.raises(Exception):
            client._parse_openai_response(400, "bad request")

    def test_parse_openai_valid(self, config):
        client = LLMClient(config)
        resp_text = json.dumps({
            "choices": [{"message": {"content": "Hello!"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            "model": "gpt-4o",
        })
        resp = client._parse_openai_response(200, resp_text)
        assert resp.content == "Hello!"
        assert resp.usage.total_tokens == 15
        assert resp.finish_reason == "stop"

    def test_unknown_provider(self, config):
        bad_config = ConsciousConfig(provider="nonexistent")
        client = LLMClient(bad_config)
        client.initialize()

        # Check that the provider raises at _invoke_provider level
        with pytest.raises(Exception, match="Unknown provider"):
            import asyncio
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(client._invoke_provider(
                    [{"role": "user", "content": "test"}],
                    temperature=0.5,
                    max_tokens=100,
                ))
            finally:
                loop.close()


# ── Reasoning Engine Tests ──────────────────────────────────────────


class TestReasoningEngine:
    def test_initialization(self, config):
        client = LLMClient(config)
        pm = PromptManager()
        engine = ReasoningEngine(config, client, pm)
        assert engine is not None

    def test_parse_cot_steps_numbered(self, config):
        client = LLMClient(config)
        pm = PromptManager()
        engine = ReasoningEngine(config, client, pm)

        text = """Step 1: First I analyze the problem.
Step 2: Then I solve it.
Step 3: Finally I verify."""
        steps = engine._parse_cot_steps(text)
        assert len(steps) == 3
        assert "analyze" in steps[0][1]
        assert "solve" in steps[1][1]

    def test_parse_cot_steps_answer_split(self, config):
        client = LLMClient(config)
        pm = PromptManager()
        engine = ReasoningEngine(config, client, pm)

        text = """I analyze the problem carefully.
I consider multiple approaches.
Answer: The optimal solution is to use a binary search."""
        steps = engine._parse_cot_steps(text)
        # Should find Answer: split
        assert len(steps) >= 2
        assert any("Answer" in s[0] for s in steps)

    def test_parse_cot_steps_empty(self, config):
        client = LLMClient(config)
        pm = PromptManager()
        engine = ReasoningEngine(config, client, pm)
        steps = engine._parse_cot_steps("Just a simple answer with no structure.")
        assert len(steps) == 0

    def test_citation_extraction(self, config):
        client = LLMClient(config)
        pm = PromptManager()
        engine = ReasoningEngine(config, client, pm)

        text = "According to the docs [src:doc001], this is correct."
        citations = engine.extract_citations(text)
        assert len(citations) == 1
        assert citations[0].source_id == "doc001"

    def test_format_context(self, config):
        client = LLMClient(config)
        pm = PromptManager()
        engine = ReasoningEngine(config, client, pm)

        ctx = {"user": "Alice", "time": "morning"}
        formatted = engine._format_context(ctx)
        assert "Alice" in formatted
        assert "morning" in formatted

    def test_format_context_none(self, config):
        client = LLMClient(config)
        pm = PromptManager()
        engine = ReasoningEngine(config, client, pm)

        formatted = engine._format_context(None)
        assert formatted == "No additional context"


# ── Service Tests ───────────────────────────────────────────────────


class TestConsciousBrainService:
    @pytest.mark.asyncio
    async def test_initialize(self):
        service = ConsciousBrainService()
        ok = await service.initialize()
        assert ok is True
        assert service.is_initialized() is True

    @pytest.mark.asyncio
    async def test_shutdown(self):
        service = ConsciousBrainService()
        await service.initialize()
        await service.shutdown()
        assert service.is_initialized() is False

    @pytest.mark.asyncio
    async def test_health_before_init(self):
        service = ConsciousBrainService()
        health = await service.health()
        assert health["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_health_after_init(self):
        service = ConsciousBrainService()
        await service.initialize()
        health = await service.health()
        assert health["status"] == "healthy"
        assert health["service_name"] == "jarvis_conscious"
        assert health["version"] == "2.0.0"

    @pytest.mark.asyncio
    async def test_stats(self):
        service = ConsciousBrainService()
        await service.initialize()
        stats = await service.stats()
        assert stats["service"] == "jarvis_conscious"
        assert "usage" in stats
        assert "templates" in stats
        assert "metrics" in stats

    @pytest.mark.asyncio
    async def test_prompt_templates_registered(self):
        service = ConsciousBrainService()
        await service.initialize()
        templates = service.list_prompt_templates()
        names = {t["name"] for t in templates}
        assert "reasoning" in names
        assert "planning" in names
        assert "coding" in names
        assert "summarization" in names

    @pytest.mark.asyncio
    async def test_custom_template_registration(self):
        service = ConsciousBrainService()
        await service.initialize()
        service.register_prompt_template(
            name="custom",
            system="You are {role}.",
            user="{query}",
            description="Custom template",
            tags=["custom"],
        )
        templates = service.list_prompt_templates()
        names = {t["name"] for t in templates}
        assert "custom" in names

    @pytest.mark.asyncio
    async def test_reason_method_no_llm_no_crash(self):
        """reason() should gracefully handle LLM unavailability."""
        service = ConsciousBrainService()
        await service.initialize()
        # Without actual API key, this should log an error and return an error result
        result = await service.reason("What is the meaning of life?")
        assert isinstance(result, ReasoningResult)
        assert result.final_answer is not None
        # Should have at least one step (error handling)
        assert len(result.steps) > 0 or result.final_answer

    @pytest.mark.asyncio
    async def test_code_method(self):
        service = ConsciousBrainService()
        await service.initialize()
        result = await service.code("Write a hello world", language="python")
        assert isinstance(result, ReasoningResult)

    @pytest.mark.asyncio
    async def test_summarize_method(self):
        service = ConsciousBrainService()
        await service.initialize()
        result = await service.summarize("Long content here " * 100, "key points", 50)
        assert isinstance(result, ReasoningResult)

    @pytest.mark.asyncio
    async def test_ask_method(self):
        service = ConsciousBrainService()
        await service.initialize()
        # Should not crash without API key
        answer = await service.ask("Hello", system_prompt="Be helpful.")
        # Without API key, it will fail but return gracefully
        assert isinstance(answer, str)

    @pytest.mark.asyncio
    async def test_plan_method(self):
        service = ConsciousBrainService()
        await service.initialize()
        result = await service.plan(
            "Organize my schedule",
            ["calendar", "reminder"],
        )
        assert isinstance(result, ReasoningResult)

    @pytest.mark.asyncio
    async def test_double_initialize(self):
        service = ConsciousBrainService()
        await service.initialize()
        await service.initialize()  # Should not crash
        assert service.is_initialized() is True

    @pytest.mark.asyncio
    async def test_reasoning_result_accumulation(self):
        result = ReasoningResult(strategy=ReasoningStrategy.CHAIN_OF_THOUGHT)
        step1 = ReasoningStep(
            step_number=1, description="Step 1",
            strategy=ReasoningStrategy.CHAIN_OF_THOUGHT,
            output="Thinking...",
        )
        step2 = ReasoningStep(
            step_number=2, description="Step 2",
            strategy=ReasoningStrategy.CHAIN_OF_THOUGHT,
            output="Answer: 42",
        )
        result.add_step(step1)
        result.add_step(step2)
        assert len(result.steps) == 2
        assert len(result.provenance.reasoning_steps) == 2
        result.final_answer = "42"
        assert result.final_answer == "42"

    @pytest.mark.asyncio
    async def test_metrics_tracking(self):
        service = ConsciousBrainService()
        await service.initialize()
        await service.reason("test query")
        snap = service._metrics.snapshot()
        assert snap["counters"].get("reasoning_calls", 0) >= 1
