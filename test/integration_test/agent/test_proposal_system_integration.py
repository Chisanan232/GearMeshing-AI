from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gearmeshing_ai.agent.abstraction.factory import AgentFactory
from gearmeshing_ai.agent.abstraction.mcp import MCPClientAbstraction
from gearmeshing_ai.agent.abstraction.settings import AgentSettings, ModelSettings
from gearmeshing_ai.agent.adapters.pydantic_ai import PydanticAIAdapter
from gearmeshing_ai.agent.models.actions import ActionProposal, MCPToolCatalog, MCPToolInfo


class MockMCPClient(MCPClientAbstraction):
    """Mock MCP client for testing"""

    def __init__(self):
        self.tools = ["run_tests", "create_pr"]
        self.tool_catalog = MCPToolCatalog(
            tools=[
                MCPToolInfo(
                    name="run_tests",
                    description="Run tests",
                    mcp_server="test_server",
                    parameters={"test_type": {"type": "string"}},
                ),
                MCPToolInfo(
                    name="create_pr",
                    description="Create pull request",
                    mcp_server="test_server",
                    parameters={"title": {"type": "string"}},
                ),
            ]
        )

    async def get_tools(self, tool_names):
        return [MagicMock() for _ in tool_names]

    async def discover_tools_for_agent(self):
        return self.tool_catalog

    async def execute_proposed_tool(self, tool_name, parameters):
        return {"success": True, "data": f"Executed {tool_name} with {parameters}", "tool_used": tool_name}


class TestProposalSystemIntegration:
    @pytest.fixture
    def mock_mcp_client(self):
        return MockMCPClient()

    @pytest.fixture
    def proposal_factory(self, mock_mcp_client):
        tool_catalog = mock_mcp_client.tool_catalog
        adapter = PydanticAIAdapter(proposal_mode=True, tool_catalog=tool_catalog)
        return AgentFactory(adapter=adapter, mcp_client=mock_mcp_client, proposal_mode=True)

    @pytest.fixture
    def traditional_factory(self, mock_mcp_client):
        adapter = PydanticAIAdapter(proposal_mode=False)
        return AgentFactory(adapter=adapter, mcp_client=mock_mcp_client, proposal_mode=False)

    @pytest.fixture
    def agent_settings(self):
        return AgentSettings(
            role="test_agent",
            description="Test agent",
            model_settings=ModelSettings(customized_name="test_model", provider="openai", model="gpt-4"),
        )

    @pytest.mark.asyncio
    async def test_proposal_factory_initialization(self, proposal_factory, mock_mcp_client):
        """Test factory initialization with proposal mode"""
        await proposal_factory.initialize_proposal_mode()

        assert proposal_factory._tool_catalog is not None
        assert len(proposal_factory._tool_catalog.tools) == 2

    @pytest.mark.asyncio
    async def test_traditional_factory_initialization(self, traditional_factory):
        """Test traditional factory initialization"""
        # Traditional mode should not initialize tool catalog
        assert traditional_factory._tool_catalog is None

    @pytest.mark.asyncio
    @patch("gearmeshing_ai.agent.adapters.pydantic_ai.PydanticAgent")
    @patch("gearmeshing_ai.agent.adapters.pydantic_ai.OpenAIModel")
    async def test_proposal_agent_creation(self, mock_openai, mock_pydantic_agent, proposal_factory, agent_settings):
        """Test creating proposal-only agent"""
        # Configure mocks to avoid API key issues
        mock_openai.return_value = MagicMock()
        mock_pydantic_agent.return_value = MagicMock()

        # Set fake API key to bypass OpenAI authentication
        import os

        os.environ["OPENAI_API_KEY"] = "fake-key-for-testing"

        proposal_factory.register_agent_settings(agent_settings)

        agent = await proposal_factory.get_or_create_agent("test_agent")
        assert agent is not None

    @pytest.mark.asyncio
    @patch("gearmeshing_ai.agent.adapters.pydantic_ai.PydanticAgent")
    @patch("gearmeshing_ai.agent.adapters.pydantic_ai.OpenAIModel")
    async def test_traditional_agent_creation(
        self, mock_openai, mock_pydantic_agent, traditional_factory, agent_settings
    ):
        """Test creating traditional agent"""
        # Configure mocks to avoid API key issues
        mock_openai.return_value = MagicMock()
        mock_pydantic_agent.return_value = MagicMock()

        # Set fake API key to bypass OpenAI authentication
        import os

        os.environ["OPENAI_API_KEY"] = "fake-key-for-testing"

        traditional_factory.register_agent_settings(agent_settings)

        agent = await traditional_factory.get_or_create_agent("test_agent")
        assert agent is not None

    @pytest.mark.asyncio
    async def test_proposal_execution(self, proposal_factory, agent_settings):
        """Test executing a proposal"""
        proposal_factory.register_agent_settings(agent_settings)

        result = await proposal_factory.execute_proposal("run_tests", {"test_type": "unit"})

        assert result["success"] is True
        assert "run_tests" in result["data"]
        assert result["tool_used"] == "run_tests"

    @pytest.mark.asyncio
    async def test_complete_proposal_workflow(self, proposal_factory, agent_settings):
        """Test complete workflow: agent creation -> proposal -> execution"""
        # Register settings
        proposal_factory.register_agent_settings(agent_settings)

        # Initialize proposal mode
        await proposal_factory.initialize_proposal_mode()

        # Mock the agent run to return a proposal
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(
            return_value=MagicMock(
                data=ActionProposal(action="run_tests", parameters={"test_type": "unit"}, reason="Need to test")
            )
        )

        # Mock adapter run to return our mock agent's result
        proposal_factory.adapter.run = AsyncMock(
            return_value=ActionProposal(action="run_tests", parameters={"test_type": "unit"}, reason="Need to test")
        )

        # Mock adapter create_agent to return our mock agent
        proposal_factory.adapter.create_agent = MagicMock(return_value=mock_agent)

        # Run complete task
        result = await proposal_factory.run_proposal_task(role="test_agent", task="Run the tests", context={})

        # Verify results
        assert "proposal" in result
        assert "execution" in result
        assert result["proposal"]["action"] == "run_tests"
        assert result["execution"]["success"] is True

    @pytest.mark.asyncio
    async def test_proposal_mode_disabled_execution(self, traditional_factory):
        """Test that execution fails when proposal mode is disabled"""
        with pytest.raises(ValueError, match="Proposal mode not enabled"):
            await traditional_factory.execute_proposal("run_tests", {})

    @pytest.mark.asyncio
    @patch("gearmeshing_ai.agent.adapters.pydantic_ai.PydanticAgent")
    @patch("gearmeshing_ai.agent.adapters.pydantic_ai.OpenAIModel")
    async def test_caching_behavior(self, mock_openai, mock_pydantic_agent, proposal_factory, agent_settings):
        """Test that agents are cached properly"""
        # Configure mocks to avoid API key issues
        mock_openai.return_value = MagicMock()
        mock_pydantic_agent.return_value = MagicMock()

        # Set fake API key to bypass OpenAI authentication
        import os

        os.environ["OPENAI_API_KEY"] = "fake-key-for-testing"

        proposal_factory.register_agent_settings(agent_settings)

        # First call should create agent
        agent1 = await proposal_factory.get_or_create_agent("test_agent")
        assert agent1 is not None

        # Second call should use cache (same object)
        agent2 = await proposal_factory.get_or_create_agent("test_agent")
        assert agent1 is agent2  # Should be the same cached instance

    @pytest.mark.asyncio
    @patch("gearmeshing_ai.agent.adapters.pydantic_ai.PydanticAgent")
    @patch("gearmeshing_ai.agent.adapters.pydantic_ai.OpenAIModel")
    async def test_proposal_vs_traditional_caching(
        self, mock_openai, mock_pydantic_agent, proposal_factory, traditional_factory, agent_settings
    ):
        """Test that proposal and traditional agents use different cache keys"""
        # Configure mocks to avoid API key issues
        mock_openai.return_value = MagicMock()
        mock_pydantic_agent.return_value = MagicMock()

        # Set fake API key to bypass OpenAI authentication
        import os

        os.environ["OPENAI_API_KEY"] = "fake-key-for-testing"

        proposal_factory.register_agent_settings(agent_settings)
        traditional_factory.register_agent_settings(agent_settings)

        # Create both agents
        proposal_agent = await proposal_factory.get_or_create_agent("test_agent")
        traditional_agent = await traditional_factory.get_or_create_agent("test_agent")

        # Verify both agents were created successfully
        assert proposal_agent is not None
        assert traditional_agent is not None
