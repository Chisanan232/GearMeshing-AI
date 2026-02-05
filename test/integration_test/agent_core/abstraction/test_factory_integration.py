"""
Integration tests for AgentFactory with real adapters and MCP client.
"""

from collections.abc import AsyncGenerator
from typing import Any, cast
from unittest.mock import Mock

import pytest

from gearmeshing_ai.agent_core.abstraction.adapter import AgentAdapter
from gearmeshing_ai.agent_core.abstraction.cache import AgentCache
from gearmeshing_ai.agent_core.abstraction.factory import AgentFactory
from gearmeshing_ai.agent_core.abstraction.mcp import MCPClientAbstraction
from gearmeshing_ai.agent_core.abstraction.settings import AgentSettings, ModelSettings


class ConcreteAgentAdapter(AgentAdapter):
    """Concrete implementation of AgentAdapter for integration testing."""

    def __init__(self) -> None:
        self.created_agents: list[Any] = []
        self.run_calls: list[tuple[Any, str, dict[str, Any]]] = []
        self.run_stream_calls: list[tuple[Any, str, dict[str, Any]]] = []

    def create_agent(self, settings: AgentSettings, tools: list[Any]) -> Any:
        agent = ConcreteAgent(settings, tools)
        self.created_agents.append(agent)
        return agent

    async def run(self, agent: Any, prompt: str, **kwargs: Any) -> Any:
        self.run_calls.append((agent, prompt, kwargs))
        return f"Response from {agent.settings.role}: {prompt}"

    async def run_stream(self, agent: Any, prompt: str, **kwargs: Any) -> AsyncGenerator[str, None]:  # type: ignore[override]
        self.run_stream_calls.append((agent, prompt, kwargs))
        yield f"Chunk 1 from {agent.settings.role}: {prompt}"
        yield f"Chunk 2 from {agent.settings.role}: {prompt}"


class ConcreteAgent:
    """Concrete agent implementation for testing."""

    def __init__(self, settings: AgentSettings, tools: list[Any]) -> None:
        self.settings = settings
        self.tools = tools
        self.execution_history: list[Any] = []

    def __repr__(self) -> str:
        return f"ConcreteAgent(role={self.settings.role}, tools={len(self.tools)})"


class ConcreteMCPClient(MCPClientAbstraction):
    """Concrete implementation of MCPClientAbstraction for integration testing."""

    def __init__(self, tools_registry: dict[str, Any] | None = None) -> None:
        self.tools_registry = tools_registry or {}
        self.get_tools_history: list[list[str]] = []
        self.connection_count = 0

    async def get_tools(self, tool_names: list[str]) -> list[Any]:
        self.get_tools_history.append(tool_names)
        self.connection_count += 1

        tools = []
        for name in tool_names:
            if name in self.tools_registry:
                tools.append(self.tools_registry[name])
            else:
                # Create a mock tool for unknown names
                tool = Mock(name=f"MCPTool_{name}")
                tool.name = name
                tool.description = f"Mock MCP tool: {name}"
                tools.append(tool)

        return tools


@pytest.mark.asyncio
class TestAgentFactoryIntegration:
    """Integration tests for AgentFactory with concrete implementations."""

    @pytest.fixture  # type: ignore[untyped-decorator]
    def adapter(self) -> ConcreteAgentAdapter:
        """Fixture providing a concrete adapter."""
        return ConcreteAgentAdapter()

    @pytest.fixture  # type: ignore[untyped-decorator]
    def tools_registry(self) -> dict[str, Any]:
        """Fixture providing a tools registry for MCP client."""
        tools: dict[str, Any] = {}
        for name in ["calculator", "weather", "database"]:
            tool = Mock(name=name, spec=["calculate", "get_weather", "query"])
            tool.name = name
            tool.description = f"Mock MCP tool: {name}"
            tools[name] = tool

        return tools

    @pytest.fixture  # type: ignore[untyped-decorator]
    def mcp_client(self, tools_registry: dict[str, Any]) -> ConcreteMCPClient:
        """Fixture providing a concrete MCP client."""
        return ConcreteMCPClient(tools_registry)

    @pytest.fixture  # type: ignore[untyped-decorator]
    def factory(self, adapter: ConcreteAgentAdapter, mcp_client: ConcreteMCPClient) -> AgentFactory:
        """Fixture providing an AgentFactory with concrete implementations."""
        return AgentFactory(adapter, mcp_client)

    @pytest.fixture  # type: ignore[untyped-decorator]
    def sample_model_settings(self) -> ModelSettings:
        """Fixture providing sample model settings."""
        return ModelSettings(
            customized_name="gpt-4-config", provider="openai", model="gpt-4", temperature=0.7, max_tokens=2048
        )

    @pytest.fixture  # type: ignore[untyped-decorator]
    def sample_agent_settings(self, sample_model_settings: ModelSettings) -> AgentSettings:
        """Fixture providing sample agent settings."""
        return AgentSettings(
            role="assistant",
            description="A helpful AI assistant",
            model_settings=sample_model_settings,
            tools=["calculator", "weather"],
            system_prompt="You are a helpful assistant.",
            metadata={"version": "1.0", "category": "general"},
        )

    def test_factory_with_concrete_implementations(
        self, factory: AgentFactory, adapter: ConcreteAgentAdapter, mcp_client: ConcreteMCPClient
    ) -> None:
        """Test factory initialization with concrete implementations."""
        assert factory.adapter is adapter
        assert factory.mcp_client is mcp_client
        assert isinstance(factory.cache, AgentCache)
        assert factory._agent_settings_registry == {}
        assert factory._model_settings_registry == {}

    async def test_complete_agent_creation_workflow(
        self, factory: AgentFactory, sample_agent_settings: AgentSettings
    ) -> None:
        """Test complete agent creation workflow with concrete implementations."""
        # Clear cache to ensure fresh creation
        factory.cache.clear()

        # Register agent settings
        factory.register_agent_settings(sample_agent_settings)

        # Create agent
        agent = await factory.get_or_create_agent("assistant")

        # Verify agent creation
        assert isinstance(agent, ConcreteAgent)
        assert agent.settings is sample_agent_settings
        assert len(agent.tools) == 2  # calculator and weather

        # Verify adapter was called
        assert len(cast(ConcreteAgentAdapter, factory.adapter).created_agents) == 1
        assert cast(ConcreteAgentAdapter, factory.adapter).created_agents[0] is agent

        # Verify MCP client was called
        assert len(cast(ConcreteMCPClient, factory.mcp_client).get_tools_history) == 1
        assert cast(ConcreteMCPClient, factory.mcp_client).get_tools_history[0] == ["calculator", "weather"]

    async def test_agent_execution_workflow(self, factory: AgentFactory, sample_agent_settings: AgentSettings) -> None:
        """Test agent execution workflow with concrete implementations."""
        # Register and create agent
        factory.register_agent_settings(sample_agent_settings)
        agent = await factory.get_or_create_agent("assistant")

        # Test run execution
        response = await factory.adapter.run(agent, "What is 2+2?")

        assert "Response from assistant: What is 2+2?" in response
        assert len(cast(ConcreteAgentAdapter, factory.adapter).run_calls) == 1
        assert cast(ConcreteAgentAdapter, factory.adapter).run_calls[0][0] is agent
        assert cast(ConcreteAgentAdapter, factory.adapter).run_calls[0][1] == "What is 2+2?"

    async def test_agent_streaming_workflow(self, factory: AgentFactory, sample_agent_settings: AgentSettings) -> None:
        """Test agent streaming workflow with concrete implementations."""
        # Register and create agent
        factory.register_agent_settings(sample_agent_settings)
        agent = await factory.get_or_create_agent("assistant")

        # Test streaming execution
        chunks = []
        stream_coro = factory.adapter.run_stream(agent, "Tell me a story")
        async for chunk in stream_coro:  # type: ignore[attr-defined]
            chunks.append(chunk)

        assert len(chunks) == 2
        assert all("assistant" in chunk for chunk in chunks)
        assert len(cast(ConcreteAgentAdapter, factory.adapter).run_stream_calls) == 1

    async def test_factory_caching_with_concrete_agents(
        self, factory: AgentFactory, sample_agent_settings: AgentSettings
    ) -> None:
        """Test agent caching behavior with concrete agents."""
        # Clear cache to start fresh
        factory.cache.clear()

        # Register settings
        factory.register_agent_settings(sample_agent_settings)

        # Create agent multiple times
        agent1 = await factory.get_or_create_agent("assistant")
        agent2 = await factory.get_or_create_agent("assistant")
        agent3 = await factory.get_or_create_agent("assistant")

        # Verify caching
        assert agent1 is agent2
        assert agent2 is agent3

        # Verify only one agent was created
        assert len(cast(ConcreteAgentAdapter, factory.adapter).created_agents) == 1
        assert len(cast(ConcreteMCPClient, factory.mcp_client).get_tools_history) == 1

    async def test_factory_with_multiple_agents(
        self, factory: AgentFactory, sample_model_settings: ModelSettings
    ) -> None:
        """Test factory with multiple different agents."""
        # Clear cache to ensure fresh creation
        factory.cache.clear()

        # Create different agent settings
        assistant_settings = AgentSettings(
            role="assistant",
            description="General assistant",
            model_settings=sample_model_settings,
            tools=["calculator"],
        )

        analyst_settings = AgentSettings(
            role="analyst",
            description="Data analyst",
            model_settings=sample_model_settings,
            tools=["database", "calculator"],
        )

        # Register both agents
        factory.register_agent_settings(assistant_settings)
        factory.register_agent_settings(analyst_settings)

        # Create both agents
        assistant = await factory.get_or_create_agent("assistant")
        analyst = await factory.get_or_create_agent("analyst")

        # Verify different agents
        assert assistant is not analyst
        assert assistant.settings.role == "assistant"
        assert analyst.settings.role == "analyst"
        assert len(assistant.tools) == 1
        assert len(analyst.tools) == 2

    async def test_factory_override_settings_workflow(
        self, factory: AgentFactory, sample_agent_settings: AgentSettings
    ) -> None:
        """Test factory workflow with override settings."""
        # Register base settings
        factory.register_agent_settings(sample_agent_settings)

        # Create agent with overrides
        overrides = {
            "description": "Overridden description",
            "system_prompt": "Overridden system prompt",
            "model_settings": {"temperature": 0.3, "max_tokens": 1024},
        }

        agent = await factory.get_or_create_agent("assistant", overrides)

        # Verify overrides were applied
        assert agent.settings.description == "Overridden description"
        assert agent.settings.system_prompt == "Overridden system prompt"

        # Check model_settings (handle both ModelSettings and dict)
        model_settings = agent.settings.model_settings
        if isinstance(model_settings, ModelSettings):
            assert model_settings.temperature == 0.3
            assert model_settings.max_tokens == 1024
            assert model_settings.provider == "openai"
        else:
            # If it's a dict due to mock behavior
            assert model_settings.get("temperature") == 0.3
            assert model_settings.get("max_tokens") == 1024
            # The provider field should be preserved from the original
            assert model_settings.get("provider", "openai") == "openai"

    async def test_factory_error_handling_workflow(self, factory: AgentFactory) -> None:
        """Test factory error handling with concrete implementations."""
        # Try to create agent without registering settings
        with pytest.raises(ValueError, match="No agent settings registered for role"):
            await factory.get_or_create_agent("nonexistent")

    async def test_mcp_client_error_propagation(
        self, factory: AgentFactory, sample_agent_settings: AgentSettings
    ) -> None:
        """Test that MCP client errors are properly propagated."""
        # Clear cache to ensure fresh creation
        factory.cache.clear()

        # Create MCP client that fails
        class FailingMCPClient(MCPClientAbstraction):
            async def get_tools(self, tool_names: list[str]) -> list[Any]:
                msg = "MCP server unavailable"
                raise RuntimeError(msg)

        factory.mcp_client = FailingMCPClient()
        factory.register_agent_settings(sample_agent_settings)

        # Should propagate MCP error
        with pytest.raises(RuntimeError, match="MCP server unavailable"):
            await factory.get_or_create_agent("assistant")

    async def test_factory_without_mcp_client(self, adapter: ConcreteAgentAdapter) -> None:
        """Test factory workflow without MCP client."""
        factory = AgentFactory(adapter)  # No MCP client

        # Register settings without tools
        model_settings = ModelSettings(customized_name="test-model", provider="openai", model="gpt-4")
        agent_settings = AgentSettings(
            role="simple-agent",
            description="Simple agent without tools",
            model_settings=model_settings,
            tools=[],  # No tools
        )

        factory.register_agent_settings(agent_settings)

        # Create agent (should work without MCP client)
        agent = await factory.get_or_create_agent("simple-agent")

        assert isinstance(agent, ConcreteAgent)
        assert len(agent.tools) == 0

    async def test_concurrent_agent_creation(self, factory: AgentFactory, sample_agent_settings: AgentSettings) -> None:
        """Test concurrent agent creation with concrete implementations."""
        factory.register_agent_settings(sample_agent_settings)

        import asyncio

        async def create_agents_concurrently() -> list[Any]:
            tasks = []
            for _i in range(5):
                task = factory.get_or_create_agent("assistant")
                tasks.append(task)

            return await asyncio.gather(*tasks)

        agents = await create_agents_concurrently()

        # All agents should be the same (cached)
        assert all(agent is agents[0] for agent in agents)
        assert len(cast(ConcreteAgentAdapter, factory.adapter).created_agents) == 1

    async def test_factory_state_isolation(self, adapter: ConcreteAgentAdapter, mcp_client: ConcreteMCPClient) -> None:
        """Test that factory instances maintain isolated state."""
        factory1 = AgentFactory(adapter, mcp_client)
        factory2 = AgentFactory(adapter, mcp_client)

        # Register different settings in each factory
        model_settings = ModelSettings(customized_name="test-model", provider="openai", model="gpt-4")

        agent1_settings = AgentSettings(role="agent1", description="Agent 1", model_settings=model_settings)

        agent2_settings = AgentSettings(role="agent2", description="Agent 2", model_settings=model_settings)

        factory1.register_agent_settings(agent1_settings)
        factory2.register_agent_settings(agent2_settings)

        # Create agents from each factory
        agent1 = await factory1.get_or_create_agent("agent1")
        agent2 = await factory2.get_or_create_agent("agent2")

        # Verify isolation
        assert agent1.settings.role == "agent1"
        assert agent2.settings.role == "agent2"
        assert factory1.get_agent_settings("agent1") is not None
        assert factory1.get_agent_settings("agent2") is None
        assert factory2.get_agent_settings("agent2") is not None
        assert factory2.get_agent_settings("agent1") is None

    async def test_complete_workflow_with_tools_execution(
        self, factory: AgentFactory, sample_agent_settings: AgentSettings
    ) -> None:
        """Test complete workflow including tool execution simulation."""
        # Clear cache to ensure fresh creation with tools
        factory.cache.clear()

        factory.register_agent_settings(sample_agent_settings)

        # Create agent
        agent = await factory.get_or_create_agent("assistant")

        # Verify tools were properly fetched and attached
        assert len(agent.tools) == 2
        tool_names = [tool.name for tool in agent.tools if hasattr(tool, "name")]
        assert "calculator" in tool_names
        assert "weather" in tool_names

        # Simulate tool usage
        calculator_tool = agent.tools[0]
        if hasattr(calculator_tool, "calculate"):
            calculator_tool.calculate.return_value = 42

        # Execute agent with tool usage
        response = await factory.adapter.run(agent, "Calculate 2*2")

        assert "Response from assistant" in response
        assert len(cast(ConcreteAgentAdapter, factory.adapter).run_calls) == 1

    def test_factory_configuration_validation(
        self, adapter: ConcreteAgentAdapter, mcp_client: ConcreteMCPClient
    ) -> None:
        """Test factory configuration validation."""
        # Test with valid configuration
        factory = AgentFactory(adapter, mcp_client)
        assert factory.adapter is adapter
        assert factory.mcp_client is mcp_client

        # Test with None adapter (should still work)
        factory = AgentFactory(cast(ConcreteAgentAdapter, None), mcp_client)
        assert factory.adapter is None

        # Test with None MCP client (should still work)
        factory = AgentFactory(adapter, None)
        assert factory.mcp_client is None

        # Test with both None
        factory = AgentFactory(None, None)
        assert factory.adapter is None
        assert factory.mcp_client is None
