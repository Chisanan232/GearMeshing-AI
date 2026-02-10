"""Unit tests for workflow state model.

Tests cover WorkflowState initialization, integration with ActionProposal
and MCPToolCatalog, validation, and type checking.
"""

from datetime import datetime
from typing import Any

import pytest
from pydantic import ValidationError

from gearmeshing_ai.agent.models.actions import ActionProposal, MCPToolCatalog, MCPToolInfo
from gearmeshing_ai.agent.runtime.models.workflow_state import (
    ExecutionContext,
    WorkflowState,
    WorkflowStatus,
)


class TestExecutionContext:
    """Tests for ExecutionContext model."""

    def test_execution_context_initialization(self) -> None:
        """Test ExecutionContext initialization with required fields."""
        context = ExecutionContext(
            task_description="Run unit tests",
            agent_role="developer",
            user_id="user_123",
        )

        assert context.task_description == "Run unit tests"
        assert context.agent_role == "developer"
        assert context.user_id == "user_123"
        assert context.metadata == {}

    def test_execution_context_with_metadata(self) -> None:
        """Test ExecutionContext with additional metadata."""
        metadata = {"priority": "high", "deadline": "2026-02-10"}
        context = ExecutionContext(
            task_description="Deploy to production",
            agent_role="devops",
            user_id="user_456",
            metadata=metadata,
        )

        assert context.metadata == metadata
        assert context.metadata["priority"] == "high"

    def test_execution_context_validation_missing_required_field(self) -> None:
        """Test ExecutionContext validation fails with missing required field."""
        with pytest.raises(ValidationError):
            ExecutionContext(
                task_description="Run tests",
                agent_role="developer",
                # Missing user_id
            )

    def test_execution_context_serialization(self) -> None:
        """Test ExecutionContext serialization to dict."""
        context = ExecutionContext(
            task_description="Run tests",
            agent_role="developer",
            user_id="user_123",
        )

        context_dict = context.model_dump()
        assert context_dict["task_description"] == "Run tests"
        assert context_dict["agent_role"] == "developer"
        assert context_dict["user_id"] == "user_123"


class TestWorkflowStatus:
    """Tests for WorkflowStatus model."""

    def test_workflow_status_initialization(self) -> None:
        """Test WorkflowStatus initialization."""
        status = WorkflowStatus(
            state="RUNNING",
            message="Workflow is running",
        )

        assert status.state == "RUNNING"
        assert status.message == "Workflow is running"
        assert status.error is None

    def test_workflow_status_with_error(self) -> None:
        """Test WorkflowStatus with error message."""
        status = WorkflowStatus(
            state="FAILED",
            message="Workflow failed",
            error="Agent creation failed",
        )

        assert status.state == "FAILED"
        assert status.error == "Agent creation failed"

    def test_workflow_status_validation(self) -> None:
        """Test WorkflowStatus validation."""
        with pytest.raises(ValidationError):
            WorkflowStatus(
                # Missing required state field
                message="Test message",
            )


class TestWorkflowState:
    """Tests for WorkflowState model."""

    def test_workflow_state_initialization(self) -> None:
        """Test WorkflowState initialization with required fields."""
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
        )

        assert state.run_id == "run_123"
        assert state.status.state == "PENDING"
        assert state.context.agent_role == "developer"
        assert state.current_proposal is None
        assert state.available_capabilities is None
        assert state.decisions == []
        assert state.executions == []
        assert state.approvals == []

    def test_workflow_state_with_action_proposal(self) -> None:
        """Test WorkflowState with ActionProposal integration."""
        context = ExecutionContext(
            task_description="Run tests",
            agent_role="developer",
            user_id="user_123",
        )
        status = WorkflowStatus(state="PROPOSAL_OBTAINED")
        proposal = ActionProposal(
            action="run_tests",
            reason="Code changed",
            parameters={"test_type": "unit"},
        )

        state = WorkflowState(
            run_id="run_123",
            status=status,
            context=context,
            current_proposal=proposal,
        )

        assert state.current_proposal is not None
        assert state.current_proposal.action == "run_tests"
        assert state.current_proposal.reason == "Code changed"
        assert state.current_proposal.parameters == {"test_type": "unit"}

    def test_workflow_state_with_mcp_tool_catalog(self) -> None:
        """Test WorkflowState with MCPToolCatalog integration."""
        context = ExecutionContext(
            task_description="Run tests",
            agent_role="developer",
            user_id="user_123",
        )
        status = WorkflowStatus(state="RUNNING")

        tool_info = MCPToolInfo(
            name="run_tests",
            description="Run unit tests",
            mcp_server="test_server",
            parameters={"type": "object", "properties": {}},
        )
        catalog = MCPToolCatalog(tools=[tool_info])

        state = WorkflowState(
            run_id="run_123",
            status=status,
            context=context,
            available_capabilities=catalog,
        )

        assert state.available_capabilities is not None
        assert len(state.available_capabilities.tools) == 1
        assert state.available_capabilities.tools[0].name == "run_tests"

    def test_workflow_state_decisions_history(self) -> None:
        """Test WorkflowState decisions history."""
        context = ExecutionContext(
            task_description="Run tests",
            agent_role="developer",
            user_id="user_123",
        )
        status = WorkflowStatus(state="RUNNING")

        decisions: list[dict[str, Any]] = [
            {"decision": "approve", "timestamp": "2026-02-09T10:00:00"},
            {"decision": "reject", "timestamp": "2026-02-09T10:05:00"},
        ]

        state = WorkflowState(
            run_id="run_123",
            status=status,
            context=context,
            decisions=decisions,
        )

        assert len(state.decisions) == 2
        assert state.decisions[0]["decision"] == "approve"

    def test_workflow_state_executions_history(self) -> None:
        """Test WorkflowState executions history."""
        context = ExecutionContext(
            task_description="Run tests",
            agent_role="developer",
            user_id="user_123",
        )
        status = WorkflowStatus(state="RUNNING")

        executions: list[dict[str, Any]] = [
            {"action": "run_tests", "result": "passed", "timestamp": "2026-02-09T10:00:00"},
        ]

        state = WorkflowState(
            run_id="run_123",
            status=status,
            context=context,
            executions=executions,
        )

        assert len(state.executions) == 1
        assert state.executions[0]["action"] == "run_tests"

    def test_workflow_state_timestamps(self) -> None:
        """Test WorkflowState timestamp fields."""
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
        )

        assert isinstance(state.created_at, datetime)
        assert isinstance(state.updated_at, datetime)
        assert state.created_at <= state.updated_at

    def test_workflow_state_model_copy(self) -> None:
        """Test WorkflowState model_copy for immutable updates."""
        context = ExecutionContext(
            task_description="Run tests",
            agent_role="developer",
            user_id="user_123",
        )
        status = WorkflowStatus(state="PENDING")

        state1 = WorkflowState(
            run_id="run_123",
            status=status,
            context=context,
        )

        # Create updated copy
        new_status = WorkflowStatus(state="RUNNING")
        state2 = state1.model_copy(update={"status": new_status})

        # Verify original unchanged
        assert state1.status.state == "PENDING"
        # Verify copy updated
        assert state2.status.state == "RUNNING"
        # Verify same run_id
        assert state2.run_id == state1.run_id

    def test_workflow_state_serialization(self) -> None:
        """Test WorkflowState serialization to JSON."""
        context = ExecutionContext(
            task_description="Run tests",
            agent_role="developer",
            user_id="user_123",
        )
        status = WorkflowStatus(state="RUNNING")

        state = WorkflowState(
            run_id="run_123",
            status=status,
            context=context,
        )

        state_dict = state.model_dump()
        assert state_dict["run_id"] == "run_123"
        assert state_dict["status"]["state"] == "RUNNING"
        assert state_dict["context"]["agent_role"] == "developer"

    def test_workflow_state_validation_missing_required_field(self) -> None:
        """Test WorkflowState validation fails with missing required field."""
        with pytest.raises(ValidationError):
            WorkflowState(
                run_id="run_123",
                # Missing status
                context=ExecutionContext(
                    task_description="Run tests",
                    agent_role="developer",
                    user_id="user_123",
                ),
            )

    def test_workflow_state_json_schema(self) -> None:
        """Test WorkflowState JSON schema generation."""
        schema = WorkflowState.model_json_schema()

        assert "properties" in schema
        assert "run_id" in schema["properties"]
        assert "status" in schema["properties"]
        assert "context" in schema["properties"]
        assert "current_proposal" in schema["properties"]
