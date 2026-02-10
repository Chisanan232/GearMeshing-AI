"""
Smoke tests for the agent.abstraction module that call real AI models.

These tests focus specifically on verifying the abstraction layer works with
real AI model calls. Non-AI tests are moved to unit tests.
"""

from typing import Any
from unittest.mock import Mock

import pytest

# Import abstraction components
from gearmeshing_ai.agent.abstraction import (
    AgentAdapter,
    AgentCache,
    AgentFactory,
    AgentSettings,
    MCPClientAbstraction,
    ModelSettings,
)

# Import concrete adapter implementation
from gearmeshing_ai.agent.adapters.pydantic_ai import PydanticAIAdapter

# Import test settings
from test.settings import test_settings


class MockMCPClient(MCPClientAbstraction):
    """Mock MCP client for testing."""

    def __init__(self, tools_data: list[Any] | None = None) -> None:
        self.tools_data = tools_data or []
        self.get_tools_call_count = 0

    async def get_tools(self, tool_names: list[str]) -> list[Any]:
        """Mock tool retrieval."""
        self.get_tools_call_count += 1
        # Return mock tools for requested names with proper name attribute
        tools = []
        for name in tool_names:
            mock_tool = Mock()
            mock_tool.name = name  # Set the name attribute directly
            tools.append(mock_tool)
        return tools

    async def discover_tools_for_agent(self) -> Any:
        """Mock tool discovery for agent."""
        # Return a simple mock catalog
        from gearmeshing_ai.agent.models.actions import MCPToolCatalog, MCPToolInfo

        tools_info = []
        for tool_data in self.tools_data:
            if isinstance(tool_data, dict):
                tool_info = MCPToolInfo(
                    name=tool_data.get("name", "unknown"),
                    description=tool_data.get("description", "Mock tool"),
                    mcp_server=tool_data.get("mcp_server", "test-server"),
                    parameters=tool_data.get("parameters", {}),
                    returns=tool_data.get("returns"),
                    example_usage=tool_data.get("example_usage", f"Use {tool_data.get('name', 'unknown')}"),
                )
                tools_info.append(tool_info)

        return MCPToolCatalog(tools=tools_info)

    async def execute_proposed_tool(self, tool_name: str, parameters: dict) -> dict:
        """Mock tool execution."""
        return {
            "success": True,
            "data": f"Mock result from {tool_name}",
            "tool_used": tool_name,
            "parameters": parameters,
        }


class TestAgentAdapterSmoke:
    """Smoke tests for the AgentAdapter with real AI model calls."""

    def test_adapter_is_abstract(self) -> None:
        """Test that AgentAdapter cannot be instantiated directly."""
        with pytest.raises(TypeError):
            AgentAdapter()  # type: ignore[abstract]

    def test_concrete_adapter_implementation(self) -> None:
        """Test that PydanticAIAdapter is a valid implementation."""
        adapter = PydanticAIAdapter()
        assert isinstance(adapter, AgentAdapter)
        assert hasattr(adapter, "create_agent")
        assert hasattr(adapter, "run")
        assert hasattr(adapter, "run_stream")

    @pytest.mark.asyncio  # type: ignore[untyped-decorator]
    @pytest.mark.ai_test  # type: ignore[untyped-decorator]
    @pytest.mark.openai  # type: ignore[untyped-decorator]
    async def test_adapter_create_agent_openai(self) -> None:
        """Test agent creation through adapter with OpenAI."""
        adapter = PydanticAIAdapter()

        # Create test settings
        model_settings = ModelSettings(
            customized_name="test_openai",
            provider="openai",
            model="gpt-4",
            api_key=test_settings.ai_provider.openai.api_key,
        )

        agent_settings = AgentSettings(
            role="test_role",
            description="Test agent",
            model_settings=model_settings,
            system_prompt="You are a test assistant.",
        )

        # Skip if no OpenAI API key
        if not test_settings.has_provider("openai"):
            pytest.skip("OpenAI API key not available")

        # Create agent
        agent = adapter.create_agent(agent_settings, [])
        assert agent is not None

        # Verify agent type
        from pydantic_ai import Agent as PydanticAgent

        assert isinstance(agent, PydanticAgent)

    @pytest.mark.asyncio  # type: ignore[untyped-decorator]
    @pytest.mark.ai_test  # type: ignore[untyped-decorator]
    @pytest.mark.openai  # type: ignore[untyped-decorator]
    async def test_adapter_run_agent_openai(self) -> None:
        """Test running agent through adapter with OpenAI."""
        adapter = PydanticAIAdapter()

        # Create test settings
        model_settings = ModelSettings(
            customized_name="test_openai",
            provider="openai",
            model="gpt-4",
            api_key=test_settings.ai_provider.openai.api_key,
            max_tokens=50,  # Limit tokens for testing
        )

        agent_settings = AgentSettings(
            role="test_role",
            description="Test agent",
            model_settings=model_settings,
            system_prompt="You are a test assistant. Respond briefly with 'Hello, test!'",
        )

        # Skip if no OpenAI API key or AI tests disabled
        if not test_settings.run_ai_tests or not test_settings.has_provider("openai"):
            pytest.skip("OpenAI API key not available or AI tests disabled")

        # Create and run agent
        agent = adapter.create_agent(agent_settings, [])
        response = await adapter.run(agent, "Say hello")

        # Verify response
        assert response is not None
        assert isinstance(response, str)
        assert len(response) > 0

    @pytest.mark.asyncio  # type: ignore[untyped-decorator]
    @pytest.mark.ai_test  # type: ignore[untyped-decorator]
    @pytest.mark.openai  # type: ignore[untyped-decorator]
    async def test_adapter_stream_agent_openai(self) -> None:
        """Test streaming agent through adapter with OpenAI."""
        adapter = PydanticAIAdapter()

        # Create test settings
        model_settings = ModelSettings(
            customized_name="test_openai",
            provider="openai",
            model="gpt-4",
            api_key=test_settings.ai_provider.openai.api_key,
            max_tokens=50,  # Limit tokens for testing
        )

        agent_settings = AgentSettings(
            role="test_role",
            description="Test agent",
            model_settings=model_settings,
            system_prompt="You are a test assistant. Count from 1 to 3.",
        )

        # Skip if no OpenAI API key or AI tests disabled
        if not test_settings.run_ai_tests or not test_settings.has_provider("openai"):
            pytest.skip("OpenAI API key not available or AI tests disabled")

        # Create and stream agent
        agent = adapter.create_agent(agent_settings, [])
        response_chunks = []

        async for chunk in adapter.run_stream(agent, "Count to 3"):
            assert isinstance(chunk, str)
            response_chunks.append(chunk)

        # Verify streaming response
        assert len(response_chunks) > 0
        full_response = "".join(response_chunks)
        assert len(full_response) > 0


class TestAgentFactorySmoke:
    """Smoke tests for the AgentFactory with real AI agent creation."""

    def setup_method(self) -> None:
        """Setup for each test method."""
        self.adapter = PydanticAIAdapter()
        self.mock_mcp = MockMCPClient()
        self.factory = AgentFactory(self.adapter, self.mock_mcp)

    def test_factory_initialization(self) -> None:
        """Test factory initialization."""
        assert self.factory.adapter == self.adapter
        assert self.factory.mcp_client == self.mock_mcp
        assert isinstance(self.factory.cache, AgentCache)
        assert isinstance(self.factory._agent_settings_registry, dict)
        assert isinstance(self.factory._model_settings_registry, dict)

    @pytest.mark.asyncio  # type: ignore[untyped-decorator]
    @pytest.mark.ai_test  # type: ignore[untyped-decorator]
    @pytest.mark.openai  # type: ignore[untyped-decorator]
    async def test_get_or_create_agent_with_real_ai(self) -> None:
        """Test agent creation with real AI model."""
        model_settings = ModelSettings(
            customized_name="test_openai",
            provider="openai",
            model="gpt-4",
            api_key=test_settings.ai_provider.openai.api_key,
            max_tokens=50,
        )

        agent_settings = AgentSettings(
            role="test_role",
            description="Test agent",
            model_settings=model_settings,
            system_prompt="You are a test assistant. Respond briefly.",
        )

        # Register settings
        self.factory.register_model_settings(model_settings)
        self.factory.register_agent_settings(agent_settings)

        # Skip if no OpenAI API key or AI tests disabled
        if not test_settings.run_ai_tests or not test_settings.has_provider("openai"):
            pytest.skip("OpenAI API key not available or AI tests disabled")

        # Create agent
        agent = await self.factory.get_or_create_agent("test_role")
        assert agent is not None

    @pytest.mark.asyncio  # type: ignore[untyped-decorator]
    async def test_get_or_create_agent_missing_settings(self) -> None:
        """Test error when settings are not registered."""
        with pytest.raises(ValueError, match="No agent settings registered for role: missing_role"):
            await self.factory.get_or_create_agent("missing_role")


class TestAgentSettingsSmoke:
    """Smoke tests for AgentSettings and ModelSettings with real API keys."""

    @pytest.mark.openai  # type: ignore[untyped-decorator]
    def test_settings_with_real_openai_key(self) -> None:
        """Test settings with real OpenAI API key."""
        if test_settings.has_provider("openai"):
            model_settings = ModelSettings(
                customized_name="real_openai",
                provider="openai",
                model="gpt-4",
                api_key=test_settings.ai_provider.openai.api_key,
            )
            assert model_settings.api_key is not None
            assert model_settings.api_key.get_secret_value() is not None

    @pytest.mark.anthropic  # type: ignore[untyped-decorator]
    def test_settings_with_real_anthropic_key(self) -> None:
        """Test settings with real Anthropic API key."""
        if test_settings.has_provider("anthropic"):
            model_settings = ModelSettings(
                customized_name="real_anthropic",
                provider="anthropic",
                model="claude-3-sonnet-20240229",
                api_key=test_settings.ai_provider.anthropic.api_key,
            )
            assert model_settings.api_key is not None
            assert model_settings.api_key.get_secret_value() is not None

    @pytest.mark.google  # type: ignore[untyped-decorator]
    def test_settings_with_real_google_key(self) -> None:
        """Test settings with real Google API key."""
        if test_settings.has_provider("google"):
            model_settings = ModelSettings(
                customized_name="real_gemini",
                provider="google",
                model="gemini-pro",
                api_key=test_settings.ai_provider.gemini.api_key,
            )
            assert model_settings.api_key is not None
            assert model_settings.api_key.get_secret_value() is not None


class TestMCPClientAbstractionSmoke:
    """Smoke tests for MCPClientAbstraction integration."""

    def test_mcp_client_is_abstract(self) -> None:
        """Test that MCPClientAbstraction cannot be instantiated directly."""
        with pytest.raises(TypeError):
            MCPClientAbstraction()  # type: ignore[abstract]

    @pytest.mark.asyncio  # type: ignore[untyped-decorator]
    async def test_mcp_client_tool_names(self) -> None:
        """Test that MCP client receives correct tool names."""
        mock_mcp = MockMCPClient()

        # Call get_tools directly
        tool_names = ["calculator", "weather", "search"]
        tools = await mock_mcp.get_tools(tool_names)

        # Verify correct tools were requested
        assert mock_mcp.get_tools_call_count == 1
        assert len(tools) == len(tool_names)

        # Verify tool names are preserved
        for i, tool in enumerate(tools):
            assert hasattr(tool, "name")
            assert tool.name == tool_names[i]


class TestIntegrationSmoke:
    """Integration smoke tests for the entire abstraction system."""

    @pytest.mark.asyncio  # type: ignore[untyped-decorator]
    @pytest.mark.ai_test  # type: ignore[untyped-decorator]
    @pytest.mark.openai  # type: ignore[untyped-decorator]
    async def test_full_abstraction_workflow(self) -> None:
        """Test complete workflow: settings -> factory -> adapter -> AI model."""
        # Skip if AI tests disabled or no API keys
        if not test_settings.run_ai_tests or not test_settings.has_provider("openai"):
            pytest.skip("AI tests disabled or OpenAI API key not available")

        # Setup components
        adapter = PydanticAIAdapter()
        mock_mcp = MockMCPClient()
        factory = AgentFactory(adapter, mock_mcp)

        # Create real settings
        model_settings = ModelSettings(
            customized_name="integration_test",
            provider="openai",
            model="gpt-4",
            api_key=test_settings.ai_provider.openai.api_key,
            temperature=0.7,
            max_tokens=50,
        )

        agent_settings = AgentSettings(
            role="integration_assistant",
            description="Integration test assistant",
            model_settings=model_settings,
            tools=[],
            system_prompt="You are an integration test assistant. Respond with 'Integration test successful!'",
        )

        # Register settings
        factory.register_model_settings(model_settings)
        factory.register_agent_settings(agent_settings)

        # Create agent through factory
        agent = await factory.get_or_create_agent("integration_assistant")
        assert agent is not None

        # Run agent through adapter
        response = await adapter.run(agent, "Run integration test")

        # Verify response
        assert response is not None
        assert isinstance(response, str)
        assert len(response) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
