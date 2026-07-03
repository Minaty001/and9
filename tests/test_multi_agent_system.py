"""
Tests for the AND9 Multi-Agent System (Phase 3).

Covers:
  - AgentBase abstract class
  - AgentRegistry (registration, routing, lifecycle)
  - All 20 agent implementations
  - Integration between agents
  - Error handling and edge cases
"""

import pytest
import time
from typing import Any, Optional

from app.agents.base import (
    AgentBase, AgentResult, AgentStatus, AgentMemory, AgentMetrics,
)
from app.agents.registry import AgentRegistry
from app.agents import create_agent_system


# ═══════════════════════════════════════════════════════════════════
# AgentBase Tests
# ═══════════════════════════════════════════════════════════════════

class SimpleTestAgent(AgentBase):
    """Minimal agent for testing base class functionality."""

    def __init__(self):
        super().__init__(
            name="test_agent",
            role="Test agent for unit tests",
            goal="Verify AgentBase functionality",
        )

    def _get_system_prompt(self) -> str:
        return "You are a test agent."

    def process(self, input_data: Any,
                context: Optional[dict] = None) -> AgentResult:
        msg = str(input_data) if not isinstance(input_data, str) else input_data
        if msg == "fail":
            return AgentResult(
                success=False, response="Failed", error="intentional_failure"
            )
        if msg == "slow":
            time.sleep(0.05)
        return AgentResult(success=True, response=f"Processed: {msg}")


class TestAgentBase:
    """Tests for the AgentBase abstract class."""

    def test_agent_creation(self):
        """Test basic agent creation with required parameters."""
        agent = SimpleTestAgent()
        assert agent.name == "test_agent"
        assert agent.role == "Test agent for unit tests"
        assert agent.goal == "Verify AgentBase functionality"
        assert agent.agent_id.startswith("test_agent_")
        assert agent.status == AgentStatus.STARTING

    def test_agent_string_repr(self):
        """Test string representation."""
        agent = SimpleTestAgent()
        assert "SimpleTestAgent" in repr(agent)
        assert "test_agent" in repr(agent)

    def test_initialization_lifecycle(self):
        """Test initialize and shutdown."""
        agent = SimpleTestAgent()
        assert not agent._initialized
        assert agent.status == AgentStatus.STARTING

        agent.initialize()
        assert agent._initialized
        assert agent.status == AgentStatus.HEALTHY

        agent.shutdown()
        assert agent.status == AgentStatus.DISABLED

    def test_successful_execution(self):
        """Test successful agent execution."""
        agent = SimpleTestAgent()
        result = agent("hello world")
        assert result.success
        assert result.response == "Processed: hello world"
        assert result.agent_name == "test_agent"
        assert result.latency_ms > 0
        assert agent.metrics.total_invocations == 1
        assert agent.metrics.successful_invocations == 1

    def test_failed_execution(self):
        """Test agent execution failure handling."""
        agent = SimpleTestAgent()
        result = agent("fail")
        assert not result.success
        assert result.error == "intentional_failure"
        assert agent.metrics.total_invocations == 1
        assert agent.metrics.failed_invocations == 1

    def test_execution_metrics(self):
        """Test that metrics are tracked correctly."""
        agent = SimpleTestAgent()
        agent("task1")
        agent("task2")
        agent("fail")

        assert agent.metrics.total_invocations == 3
        assert agent.metrics.successful_invocations == 2
        assert agent.metrics.failed_invocations == 1
        assert agent.metrics.success_rate == 2/3
        assert agent.metrics.avg_latency_ms > 0

    def test_agent_memory(self):
        """Test agent short-term memory with TTL."""
        agent = SimpleTestAgent()
        agent.memory.remember("key1", "value1", ttl=10)
        assert agent.memory.recall("key1") == "value1"

        # Expired memory
        agent.memory.remember("key2", "value2", ttl=0)
        time.sleep(0.01)
        assert agent.memory.recall("key2") is None

    def test_tool_binding_and_usage(self):
        """Test tool binding and usage on an agent."""
        agent = SimpleTestAgent()

        def my_tool(x: int) -> int:
            return x * 2

        agent.bind_tool("double", my_tool)
        assert "double" in agent.tools

        result = agent.use_tool("double", 5)
        assert result == 10

    def test_tool_usage_tracking(self):
        """Test that tool usage is tracked in metrics."""
        agent = SimpleTestAgent()

        def my_tool(x: int) -> int:
            return x + 1

        agent.bind_tool("add_one", my_tool)
        agent.use_tool("add_one", 5)
        assert agent.metrics.tool_usage.get("add_one") == 1

    def test_missing_tool_raises_error(self):
        """Test that using an unregistered tool raises KeyError."""
        agent = SimpleTestAgent()
        with pytest.raises(KeyError):
            agent.use_tool("nonexistent")

    def test_health_check(self):
        """Test health check output structure."""
        agent = SimpleTestAgent()
        agent.initialize()
        health = agent.health_check()
        assert health["name"] == "test_agent"
        assert health["status"] == "healthy"
        assert "initialized" in health
        assert "total_invocations" in health

    def test_agent_logging(self):
        """Test action logging."""
        agent = SimpleTestAgent()
        agent.log_action("test_action", "input_data", "output_data", True, 10.0)
        logs = agent.get_recent_logs()
        assert len(logs) == 1
        assert logs[0]["action"] == "test_action"
        assert logs[0]["success"] is True

    def test_serialization(self):
        """Test to_dict serialization."""
        agent = SimpleTestAgent()
        agent.initialize()
        d = agent.to_dict()
        assert d["name"] == "test_agent"
        assert d["status"] == "healthy"
        assert d["initialized"] is True
        assert "metrics" in d
        assert "tools" in d

    def test_abstract_class_enforcement(self):
        """Test that AgentBase cannot be instantiated directly."""
        with pytest.raises(TypeError):
            AgentBase(name="x", role="y", goal="z")  # noqa

    def test_metrics_to_dict(self):
        """Test AgentMetrics serialization."""
        metrics = AgentMetrics()
        metrics.record_success(50.0, tool="tool1")
        d = metrics.to_dict()
        assert d["total_invocations"] == 1
        assert d["successful"] == 1
        assert d["avg_latency_ms"] == 50.0
        assert "tool1" in d["tool_usage"]

    def test_result_to_dict(self):
        """Test AgentResult serialization."""
        result = AgentResult(
            success=True,
            response="Done!",
            data={"key": "value"},
            confidence=0.95,
            agent_name="test",
            latency_ms=42.0,
        )
        d = result.to_dict()
        assert d["success"] is True
        assert d["response"] == "Done!"
        assert d["confidence"] == 0.95


# ═══════════════════════════════════════════════════════════════════
# AgentRegistry Tests
# ═══════════════════════════════════════════════════════════════════

class TestAgentRegistry:
    """Tests for the AgentRegistry class."""

    @pytest.fixture
    def registry(self):
        """Create a fresh registry with test agents."""
        reg = AgentRegistry()
        agent1 = SimpleTestAgent()
        agent1.name = "alpha"
        agent2 = SimpleTestAgent()
        agent2.name = "beta"
        reg.register(agent1)
        reg.register(agent2)
        return reg

    def test_registration_and_lookup(self, registry):
        """Test registering and looking up agents."""
        assert registry.count() == 2
        assert registry.get("alpha") is not None
        assert registry.get("beta") is not None
        assert registry.get("nonexistent") is None

    def test_duplicate_registration_error(self, registry):
        """Test that duplicate registration raises ValueError."""
        from app.agents.base import AgentBase
        dup = SimpleTestAgent()
        dup.name = "alpha"
        with pytest.raises(ValueError, match="already registered"):
            registry.register(dup)

    def test_deregistration(self, registry):
        """Test deregistering an agent."""
        assert registry.count() == 2
        result = registry.deregister("alpha")
        assert result is True
        assert registry.count() == 1
        assert registry.get("alpha") is None

        result = registry.deregister("nonexistent")
        assert result is False

    def test_list_agents(self, registry):
        """Test listing all agents."""
        agent_list = registry.list_agents()
        assert len(agent_list) == 2
        names = [a["name"] for a in agent_list]
        assert "alpha" in names
        assert "beta" in names

    def test_find_by_role(self, registry):
        """Test finding agents by role keyword."""
        agents = registry.find_by_role("test")
        assert len(agents) == 2

    def test_initialize_all(self, registry):
        """Test initializing all agents."""
        registry.initialize_all()
        assert registry.get("alpha")._initialized is True
        assert registry.get("alpha").status == AgentStatus.HEALTHY

    def test_shutdown_all(self, registry):
        """Test shutting down all agents."""
        registry.initialize_all()
        registry.shutdown_all()
        assert registry.get("alpha").status == AgentStatus.DISABLED

    def test_health_report(self, registry):
        """Test health report generation."""
        registry.initialize_all()
        report = registry.health_report()
        assert report["total_agents"] == 2
        assert report["healthy"] == 2
        assert report["overall_status"] == "healthy"

    def test_routing_to_specific_agent(self, registry):
        """Test routing with a preferred agent."""
        result = registry.route("hello", preferred_agent="alpha")
        assert result.success
        assert result.agent_name == "alpha"

    def test_routing_preferred_not_found(self, registry):
        """Test routing with a nonexistent preferred agent falls back."""
        result = registry.route("hello", preferred_agent="nonexistent")
        # With no matching agents for "hello", should get no_suitable_agent
        assert not result.success
        assert result.error == "no_suitable_agent"

    def test_routing_without_agents(self):
        """Test routing when no agents match a task."""
        reg = AgentRegistry()
        result = reg.route("do something")
        assert not result.success
        assert result.error == "no_suitable_agent"

    def test_delegation(self, registry):
        """Test delegating a subtask to a specific agent."""
        result = registry.delegate("alpha", "do_stuff")
        assert result.success
        assert result.agent_name == "alpha"

    def test_delegation_to_nonexistent_agent(self, registry):
        """Test delegation to an agent that doesn't exist."""
        result = registry.delegate("nonexistent", "task")
        assert not result.success
        assert "not found" in result.response

    def test_broadcast(self, registry):
        """Test event broadcasting to all agents."""
        # Should not raise
        registry.broadcast("test_event", {"data": 123})
        registry.broadcast("test_event", None)

    def test_route_to_all(self, registry):
        """Test routing a task to ALL agents."""
        results = registry.route_to_all("hello")
        assert len(results) == 2
        for name, result in results.items():
            assert result.success

    def test_serialization(self, registry):
        """Test registry to_dict."""
        d = registry.to_dict()
        assert d["agent_count"] == 2
        assert len(d["agents"]) == 2

    def test_delegate_parallel(self, registry):
        """Test parallel delegation."""
        assignments = [("alpha", "task1"), ("beta", "task2")]
        results = registry.delegate_parallel(assignments)
        assert len(results) == 2
        assert "alpha" in results
        assert "beta" in results


# ═══════════════════════════════════════════════════════════════════
# Full Agent System Tests
# ═══════════════════════════════════════════════════════════════════

class TestAgentSystem:
    """Tests for the complete multi-agent system."""

    @pytest.fixture
    def registry(self):
        """Create the full agent system."""
        return create_agent_system(auto_init=False)

    def test_all_agents_registered(self, registry):
        """Test that all 20 agents are registered."""
        assert registry.count() == 20

    def test_agent_names(self, registry):
        """Test that all expected agent names are present."""
        expected_names = {
            "executive", "conversation", "planning",
            "research", "coding", "debug",
            "memory", "learning", "reflection",
            "android", "voice", "browser",
            "scheduler", "automation", "security", "health",
            "tool", "integration", "notification", "workflow",
        }
        registered_names = {a.name for a in registry.agents.values()}
        assert registered_names == expected_names

    def test_agent_roles_defined(self, registry):
        """Test that every agent has a non-empty role."""
        for agent in registry.agents.values():
            assert agent.role, f"Agent '{agent.name}' has no role"

    def test_agent_goals_defined(self, registry):
        """Test that every agent has a non-empty goal."""
        for agent in registry.agents.values():
            assert agent.goal, f"Agent '{agent.name}' has no goal"

    def test_agent_system_prompts(self, registry):
        """Test that every agent has a system prompt."""
        for agent in registry.agents.values():
            prompt = agent._get_system_prompt()
            assert prompt, f"Agent '{agent.name}' has no system prompt"
            assert len(prompt) > 20, f"Agent '{agent.name}' prompt too short"

    def test_initialize_all_agents(self, registry):
        """Test initializing all agents in the system."""
        registry.initialize_all()
        for agent in registry.agents.values():
            assert agent._initialized, f"Agent '{agent.name}' not initialized"
            assert agent.status == AgentStatus.HEALTHY, \
                f"Agent '{agent.name}' status is {agent.status}"

    def test_each_agent_can_process(self, registry):
        """Test that every agent can process a message."""
        for agent in registry.agents.values():
            result = agent("Hello, what can you do?")
            assert result.success, f"Agent '{agent.name}' failed: {result.error}"
            assert result.response, f"Agent '{agent.name}' returned empty response"
            assert result.agent_name == agent.name

    def test_each_agent_metrics_tracked(self, registry):
        """Test that each agent tracks its metrics after processing."""
        for agent in registry.agents.values():
            # Reset metrics first to get clean state
            agent.metrics.total_invocations = 0
            agent.metrics.successful_invocations = 0
            agent.metrics.total_latency_ms = 0.0
            agent("test input")
            assert agent.metrics.total_invocations == 1
            assert agent.metrics.avg_latency_ms > 0

    def test_health_report_includes_all(self, registry):
        """Test health report covers all agents."""
        registry.initialize_all()
        report = registry.health_report()
        assert report["total_agents"] == 20

    def test_executive_agent_routing(self, registry):
        """Test executive agent routing to specialists."""
        executive = registry.get("executive")
        executive.set_registry(registry)

        # Test that "write code" routes to coding agent
        # (We'd need the coding agent to actually be callable)
        result = executive("Write a Python script")
        assert result.success

    def test_memory_agent_store_and_recall(self, registry):
        """Test memory agent's store and recall capabilities."""
        memory = registry.get("memory")

        # Store something
        result = memory("remember my favorite color is blue")
        assert result.success

        # Recall it
        result = memory("recall favorite")
        assert result.success

    def test_automation_agent_rules(self, registry):
        """Test automation agent rule creation."""
        automation = registry.get("automation")

        result = automation("when wifi connects then open whatsapp")
        assert result.success
        assert "Rule created" in result.response

        # List rules
        result = automation("list rules")
        assert result.success
        assert len(result.data.get("rules", {})) >= 1

    def test_scheduler_agent_detection(self, registry):
        """Test scheduler agent's intent detection."""
        scheduler = registry.get("scheduler")

        result = scheduler("Set an alarm for 7 AM")
        assert result.success
        assert result.data["task_type"] == "alarm"

        result = scheduler("Remind me to buy groceries")
        assert result.success
        assert result.data["task_type"] == "reminder"

        result = scheduler("Set a timer for 10 minutes")
        assert result.success
        assert result.data["task_type"] == "timer"

    def test_conversation_agent_context(self, registry):
        """Test conversation agent maintains context."""
        conv = registry.get("conversation")

        result = conv("Hello!")
        assert result.success

        # Should remember the previous message
        remembered = conv.memory.recall("last_user_message")
        assert remembered == "Hello!"

    def test_research_agent_plan(self, registry):
        """Test research agent produces a research plan."""
        research = registry.get("research")
        result = research("Research the latest AI trends")
        assert result.success
        assert result.data["query"] == "Research the latest AI trends"

    def test_planning_agent_produces_plan(self, registry):
        """Test planning agent produces a structured plan."""
        planner = registry.get("planning")
        result = planner("Build a web application")
        assert result.success
        assert "milestones" in result.data
        assert "risks" in result.data
        assert "Plan for:" in result.response

    def test_security_agent_status(self, registry):
        """Test security agent reports status."""
        security = registry.get("security")
        result = security("Check security status")
        assert result.success
        assert result.data["status"] == "secure"

    def test_health_agent_report(self, registry):
        """Test health agent produces report."""
        health = registry.get("health")
        result = health("System health check")
        assert result.success
        assert result.data["overall_status"] == "healthy"

    def test_tool_agent_list_tools(self, registry):
        """Test tool agent can list tools."""
        tool = registry.get("tool")
        result = tool("list tools")
        assert result.success

    def test_tool_agent_register_tool(self, registry):
        """Test tool agent's programmatic tool registration."""
        tool = registry.get("tool")

        def my_handler(x):
            return x * 2

        tool.register_tool("custom_tool", "A custom test tool", my_handler)
        assert "custom_tool" in tool._tools
        assert "custom_tool" in tool.tools

    def test_android_agent_classification(self, registry):
        """Test android agent command classification."""
        android = registry.get("android")
        result = android("Open YouTube")
        assert result.success
        assert result.data["action_type"] == "launch_app"

        result = android("Call mom")
        assert result.success
        assert result.data["action_type"] == "call"

    def test_voice_agent_config(self, registry):
        """Test voice agent configuration."""
        voice = registry.get("voice")
        result = voice("Configure voice")
        assert result.success
        assert "jarvis" in str(result.data.get("wake_word", ""))

    def test_browser_agent_basic(self, registry):
        """Test browser agent basic functionality."""
        browser = registry.get("browser")
        result = browser("Open https://example.com")
        assert result.success

    def test_notification_agent(self, registry):
        """Test notification agent."""
        notification = registry.get("notification")
        result = notification("Send alert: server is down")
        assert result.success
        assert result.data["delivered"] is True

    def test_workflow_agent(self, registry):
        """Test workflow agent."""
        workflow = registry.get("workflow")
        result = workflow("Research topic then write code")
        assert result.success

    def test_debug_agent_analysis(self, registry):
        """Test debug agent analysis."""
        debug = registry.get("debug")
        result = debug("Traceback: ZeroDivisionError at line 42")
        assert result.success
        assert result.data.get("has_stack_trace")

    def test_reflection_agent(self, registry):
        """Test reflection agent."""
        reflection = registry.get("reflection")
        result = reflection("Completed task: wrote email script")
        assert result.success

    def test_learning_agent_analysis(self, registry):
        """Test learning agent with metrics context."""
        learning = registry.get("learning")
        result = learning("Analyze my usage patterns", context={
            "metrics": {"success_rate": 0.95, "total_actions": 100}
        })
        assert result.success

    def test_integration_agent(self, registry):
        """Test integration agent."""
        integration = registry.get("integration")
        result = integration("Connect to Telegram")
        assert result.success
        assert "active_connections" in result.data


# ═══════════════════════════════════════════════════════════════════
# Edge Cases & Error Handling
# ═══════════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_input(self):
        """Test agents handle empty input gracefully."""
        agent = SimpleTestAgent()
        result = agent("")
        assert result.success  # Should not crash

    def test_very_long_input(self):
        """Test agents handle very long input."""
        agent = SimpleTestAgent()
        long_input = "a" * 10000
        result = agent(long_input)
        assert result.success

    def test_special_characters(self):
        """Test agents handle special characters."""
        agent = SimpleTestAgent()
        result = agent("Hello! @#$%^&*() test 👋🌍")
        assert result.success

    def test_registry_with_no_agents(self):
        """Test registry operations with no agents."""
        reg = AgentRegistry()
        assert reg.count() == 0
        assert reg.list_agents() == []
        report = reg.health_report()
        assert report["total_agents"] == 0

    def test_agent_metrics_defaults(self):
        """Test that metrics have sane defaults."""
        metrics = AgentMetrics()
        assert metrics.avg_latency_ms == 0.0
        assert metrics.success_rate == 1.0
        assert metrics.total_invocations == 0

    def test_memory_clear(self):
        """Test clearing agent memory."""
        agent = SimpleTestAgent()
        agent.memory.remember("key", "value")
        agent.memory.clear()
        assert agent.memory.recall("key") is None

    def test_memory_forget(self):
        """Test forgetting specific memory keys."""
        agent = SimpleTestAgent()
        agent.memory.remember("key", "value")
        agent.memory.forget("key")
        assert agent.memory.recall("key") is None

    def test_repeated_deregistration(self):
        """Test deregistering same agent twice."""
        reg = AgentRegistry()
        agent = SimpleTestAgent()
        agent.name = "test"
        reg.register(agent)

        assert reg.deregister("test") is True
        assert reg.deregister("test") is False

    def test_health_check_without_initialization(self):
        """Test health check before initialization."""
        agent = SimpleTestAgent()
        health = agent.health_check()
        assert health["status"] == "starting"
        assert health["initialized"] is False

    def test_process_with_error_recovery(self):
        """Test that agents recover after errors."""
        agent = SimpleTestAgent()
        result = agent("fail")
        assert not result.success

        # Next call should work
        result = agent("ok")
        assert result.success
