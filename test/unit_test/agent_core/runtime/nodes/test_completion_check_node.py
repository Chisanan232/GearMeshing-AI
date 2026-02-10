"""Unit tests for completion check node.

Tests cover completion detection, state transitions, and workflow continuation logic.
"""

import pytest

from gearmeshing_ai.agent_core.runtime.models.workflow_state import (
    ExecutionContext,
    WorkflowState,
    WorkflowStatus,
)
from gearmeshing_ai.agent_core.runtime.nodes.completion_check import completion_check_node

from ..conftest import merge_state_update


@pytest.fixture
def workflow_state_base() -> WorkflowState:
    """Create a base test workflow state."""
    context = ExecutionContext(
        task_description="Run tests",
        agent_role="developer",
        user_id="user_123",
    )
    return WorkflowState(
        run_id="run_123",
        status=WorkflowStatus(state="PENDING"),
        context=context,
    )


class TestCompletionCheckNode:
    """Tests for completion check node."""

    @pytest.mark.asyncio
    async def test_completion_check_node_results_processed(
        self,
        workflow_state_base: WorkflowState,
    ) -> None:
        """Test completion check node with RESULTS_PROCESSED state."""
        state = workflow_state_base.model_copy(update={"status": WorkflowStatus(state="RESULTS_PROCESSED")})

        result = await completion_check_node(state)
        updated_state = merge_state_update(state, result)
        assert updated_state.status.state == "COMPLETED"

    @pytest.mark.asyncio
    async def test_completion_check_node_policy_rejected(
        self,
        workflow_state_base: WorkflowState,
    ) -> None:
        """Test completion check node with POLICY_REJECTED state."""
        state = workflow_state_base.model_copy(update={"status": WorkflowStatus(state="POLICY_REJECTED")})

        result = await completion_check_node(state)
        updated_state = merge_state_update(state, result)
        assert updated_state.status.state == "COMPLETED"

    @pytest.mark.asyncio
    async def test_completion_check_node_error_handled(
        self,
        workflow_state_base: WorkflowState,
    ) -> None:
        """Test completion check node with ERROR_HANDLED state."""
        state = workflow_state_base.model_copy(update={"status": WorkflowStatus(state="ERROR_HANDLED")})

        result = await completion_check_node(state)
        updated_state = merge_state_update(state, result)
        assert updated_state.status.state == "COMPLETED"

    @pytest.mark.asyncio
    async def test_completion_check_node_continuing(
        self,
        workflow_state_base: WorkflowState,
    ) -> None:
        """Test completion check node with continuing state."""
        state = workflow_state_base.model_copy(update={"status": WorkflowStatus(state="PROPOSAL_OBTAINED")})

        result = await completion_check_node(state)
        updated_state = merge_state_update(state, result)
        assert updated_state.status.state == "CONTINUING"

    @pytest.mark.asyncio
    async def test_completion_check_node_preserves_run_id(
        self,
        workflow_state_base: WorkflowState,
    ) -> None:
        """Test completion check node preserves run_id."""
        state = workflow_state_base.model_copy(update={"status": WorkflowStatus(state="RESULTS_PROCESSED")})

        result = await completion_check_node(state)
        updated_state = merge_state_update(state, result)
        assert updated_state.run_id == "run_123"

    @pytest.mark.asyncio
    async def test_completion_check_node_preserves_context(
        self,
        workflow_state_base: WorkflowState,
    ) -> None:
        """Test completion check node preserves context."""
        state = workflow_state_base.model_copy(update={"status": WorkflowStatus(state="RESULTS_PROCESSED")})

        result = await completion_check_node(state)
        updated_state = merge_state_update(state, result)
        assert updated_state.context.agent_role == "developer"
        assert updated_state.context.user_id == "user_123"

    @pytest.mark.asyncio
    async def test_completion_check_node_with_error(
        self,
        workflow_state_base: WorkflowState,
    ) -> None:
        """Test completion check node with error status."""
        state = workflow_state_base.model_copy(
            update={
                "status": WorkflowStatus(
                    state="RESULTS_PROCESSED",
                    error="Some error occurred",
                )
            }
        )

        result = await completion_check_node(state)
        updated_state = merge_state_update(state, result)
        # Completion check should mark as COMPLETED even with error
        assert updated_state.status.state == "COMPLETED"
