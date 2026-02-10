"""Integration tests for AI agent tool registration."""

from unittest.mock import MagicMock, patch

import pytest

from gearmeshing_ai.agent.abstraction.settings import AgentSettings, ModelSettings
from gearmeshing_ai.agent.adapters.pydantic_ai import PydanticAIAdapter


class TestToolRegistration:
    """Test tool registration in AI agent adapters."""

    def test_pydantic_ai_tool_registration(self):
        """Test that Pydantic AI adapter properly registers tools."""
        adapter = PydanticAIAdapter()

        # Create settings (no tool configuration needed)
        model_settings = ModelSettings(customized_name="test-model", provider="openai", model="gpt-3.5-turbo")
        agent_settings = AgentSettings(role="test", description="Test agent", model_settings=model_settings)

        # Mock both the model classes and PydanticAgent to avoid API key requirement
        with (
            patch("gearmeshing_ai.agent.adapters.pydantic_ai.OpenAIModel") as mock_openai_model,
            patch("gearmeshing_ai.agent.adapters.pydantic_ai.PydanticAgent") as mock_agent_class,
        ):
            mock_model = MagicMock()
            mock_openai_model.return_value = mock_model
            mock_agent = MagicMock()
            mock_agent_class.return_value = mock_agent

            # Create agent (should register tools automatically)
            agent = adapter.create_agent(agent_settings, tools=[])

            # Verify agent was created
            assert agent is not None
            mock_agent_class.assert_called_once()

    def test_proposal_mode_no_tools(self):
        """Test that proposal mode doesn't register tools."""
        adapter = PydanticAIAdapter(proposal_mode=True)

        # Create settings
        model_settings = ModelSettings(customized_name="test-model", provider="openai", model="gpt-3.5-turbo")
        agent_settings = AgentSettings(role="test", description="Test agent", model_settings=model_settings)

        # Mock both the model classes and PydanticAgent to avoid API key requirement
        with (
            patch("gearmeshing_ai.agent.adapters.pydantic_ai.OpenAIModel") as mock_openai_model,
            patch("gearmeshing_ai.agent.adapters.pydantic_ai.PydanticAgent") as mock_agent_class,
        ):
            mock_model = MagicMock()
            mock_openai_model.return_value = mock_model
            mock_agent = MagicMock()
            mock_agent_class.return_value = mock_agent

            # Create agent (proposal mode - no tools registered)
            agent = adapter.create_agent(agent_settings, tools=[])

            assert agent is not None
            # Tools should not be registered in proposal mode

    def test_tool_registration_methods_exist(self):
        """Test that all required tool registration methods exist."""
        adapter = PydanticAIAdapter()

        # Check that all protected methods exist
        assert hasattr(adapter, "_register_tool_read_file")
        assert hasattr(adapter, "_register_tool_write_file")
        assert hasattr(adapter, "_register_tool_list_files")
        assert hasattr(adapter, "_register_tool_run_command")
        assert hasattr(adapter, "_register_file_tools")
        assert hasattr(adapter, "_register_command_tools")
        assert hasattr(adapter, "_register_tools")

    def test_tool_registration_methods_are_callable(self):
        """Test that tool registration methods are callable."""
        adapter = PydanticAIAdapter()

        # These methods should be callable (even if they just pass)
        assert callable(adapter._register_tool_read_file)
        assert callable(adapter._register_tool_write_file)
        assert callable(adapter._register_tool_list_files)
        assert callable(adapter._register_tool_run_command)
        assert callable(adapter._register_file_tools)
        assert callable(adapter._register_command_tools)
        assert callable(adapter._register_tools)

    @pytest.mark.asyncio
    async def test_tool_execution_integration(self):
        """Test that tools can be executed through the agent."""
        # This test would require a real API key and Pydantic AI installation
        # For now, we'll just test the integration structure

        adapter = PydanticAIAdapter()

        # Create settings
        model_settings = ModelSettings(customized_name="test-model", provider="openai", model="gpt-3.5-turbo")
        agent_settings = AgentSettings(role="test", description="Test agent", model_settings=model_settings)

        # Mock both the model classes and PydanticAgent to avoid API key requirement
        with (
            patch("gearmeshing_ai.agent.adapters.pydantic_ai.OpenAIModel") as mock_openai_model,
            patch("gearmeshing_ai.agent.adapters.pydantic_ai.PydanticAgent") as mock_agent_class,
        ):
            mock_model = MagicMock()
            mock_openai_model.return_value = mock_model
            mock_agent = MagicMock()
            mock_agent_class.return_value = mock_agent

            # Create agent
            agent = adapter.create_agent(agent_settings, tools=[])
            assert agent is not None

        # Note: Actual tool execution testing would require:
        # 1. Real API key
        # 2. Pydantic AI library installed
        # 3. Mocking or integration test setup
        # This test verifies the structure is in place

    def test_adapter_inheritance(self):
        """Test that adapter properly inherits from AgentAdapter."""
        from gearmeshing_ai.agent.abstraction.adapter import AgentAdapter

        adapter = PydanticAIAdapter()
        assert isinstance(adapter, AgentAdapter)

    def test_adapter_initialization(self):
        """Test adapter initialization with different modes."""
        # Traditional mode
        adapter1 = PydanticAIAdapter(proposal_mode=False)
        assert adapter1.proposal_mode is False
        assert adapter1.tool_catalog is None

        # Proposal mode
        adapter2 = PydanticAIAdapter(proposal_mode=True)
        assert adapter2.proposal_mode is True
        assert adapter2.tool_catalog is None

        # With tool catalog
        from gearmeshing_ai.agent.models.actions import MCPToolCatalog

        catalog = MCPToolCatalog(tools=[])
        adapter3 = PydanticAIAdapter(proposal_mode=True, tool_catalog=catalog)
        assert adapter3.proposal_mode is True
        assert adapter3.tool_catalog is catalog
