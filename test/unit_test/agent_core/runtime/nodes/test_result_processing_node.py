"""Unit tests for result processing node.

Tests cover result processing logic, error detection, and state updates.
"""

from typing import Any

import pytest

from ..conftest import merge_state_update

from gearmeshing_ai.agent_core.runtime.nodes.result_processing import result_processing_node
from gearmeshing_ai.agent_core.runtime.workflow_state import (
    ExecutionContext,
    WorkflowState,
    WorkflowStatus,
)


@pytest.fixture
def workflow_state_with_execution() -> WorkflowState:
    """Create a test workflow state with execution results."""
    context = ExecutionContext(
        task_description="Run tests",
        agent_role="developer",
        user_id="user_123",
    )
    status = WorkflowStatus(state="APPROVAL_SKIPPED")
    executions: list[dict[str, Any]] = [
        {
            "action": "run_tests",
            "result": "passed",
            "timestamp": "2026-02-09T10:00:00",
        }
    ]

    return WorkflowState(
        run_id="run_123",
        status=status,
        context=context,
        executions=executions,
    )


class TestResultProcessingNode:
    """Tests for result processing node."""

    @pytest.mark.asyncio
    async def test_result_processing_node_success(
        self,
        workflow_state_with_execution: WorkflowState,
    ) -> None:
        """Test result processing node with successful execution."""
        result = await result_processing_node(workflow_state_with_execution)
        updated_state = merge_state_update(workflow_state_with_execution, result)
        assert updated_state.status.state == "RESULTS_PROCESSED"
        assert "run_tests" in updated_state.status.message

    @pytest.mark.asyncio
    async def test_result_processing_node_no_executions(self) -> None:
        """Test result processing node with no executions."""
        context = ExecutionContext(
            task_description="Run tests",
            agent_role="developer",
            user_id="user_123",
        )
        status = WorkflowStatus(state="APPROVAL_SKIPPED")
        state = WorkflowState(
            run_id="run_123",
            status=status,
            context=context,
            executions=[],
        )

        result = await result_processing_node(state)
        updated_state = merge_state_update(state, result)
        assert updated_state.status.state == "RESULTS_PROCESSED"
        assert "no execution results" in updated_state.status.message.lower()

    @pytest.mark.asyncio
    async def test_result_processing_node_with_error(self) -> None:
        """Test result processing node with execution error."""
        context = ExecutionContext(
            task_description="Run tests",
            agent_role="developer",
            user_id="user_123",
        )
        status = WorkflowStatus(state="APPROVAL_SKIPPED")
        executions: list[dict[str, Any]] = [
            {
                "action": "run_tests",
                "error": "Tests failed",
                "timestamp": "2026-02-09T10:00:00",
            }
        ]
        state = WorkflowState(
            run_id="run_123",
            status=status,
            context=context,
            executions=executions,
        )

        result = await result_processing_node(state)
        updated_state = merge_state_update(state, result)
        assert updated_state.status.state == "EXECUTION_FAILED"
        assert "Tests failed" in updated_state.status.error or "Tests failed" in updated_state.status.message

    @pytest.mark.asyncio
    async def test_result_processing_node_preserves_run_id(
        self,
        workflow_state_with_execution: WorkflowState,
    ) -> None:
        """Test result processing node preserves run_id."""
        result = await result_processing_node(workflow_state_with_execution)
        updated_state = merge_state_update(workflow_state_with_execution, result)
        assert updated_state.run_id == "run_123"

    @pytest.mark.asyncio
    async def test_result_processing_node_preserves_context(
        self,
        workflow_state_with_execution: WorkflowState,
    ) -> None:
        """Test result processing node preserves context."""
        result = await result_processing_node(workflow_state_with_execution)
        updated_state = merge_state_update(workflow_state_with_execution, result)
        assert updated_state.context.agent_role == "developer"
        assert updated_state.context.user_id == "user_123"

    @pytest.mark.asyncio
    async def test_result_processing_node_multiple_executions(self) -> None:
        """Test result processing node with multiple executions."""
        context = ExecutionContext(
            task_description="Run tests",
            agent_role="developer",
            user_id="user_123",
        )
        status = WorkflowStatus(state="APPROVAL_SKIPPED")
        executions: list[dict[str, Any]] = [
            {"action": "run_unit_tests", "result": "passed"},
            {"action": "run_integration_tests", "result": "passed"},
            {"action": "run_e2e_tests", "result": "passed"},
        ]
        state = WorkflowState(
            run_id="run_123",
            status=status,
            context=context,
            executions=executions,
        )

        result = await result_processing_node(state)
        updated_state = merge_state_update(state, result)
        assert updated_state.status.state == "RESULTS_PROCESSED"
        assert "run_e2e_tests" in updated_state.status.message
