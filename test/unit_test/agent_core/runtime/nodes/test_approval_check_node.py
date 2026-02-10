"""Unit tests for approval check node.

Tests cover approval decision logic, state transitions, and error handling.
"""

import pytest

from ..conftest import merge_state_update

from gearmeshing_ai.agent_core.models.actions import ActionProposal
from gearmeshing_ai.agent_core.runtime.nodes.approval_check import approval_check_node
from gearmeshing_ai.agent_core.runtime.workflow_state import (
    ExecutionContext,
    WorkflowState,
    WorkflowStatus,
)


@pytest.fixture
def workflow_state_with_proposal() -> WorkflowState:
    """Create a test workflow state with proposal."""
    context = ExecutionContext(
        task_description="Deploy to production",
        agent_role="devops",
        user_id="user_123",
    )
    status = WorkflowStatus(state="POLICY_APPROVED")
    proposal = ActionProposal(
        action="deploy",
        reason="Release ready",
    )

    return WorkflowState(
        run_id="run_123",
        status=status,
        context=context,
        current_proposal=proposal,
    )


class TestApprovalCheckNode:
    """Tests for approval check node."""

    @pytest.mark.asyncio
    async def test_approval_check_node_no_approval_required(
        self,
        workflow_state_with_proposal: WorkflowState,
    ) -> None:
        """Test approval check node when no approval required."""
        result = await approval_check_node(workflow_state_with_proposal)
        updated_state = merge_state_update(workflow_state_with_proposal, result)
        assert updated_state.status.state == "APPROVAL_SKIPPED"
        assert "proceeding" in updated_state.status.message.lower()

    @pytest.mark.asyncio
    async def test_approval_check_node_preserves_proposal(
        self,
        workflow_state_with_proposal: WorkflowState,
    ) -> None:
        """Test approval check node preserves current proposal."""
        result = await approval_check_node(workflow_state_with_proposal)
        updated_state = merge_state_update(workflow_state_with_proposal, result)
        assert updated_state.current_proposal is not None
        assert updated_state.current_proposal.action == "deploy"

    @pytest.mark.asyncio
    async def test_approval_check_node_no_proposal(self) -> None:
        """Test approval check node without proposal."""
        context = ExecutionContext(
            task_description="Deploy",
            agent_role="devops",
            user_id="user_123",
        )
        status = WorkflowStatus(state="POLICY_APPROVED")
        state = WorkflowState(
            run_id="run_123",
            status=status,
            context=context,
            current_proposal=None,
        )

        result = await approval_check_node(state)
        updated_state = merge_state_update(state, result)
        assert updated_state.status.state == "FAILED"
        assert updated_state.status.error is not None

    @pytest.mark.asyncio
    async def test_approval_check_node_preserves_run_id(
        self,
        workflow_state_with_proposal: WorkflowState,
    ) -> None:
        """Test approval check node preserves run_id."""
        result = await approval_check_node(workflow_state_with_proposal)
        updated_state = merge_state_update(workflow_state_with_proposal, result)
        assert updated_state.run_id == "run_123"

    @pytest.mark.asyncio
    async def test_approval_check_node_preserves_context(
        self,
        workflow_state_with_proposal: WorkflowState,
    ) -> None:
        """Test approval check node preserves context."""
        result = await approval_check_node(workflow_state_with_proposal)
        updated_state = merge_state_update(workflow_state_with_proposal, result)
        assert updated_state.context.agent_role == "devops"
        assert updated_state.context.user_id == "user_123"
