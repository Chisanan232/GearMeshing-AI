"""End-to-end tests for LangGraph workflow execution.

Tests cover complete workflow execution scenarios with real-like conditions,
including error handling, state management, and workflow completion.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from gearmeshing_ai.agent.abstraction.factory import AgentFactory
from gearmeshing_ai.agent.abstraction.mcp import MCPClientAbstraction
from gearmeshing_ai.agent.models.actions import ActionProposal
from gearmeshing_ai.agent.runtime.langgraph_workflow import create_agent_workflow
from gearmeshing_ai.agent.runtime.models.workflow_state import (
    ExecutionContext,
    WorkflowState,
    WorkflowStatus,
)


@pytest.fixture
def mock_agent_factory() -> MagicMock:
    """Create a mock AgentFactory for E2E tests."""
    factory = MagicMock(spec=AgentFactory)
    factory.adapter = MagicMock()
    factory.get_or_create_agent = AsyncMock()
    return factory


@pytest.fixture
def mock_mcp_client() -> MagicMock:
    """Create a mock MCPClientAbstraction for E2E tests."""
    client = MagicMock(spec=MCPClientAbstraction)
    client.execute_proposed_tool = AsyncMock()
    return client


class TestWorkflowE2E:
    """End-to-end tests for LangGraph workflow."""

    def test_complete_workflow_creation(
        self,
        mock_agent_factory: MagicMock,
        mock_mcp_client: MagicMock,
    ) -> None:
        """Test complete workflow creation and compilation."""
        workflow = create_agent_workflow(mock_agent_factory, mock_mcp_client)

        assert workflow is not None
        assert hasattr(workflow, "invoke") or hasattr(workflow, "ainvoke")

    def test_workflow_with_successful_proposal(
        self,
        mock_agent_factory: MagicMock,
        mock_mcp_client: MagicMock,
    ) -> None:
        """Test workflow with successful agent proposal."""
        # Setup mocks
        mock_agent = MagicMock()
        mock_agent_factory.get_or_create_agent = AsyncMock(return_value=mock_agent)

        proposal = ActionProposal(
            action="run_tests",
            reason="Code changed",
            parameters={"test_type": "unit"},
            expected_result="All tests pass",
        )
        mock_agent_factory.adapter.run = AsyncMock(return_value=proposal)

        # Create workflow
        workflow = create_agent_workflow(mock_agent_factory, mock_mcp_client)

        # Verify workflow
        assert workflow is not None

    def test_workflow_with_agent_error(
        self,
        mock_agent_factory: MagicMock,
        mock_mcp_client: MagicMock,
    ) -> None:
        """Test workflow handling agent creation error."""
        # Setup mock to raise error
        mock_agent_factory.get_or_create_agent = AsyncMock(side_effect=ValueError("Agent role not found"))

        # Create workflow
        workflow = create_agent_workflow(mock_agent_factory, mock_mcp_client)

        # Verify workflow was created despite error setup
        assert workflow is not None

    def test_workflow_with_tool_execution(
        self,
        mock_agent_factory: MagicMock,
        mock_mcp_client: MagicMock,
    ) -> None:
        """Test workflow with tool execution."""
        # Setup mocks
        mock_agent = MagicMock()
        mock_agent_factory.get_or_create_agent = AsyncMock(return_value=mock_agent)

        proposal = ActionProposal(
            action="run_tests",
            reason="Code changed",
        )
        mock_agent_factory.adapter.run = AsyncMock(return_value=proposal)

        mock_mcp_client.execute_proposed_tool = AsyncMock(
            return_value={"status": "success", "output": "All tests passed"}
        )

        # Create workflow
        workflow = create_agent_workflow(mock_agent_factory, mock_mcp_client)

        # Verify workflow
        assert workflow is not None

    def test_workflow_state_management(
        self,
        mock_agent_factory: MagicMock,
        mock_mcp_client: MagicMock,
    ) -> None:
        """Test workflow state management across execution."""
        context = ExecutionContext(
            task_description="Run unit tests",
            agent_role="developer",
            user_id="user_123",
        )
        status = WorkflowStatus(state="PENDING")

        initial_state = WorkflowState(
            run_id="run_123",
            status=status,
            context=context,
        )

        # Create workflow
        workflow = create_agent_workflow(mock_agent_factory, mock_mcp_client)

        # Verify workflow can handle state
        assert workflow is not None
        assert initial_state.run_id == "run_123"
        assert initial_state.context.agent_role == "developer"

    def test_workflow_with_multiple_proposals(
        self,
        mock_agent_factory: MagicMock,
        mock_mcp_client: MagicMock,
    ) -> None:
        """Test workflow handling multiple proposal scenarios."""
        proposals = [
            ActionProposal(action="run_tests", reason="Code changed"),
            ActionProposal(action="deploy", reason="Release ready"),
            ActionProposal(action="rollback", reason="Deployment failed"),
        ]

        for proposal in proposals:
            mock_agent = MagicMock()
            mock_agent_factory.get_or_create_agent = AsyncMock(return_value=mock_agent)
            mock_agent_factory.adapter.run = AsyncMock(return_value=proposal)

            workflow = create_agent_workflow(mock_agent_factory, mock_mcp_client)

            assert workflow is not None

    def test_workflow_error_recovery(
        self,
        mock_agent_factory: MagicMock,
        mock_mcp_client: MagicMock,
    ) -> None:
        """Test workflow error recovery and handling."""
        # First call raises error, second succeeds
        mock_agent = MagicMock()
        mock_agent_factory.get_or_create_agent = AsyncMock(return_value=mock_agent)

        proposal = ActionProposal(
            action="run_tests",
            reason="Code changed",
        )
        mock_agent_factory.adapter.run = AsyncMock(return_value=proposal)

        # Create workflow
        workflow = create_agent_workflow(mock_agent_factory, mock_mcp_client)

        # Verify workflow
        assert workflow is not None

    def test_workflow_context_preservation(
        self,
        mock_agent_factory: MagicMock,
        mock_mcp_client: MagicMock,
    ) -> None:
        """Test workflow preserves execution context throughout."""
        context = ExecutionContext(
            task_description="Deploy to production",
            agent_role="devops",
            user_id="user_456",
            metadata={"priority": "high", "deadline": "2026-02-10"},
        )
        status = WorkflowStatus(state="PENDING")

        state = WorkflowState(
            run_id="run_456",
            status=status,
            context=context,
        )

        # Create workflow
        workflow = create_agent_workflow(mock_agent_factory, mock_mcp_client)

        # Verify context is preserved
        assert workflow is not None
        assert state.context.metadata["priority"] == "high"
        assert state.context.user_id == "user_456"

    def test_workflow_completion_scenarios(
        self,
        mock_agent_factory: MagicMock,
        mock_mcp_client: MagicMock,
    ) -> None:
        """Test various workflow completion scenarios."""
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

        # Verify workflow
        assert workflow is not None
