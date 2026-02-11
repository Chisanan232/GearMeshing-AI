"""Unit tests for orchestrator data models."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from gearmeshing_ai.agent.orchestrator.models import (
    ApprovalDecision,
    ApprovalDecisionRecord,
    ApprovalRequest,
    OrchestratorConfig,
    WorkflowCallbacks,
    WorkflowCheckpoint,
    WorkflowEvent,
    WorkflowEventType,
    WorkflowResult,
    WorkflowStatus,
)


class TestDataModels:
    """Test suite for orchestrator data models."""

    def test_workflow_status_enum(self):
        """Test WorkflowStatus enum."""
        assert WorkflowStatus.PENDING.value == "pending"
        assert WorkflowStatus.RUNNING.value == "running"
        assert WorkflowStatus.AWAITING_APPROVAL.value == "awaiting_approval"
        assert WorkflowStatus.SUCCESS.value == "success"
        assert WorkflowStatus.FAILED.value == "failed"
        assert WorkflowStatus.TIMEOUT.value == "timeout"
        assert WorkflowStatus.CANCELLED.value == "cancelled"

    def test_approval_decision_enum(self):
        """Test ApprovalDecision enum."""
        assert ApprovalDecision.APPROVED.value == "approved"
        assert ApprovalDecision.REJECTED.value == "rejected"
        assert ApprovalDecision.TIMEOUT.value == "timeout"

    def test_workflow_event_type_enum(self):
        """Test WorkflowEventType enum."""
        assert WorkflowEventType.WORKFLOW_STARTED.value == "workflow_started"
        assert WorkflowEventType.APPROVAL_REQUIRED.value == "approval_required"
        assert WorkflowEventType.WORKFLOW_COMPLETED.value == "workflow_completed"

    def test_approval_request_creation(self):
        """Test ApprovalRequest creation."""
        request = ApprovalRequest(
            run_id="run_123",
            operation="deploy",
            risk_level="high",
            description="Deploy to production",
            timeout_seconds=3600,
        )

        assert request.run_id == "run_123"
        assert request.operation == "deploy"
        assert request.risk_level == "high"
        assert request.description == "Deploy to production"
        assert request.timeout_seconds == 3600
        assert isinstance(request.created_at, datetime)

    def test_approval_decision_record_creation(self):
        """Test ApprovalDecisionRecord creation."""
        record = ApprovalDecisionRecord(
            approval_id="approval_123",
            run_id="run_123",
            decision=ApprovalDecision.APPROVED,
            approver_id="manager_123",
            reason="Approved",
        )

        assert record.approval_id == "approval_123"
        assert record.run_id == "run_123"
        assert record.decision == ApprovalDecision.APPROVED
        assert record.approver_id == "manager_123"
        assert record.reason == "Approved"

    def test_workflow_event_creation(self):
        """Test WorkflowEvent creation."""
        event = WorkflowEvent(
            event_type=WorkflowEventType.WORKFLOW_STARTED,
            run_id="run_123",
            payload={"task": "test"},
        )

        assert event.event_type == WorkflowEventType.WORKFLOW_STARTED
        assert event.run_id == "run_123"
        assert event.payload["task"] == "test"
        assert isinstance(event.timestamp, datetime)

    def test_workflow_result_creation(self):
        """Test WorkflowResult creation."""
        result = WorkflowResult(
            run_id="run_123",
            status=WorkflowStatus.SUCCESS,
            output={"result": "success"},
        )

        assert result.run_id == "run_123"
        assert result.status == WorkflowStatus.SUCCESS
        assert result.output["result"] == "success"
        assert isinstance(result.started_at, datetime)

    def test_workflow_checkpoint_creation(self):
        """Test WorkflowCheckpoint creation."""
        checkpoint = WorkflowCheckpoint(
            run_id="run_123",
            state={"step": 1, "data": "test"},
        )

        assert checkpoint.run_id == "run_123"
        assert checkpoint.state["step"] == 1
        assert checkpoint.checkpoint_id is not None
        assert isinstance(checkpoint.created_at, datetime)

    def test_workflow_callbacks_creation(self):
        """Test WorkflowCallbacks creation."""
        def on_event(event):
            pass

        callbacks = WorkflowCallbacks(on_event=on_event)

        assert callbacks.on_event is not None
        assert callable(callbacks.on_event)

    def test_orchestrator_config_creation(self):
        """Test OrchestratorConfig creation."""
        config = OrchestratorConfig(
            default_timeout_seconds=300,
            default_approval_timeout_seconds=3600,
            persistence_backend="database",
            enable_event_logging=True,
            max_retries=3,
            retry_delay_seconds=5,
        )

        assert config.default_timeout_seconds == 300
        assert config.default_approval_timeout_seconds == 3600
        assert config.persistence_backend == "database"
        assert config.enable_event_logging is True
        assert config.max_retries == 3
        assert config.retry_delay_seconds == 5

    def test_orchestrator_config_defaults(self):
        """Test OrchestratorConfig default values."""
        config = OrchestratorConfig()

        assert config.default_timeout_seconds == 300
        assert config.default_approval_timeout_seconds == 3600
        assert config.persistence_backend == "database"
        assert config.enable_event_logging is True
        assert config.max_retries == 3
        assert config.retry_delay_seconds == 5

    def test_workflow_result_with_error(self):
        """Test WorkflowResult with error."""
        result = WorkflowResult(
            run_id="run_123",
            status=WorkflowStatus.FAILED,
            error="Execution failed",
        )

        assert result.status == WorkflowStatus.FAILED
        assert result.error == "Execution failed"
        assert result.output is None

    def test_approval_request_with_metadata(self):
        """Test ApprovalRequest with metadata."""
        metadata = {"priority": "high", "ticket_id": "TICKET-123"}
        request = ApprovalRequest(
            run_id="run_123",
            operation="deploy",
            risk_level="high",
            description="Deploy to production",
            metadata=metadata,
        )

        assert request.metadata["priority"] == "high"
        assert request.metadata["ticket_id"] == "TICKET-123"

    def test_workflow_event_with_approval_request(self):
        """Test WorkflowEvent with approval request."""
        approval_request = ApprovalRequest(
            run_id="run_123",
            operation="deploy",
            risk_level="high",
            description="Deploy to production",
        )

        event = WorkflowEvent(
            event_type=WorkflowEventType.APPROVAL_REQUIRED,
            run_id="run_123",
            approval_request=approval_request,
        )

        assert event.approval_request is not None
        assert event.approval_request.operation == "deploy"
