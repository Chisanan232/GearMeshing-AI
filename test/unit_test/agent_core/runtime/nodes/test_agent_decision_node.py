"""Unit tests for agent decision node.

Tests cover agent creation, proposal generation, error handling,
and integration with AgentFactory.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from gearmeshing_ai.agent_core.abstraction.factory import AgentFactory
from gearmeshing_ai.agent_core.models.actions import ActionProposal
from gearmeshing_ai.agent_core.runtime.nodes.agent_decision import agent_decision_node
from gearmeshing_ai.agent_core.runtime.models.workflow_state import (
    ExecutionContext,
    WorkflowState,
    WorkflowStatus,
)

from ..conftest import merge_state_update


@pytest.fixture
def workflow_state() -> WorkflowState:
    """Create a test workflow state."""
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


@pytest.fixture
def mock_agent_factory() -> MagicMock:
    """Create a mock AgentFactory."""
    factory = MagicMock(spec=AgentFactory)
    factory.adapter = MagicMock()
    return factory


class TestAgentDecisionNode:
    """Tests for agent decision node."""

    @pytest.mark.asyncio
    async def test_agent_decision_node_basic(
        self,
        workflow_state: WorkflowState,
        mock_agent_factory: MagicMock,
    ) -> None:
        """Test basic agent decision node execution."""
        # Setup mock
        mock_agent = MagicMock()
        mock_agent_factory.get_or_create_agent = AsyncMock(return_value=mock_agent)

        proposal = ActionProposal(
            action="run_tests",
            reason="Code changed",
            parameters={"test_type": "unit"},
        )
        mock_agent_factory.adapter.run = AsyncMock(return_value=proposal)

        # Execute node
        result = await agent_decision_node(workflow_state, mock_agent_factory)

        # Merge state update (simulating LangGraph behavior)
        updated_state = merge_state_update(workflow_state, result)

        # Verify
        assert updated_state.current_proposal is not None
        assert updated_state.current_proposal.action == "run_tests"
        assert updated_state.status.state == "PROPOSAL_OBTAINED"

    @pytest.mark.asyncio
    async def test_agent_decision_node_with_context(
        self,
        workflow_state: WorkflowState,
        mock_agent_factory: MagicMock,
    ) -> None:
        """Test agent decision node with execution context."""
        # Setup mock
        mock_agent = MagicMock()
        mock_agent_factory.get_or_create_agent = AsyncMock(return_value=mock_agent)

        proposal = ActionProposal(
            action="deploy",
            reason="Release ready",
            parameters={"environment": "production"},
        )
        mock_agent_factory.adapter.run = AsyncMock(return_value=proposal)

        # Execute node
        result = await agent_decision_node(workflow_state, mock_agent_factory)

        # Merge state update
        updated_state = merge_state_update(workflow_state, result)

        # Verify agent was called with correct role
        mock_agent_factory.get_or_create_agent.assert_called_once_with("developer")

        # Verify adapter was called with correct task
        mock_agent_factory.adapter.run.assert_called_once()
        call_args = mock_agent_factory.adapter.run.call_args
        assert call_args[0][1] == "Run unit tests"
        
        # Verify proposal was set
        assert updated_state.current_proposal is not None

    @pytest.mark.asyncio
    async def test_agent_decision_node_invalid_proposal_type(
        self,
        workflow_state: WorkflowState,
        mock_agent_factory: MagicMock,
    ) -> None:
        """Test agent decision node with invalid proposal type."""
        # Setup mock to return wrong type
        mock_agent = MagicMock()
        mock_agent_factory.get_or_create_agent = AsyncMock(return_value=mock_agent)
        mock_agent_factory.adapter.run = AsyncMock(return_value={"invalid": "proposal"})

        # Execute node - should raise TypeError
        with pytest.raises(TypeError):
            await agent_decision_node(workflow_state, mock_agent_factory)

    @pytest.mark.asyncio
    async def test_agent_decision_node_agent_not_found(
        self,
        workflow_state: WorkflowState,
        mock_agent_factory: MagicMock,
    ) -> None:
        """Test agent decision node when agent role not found."""
        # Setup mock to raise ValueError
        mock_agent_factory.get_or_create_agent = AsyncMock(side_effect=ValueError("Agent role not found"))

        # Execute node
        result = await agent_decision_node(workflow_state, mock_agent_factory)

        # Merge state update
        updated_state = merge_state_update(workflow_state, result)

        # Verify error state
        assert updated_state.status.state == "FAILED"
        assert updated_state.status.error is not None
        assert "Agent role not found" in updated_state.status.error

    @pytest.mark.asyncio
    async def test_agent_decision_node_agent_execution_error(
        self,
        workflow_state: WorkflowState,
        mock_agent_factory: MagicMock,
    ) -> None:
        """Test agent decision node when agent execution fails."""
        # Setup mock to raise RuntimeError
        mock_agent = MagicMock()
        mock_agent_factory.get_or_create_agent = AsyncMock(return_value=mock_agent)
        mock_agent_factory.adapter.run = AsyncMock(side_effect=RuntimeError("Agent execution failed"))

        # Execute node
        result = await agent_decision_node(workflow_state, mock_agent_factory)

        # Merge state update
        updated_state = merge_state_update(workflow_state, result)

        # Verify error state
        assert updated_state.status.state == "FAILED"
        assert updated_state.status.error is not None
        assert "Agent execution failed" in updated_state.status.error

    @pytest.mark.asyncio
    async def test_agent_decision_node_preserves_run_id(
        self,
        workflow_state: WorkflowState,
        mock_agent_factory: MagicMock,
    ) -> None:
        """Test agent decision node preserves run_id."""
        # Setup mock
        mock_agent = MagicMock()
        mock_agent_factory.get_or_create_agent = AsyncMock(return_value=mock_agent)

        proposal = ActionProposal(
            action="run_tests",
            reason="Code changed",
        )
        mock_agent_factory.adapter.run = AsyncMock(return_value=proposal)

        # Execute node
        result = await agent_decision_node(workflow_state, mock_agent_factory)

        # Merge state update
        updated_state = merge_state_update(workflow_state, result)

        # Verify run_id preserved
        assert updated_state.run_id == "run_123"

    @pytest.mark.asyncio
    async def test_agent_decision_node_preserves_context(
        self,
        workflow_state: WorkflowState,
        mock_agent_factory: MagicMock,
    ) -> None:
        """Test agent decision node preserves execution context."""
        # Setup mock
        mock_agent = MagicMock()
        mock_agent_factory.get_or_create_agent = AsyncMock(return_value=mock_agent)

        proposal = ActionProposal(
            action="run_tests",
            reason="Code changed",
        )
        mock_agent_factory.adapter.run = AsyncMock(return_value=proposal)

        # Execute node
        result = await agent_decision_node(workflow_state, mock_agent_factory)

        # Merge state update
        updated_state = merge_state_update(workflow_state, result)

        # Verify context preserved
        assert updated_state.context.task_description == "Run unit tests"
        assert updated_state.context.agent_role == "developer"
        assert updated_state.context.user_id == "user_123"

    @pytest.mark.asyncio
    async def test_agent_decision_node_with_parameters(
        self,
        workflow_state: WorkflowState,
        mock_agent_factory: MagicMock,
    ) -> None:
        """Test agent decision node with proposal parameters."""
        # Setup mock
        mock_agent = MagicMock()
        mock_agent_factory.get_or_create_agent = AsyncMock(return_value=mock_agent)

        proposal = ActionProposal(
            action="run_tests",
            reason="Code changed",
            parameters={"test_type": "unit", "coverage": True},
            expected_result="All tests pass",
        )
        mock_agent_factory.adapter.run = AsyncMock(return_value=proposal)

        # Execute node
        result = await agent_decision_node(workflow_state, mock_agent_factory)

        # Merge state update
        updated_state = merge_state_update(workflow_state, result)

        # Verify proposal details
        assert updated_state.current_proposal.parameters == {
            "test_type": "unit",
            "coverage": True,
        }
        assert updated_state.current_proposal.expected_result == "All tests pass"

    @pytest.mark.asyncio
    async def test_agent_decision_node_status_message(
        self,
        workflow_state: WorkflowState,
        mock_agent_factory: MagicMock,
    ) -> None:
        """Test agent decision node status message."""
        # Setup mock
        mock_agent = MagicMock()
        mock_agent_factory.get_or_create_agent = AsyncMock(return_value=mock_agent)

        proposal = ActionProposal(
            action="deploy_app",
            reason="Release ready",
        )
        mock_agent_factory.adapter.run = AsyncMock(return_value=proposal)

        # Execute node
        result = await agent_decision_node(workflow_state, mock_agent_factory)

        # Merge state update
        updated_state = merge_state_update(workflow_state, result)

        # Verify status message
        assert "deploy_app" in updated_state.status.message
        assert "Agent proposed action" in updated_state.status.message
