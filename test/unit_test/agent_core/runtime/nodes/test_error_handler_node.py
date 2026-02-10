"""Unit tests for error handler node.

Tests cover error logging, state transitions, and error record management.
"""

import pytest

from ..conftest import merge_state_update

from gearmeshing_ai.agent_core.runtime.nodes.error_handler import error_handler_node
from gearmeshing_ai.agent_core.runtime.models.workflow_state import (
    ExecutionContext,
    WorkflowState,
    WorkflowStatus,
)


@pytest.fixture
def workflow_state_with_error() -> WorkflowState:
    """Create a test workflow state with error."""
    context = ExecutionContext(
        task_description="Run tests",
        agent_role="developer",
        user_id="user_123",
    )
    status = WorkflowStatus(
        state="FAILED",
        message="Agent creation failed",
        error="Agent role not found",
    )

    return WorkflowState(
        run_id="run_123",
        status=status,
        context=context,
    )


class TestErrorHandlerNode:
    """Tests for error handler node."""

    @pytest.mark.asyncio
    async def test_error_handler_node_with_error(
        self,
        workflow_state_with_error: WorkflowState,
    ) -> None:
        """Test error handler node with error status."""
        result = await error_handler_node(workflow_state_with_error)
        updated_state = merge_state_update(workflow_state_with_error, result)
        assert updated_state.status.state == "ERROR_HANDLED"
        assert len(updated_state.executions) == 1

    @pytest.mark.asyncio
    async def test_error_handler_node_error_record(
        self,
        workflow_state_with_error: WorkflowState,
    ) -> None:
        """Test error handler node creates error record."""
        result = await error_handler_node(workflow_state_with_error)
        updated_state = merge_state_update(workflow_state_with_error, result)
        error_record = updated_state.executions[0]

        assert "timestamp" in error_record
        assert "error" in error_record
        assert "state" in error_record
        assert error_record["error"] == "Agent role not found"

    @pytest.mark.asyncio
    async def test_error_handler_node_no_error(self) -> None:
        """Test error handler node without error."""
        context = ExecutionContext(
            task_description="Run tests",
            agent_role="developer",
            user_id="user_123",
        )
        status = WorkflowStatus(state="COMPLETED")
        state = WorkflowState(
            run_id="run_123",
            status=status,
            context=context,
        )

        result = await error_handler_node(state)
        updated_state = merge_state_update(state, result)
        assert updated_state.status.state == "COMPLETED"
        assert len(updated_state.executions) == 0

    @pytest.mark.asyncio
    async def test_error_handler_node_preserves_run_id(
        self,
        workflow_state_with_error: WorkflowState,
    ) -> None:
        """Test error handler node preserves run_id."""
        result = await error_handler_node(workflow_state_with_error)
        updated_state = merge_state_update(workflow_state_with_error, result)
        assert updated_state.run_id == "run_123"

    @pytest.mark.asyncio
    async def test_error_handler_node_preserves_context(
        self,
        workflow_state_with_error: WorkflowState,
    ) -> None:
        """Test error handler node preserves context."""
        result = await error_handler_node(workflow_state_with_error)
        updated_state = merge_state_update(workflow_state_with_error, result)
        assert updated_state.context.agent_role == "developer"
        assert updated_state.context.user_id == "user_123"

    @pytest.mark.asyncio
    async def test_error_handler_node_multiple_errors(self) -> None:
        """Test error handler node with multiple error records."""
        context = ExecutionContext(
            task_description="Run tests",
            agent_role="developer",
            user_id="user_123",
        )
        status = WorkflowStatus(
            state="FAILED",
            message="Second error",
            error="Another error occurred",
        )
        executions = [
            {"error": "First error", "timestamp": "2026-02-09T10:00:00"},
        ]
        state = WorkflowState(
            run_id="run_123",
            status=status,
            context=context,
            executions=executions,
        )

        result = await error_handler_node(state)
        updated_state = merge_state_update(state, result)
        assert len(updated_state.executions) == 2
        assert updated_state.executions[1]["error"] == "Another error occurred"
