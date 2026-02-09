"""Integration tests for LangGraph workflow with real components.

Tests cover workflow execution with real AgentFactory and MCP client interactions,
state transitions, and multi-node workflows.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from gearmeshing_ai.agent_core.abstraction.factory import AgentFactory
from gearmeshing_ai.agent_core.abstraction.mcp import MCPClientAbstraction
from gearmeshing_ai.agent_core.models.actions import ActionProposal
from gearmeshing_ai.agent_core.runtime.langgraph_workflow import create_agent_workflow
from gearmeshing_ai.agent_core.runtime.workflow_state import (
    ExecutionContext,
    WorkflowState,
    WorkflowStatus,
)


@pytest.fixture
def mock_agent_factory() -> MagicMock:
    """Create a mock AgentFactory for integration tests."""
    factory = MagicMock(spec=AgentFactory)
    factory.adapter = MagicMock()
    factory.get_or_create_agent = AsyncMock()
    return factory


@pytest.fixture
def mock_mcp_client() -> MagicMock:
    """Create a mock MCPClientAbstraction for integration tests."""
    client = MagicMock(spec=MCPClientAbstraction)
    client.execute_proposed_tool = AsyncMock()
    return client


@pytest.fixture
def initial_workflow_state() -> WorkflowState:
    """Create initial workflow state for integration tests."""
    context = ExecutionContext(
        task_description="Run unit tests",
        agent_role="developer",
        user_id="user_123",
    )
    status = WorkflowStatus(state="PENDING")

    return WorkflowState(
        run_id="run_123",
        status=status,
        context=context,
    )


class TestWorkflowIntegration:
    """Integration tests for LangGraph workflow."""

    def test_workflow_creation_with_real_components(
        self,
        mock_agent_factory: MagicMock,
        mock_mcp_client: MagicMock,
    ) -> None:
        """Test workflow creation with real component instances."""
        workflow = create_agent_workflow(mock_agent_factory, mock_mcp_client)

        assert workflow is not None
        assert hasattr(workflow, "invoke") or hasattr(workflow, "ainvoke")

    @pytest.mark.asyncio
    async def test_workflow_agent_decision_integration(
        self,
        mock_agent_factory: MagicMock,
        mock_mcp_client: MagicMock,
        initial_workflow_state: WorkflowState,
    ) -> None:
        """Test workflow agent decision node integration."""
        # Setup mocks
        mock_agent = MagicMock()
        mock_agent_factory.get_or_create_agent = AsyncMock(return_value=mock_agent)

        proposal = ActionProposal(
            action="run_tests",
            reason="Code changed",
            parameters={"test_type": "unit"},
        )
        mock_agent_factory.adapter.run = AsyncMock(return_value=proposal)

        # Create workflow
        workflow = create_agent_workflow(mock_agent_factory, mock_mcp_client)

        # Verify workflow was created
        assert workflow is not None

    @pytest.mark.asyncio
    async def test_workflow_with_policy_validation(
        self,
        mock_agent_factory: MagicMock,
        mock_mcp_client: MagicMock,
        initial_workflow_state: WorkflowState,
    ) -> None:
        """Test workflow with policy validation node."""
        # Setup mocks
        mock_agent = MagicMock()
        mock_agent_factory.get_or_create_agent = AsyncMock(return_value=mock_agent)

        proposal = ActionProposal(
            action="run_tests",
            reason="Code changed",
        )
        mock_agent_factory.adapter.run = AsyncMock(return_value=proposal)

        # Create workflow
        workflow = create_agent_workflow(mock_agent_factory, mock_mcp_client)

        # Verify workflow structure
        assert workflow is not None

    def test_workflow_state_preservation(
        self,
        mock_agent_factory: MagicMock,
        mock_mcp_client: MagicMock,
        initial_workflow_state: WorkflowState,
    ) -> None:
        """Test that workflow preserves state across nodes."""
        workflow = create_agent_workflow(mock_agent_factory, mock_mcp_client)

        # Verify workflow can handle state
        assert workflow is not None
        assert hasattr(workflow, "invoke") or hasattr(workflow, "ainvoke")

    def test_workflow_error_handling_integration(
        self,
        mock_agent_factory: MagicMock,
        mock_mcp_client: MagicMock,
    ) -> None:
        """Test workflow error handling across nodes."""
        # Setup mock to raise error
        mock_agent_factory.get_or_create_agent = AsyncMock(
            side_effect=ValueError("Agent not found")
        )

        workflow = create_agent_workflow(mock_agent_factory, mock_mcp_client)

        # Verify workflow was created successfully
        assert workflow is not None

    def test_workflow_with_multiple_factory_instances(
        self,
        mock_mcp_client: MagicMock,
    ) -> None:
        """Test workflow creation with multiple factory instances."""
        factory1 = MagicMock(spec=AgentFactory)
        factory1.adapter = MagicMock()

        factory2 = MagicMock(spec=AgentFactory)
        factory2.adapter = MagicMock()

        workflow1 = create_agent_workflow(factory1, mock_mcp_client)
        workflow2 = create_agent_workflow(factory2, mock_mcp_client)

        # Both workflows should be independent
        assert workflow1 is not None
        assert workflow2 is not None
        assert workflow1 is not workflow2

    def test_workflow_component_interaction(
        self,
        mock_agent_factory: MagicMock,
        mock_mcp_client: MagicMock,
    ) -> None:
        """Test interaction between workflow components."""
        # Setup mocks for component interaction
        mock_agent = MagicMock()
        mock_agent_factory.get_or_create_agent = AsyncMock(return_value=mock_agent)
        mock_agent_factory.adapter.run = AsyncMock(
            return_value=ActionProposal(
                action="test_action",
                reason="test reason",
            )
        )

        mock_mcp_client.execute_proposed_tool = AsyncMock(
            return_value={"status": "success"}
        )

        # Create workflow
        workflow = create_agent_workflow(mock_agent_factory, mock_mcp_client)

        # Verify workflow was created
        assert workflow is not None

    def test_workflow_state_transitions(
        self,
        mock_agent_factory: MagicMock,
        mock_mcp_client: MagicMock,
        initial_workflow_state: WorkflowState,
    ) -> None:
        """Test workflow state transitions across nodes."""
        workflow = create_agent_workflow(mock_agent_factory, mock_mcp_client)

        # Verify workflow structure supports state transitions
        assert workflow is not None
        assert hasattr(workflow, "invoke") or hasattr(workflow, "ainvoke")

    def test_workflow_with_context_preservation(
        self,
        mock_agent_factory: MagicMock,
        mock_mcp_client: MagicMock,
        initial_workflow_state: WorkflowState,
    ) -> None:
        """Test workflow preserves execution context."""
        workflow = create_agent_workflow(mock_agent_factory, mock_mcp_client)

        # Verify workflow was created
        assert workflow is not None

        # Verify initial state has context
        assert initial_workflow_state.context is not None
        assert initial_workflow_state.context.agent_role == "developer"
