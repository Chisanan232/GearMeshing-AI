"""Unit tests for policy validation node.

Tests cover policy validation logic, approval routing, and error handling.
"""

import pytest

from gearmeshing_ai.agent.models.actions import ActionProposal
from gearmeshing_ai.agent.runtime.models.workflow_state import (
    ExecutionContext,
    WorkflowState,
    WorkflowStatus,
)
from gearmeshing_ai.agent.runtime.nodes.policy_validation import policy_validation_node

from ..conftest import merge_state_update


@pytest.fixture
def workflow_state_with_proposal() -> WorkflowState:
    """Create a test workflow state with proposal."""
    context = ExecutionContext(
        task_description="Run unit tests",
        agent_role="developer",
        user_id="user_123",
    )
    status = WorkflowStatus(state="PROPOSAL_OBTAINED")
    proposal = ActionProposal(
        action="run_tests",
        reason="Code changed",
        parameters={"test_type": "unit"},
    )

    return WorkflowState(
        run_id="run_123",
        status=status,
        context=context,
        current_proposal=proposal,
    )


class TestPolicyValidationNode:
    """Tests for policy validation node."""

    @pytest.mark.asyncio
    async def test_policy_validation_node_approved(
        self,
        workflow_state_with_proposal: WorkflowState,
    ) -> None:
        """Test policy validation node with approved proposal."""
        result = await policy_validation_node(workflow_state_with_proposal)
        updated_state = merge_state_update(workflow_state_with_proposal, result)
        assert updated_state.status.state == "POLICY_APPROVED"
        assert "approved" in updated_state.status.message.lower()

    @pytest.mark.asyncio
    async def test_policy_validation_node_preserves_proposal(
        self,
        workflow_state_with_proposal: WorkflowState,
    ) -> None:
        """Test policy validation node preserves current proposal."""
        result = await policy_validation_node(workflow_state_with_proposal)
        updated_state = merge_state_update(workflow_state_with_proposal, result)
        assert updated_state.current_proposal is not None
        assert updated_state.current_proposal.action == "run_tests"

    @pytest.mark.asyncio
    async def test_policy_validation_node_no_proposal(self) -> None:
        """Test policy validation node without proposal."""
        context = ExecutionContext(
            task_description="Run tests",
            agent_role="developer",
            user_id="user_123",
        )
        status = WorkflowStatus(state="PENDING")
        state = WorkflowState(
            run_id="run_123",
            status=status,
            context=context,
            current_proposal=None,
        )

        result = await policy_validation_node(state)
        updated_state = merge_state_update(state, result)
        assert updated_state.status.state == "FAILED"
        assert updated_state.status.error is not None

    @pytest.mark.asyncio
    async def test_policy_validation_node_preserves_run_id(
        self,
        workflow_state_with_proposal: WorkflowState,
    ) -> None:
        """Test policy validation node preserves run_id."""
        result = await policy_validation_node(workflow_state_with_proposal)
        updated_state = merge_state_update(workflow_state_with_proposal, result)
        assert updated_state.run_id == "run_123"

    @pytest.mark.asyncio
    async def test_policy_validation_node_preserves_context(
        self,
        workflow_state_with_proposal: WorkflowState,
    ) -> None:
        """Test policy validation node preserves context."""
        result = await policy_validation_node(workflow_state_with_proposal)
        updated_state = merge_state_update(workflow_state_with_proposal, result)
        assert updated_state.context.agent_role == "developer"
        assert updated_state.context.user_id == "user_123"

    @pytest.mark.asyncio
    async def test_policy_validation_node_status_message(
        self,
        workflow_state_with_proposal: WorkflowState,
    ) -> None:
        """Test policy validation node status message."""
        result = await policy_validation_node(workflow_state_with_proposal)
        updated_state = merge_state_update(workflow_state_with_proposal, result)
        assert "run_tests" in updated_state.status.message
        assert "approved" in updated_state.status.message.lower()

    @pytest.mark.asyncio
    async def test_policy_validation_node_with_different_actions(self) -> None:
        """Test policy validation node with different action types."""
        context = ExecutionContext(
            task_description="Deploy to production",
            agent_role="devops",
            user_id="user_456",
        )
        status = WorkflowStatus(state="PROPOSAL_OBTAINED")

        actions = ["deploy", "rollback", "scale_up", "update_config"]

        for action in actions:
            proposal = ActionProposal(
                action=action,
                reason=f"Execute {action}",
            )
            state = WorkflowState(
                run_id="run_456",
                status=status,
                context=context,
                current_proposal=proposal,
            )

            result = await policy_validation_node(state)
            updated_state = merge_state_update(state, result)

            assert updated_state.status.state == "POLICY_APPROVED"
            assert action in updated_state.status.message
