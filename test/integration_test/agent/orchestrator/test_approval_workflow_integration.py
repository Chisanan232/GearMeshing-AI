"""
Integration tests for approval workflow.

Tests complete approval workflow scenarios end-to-end.
"""

import asyncio
from uuid import uuid4

import pytest

from gearmeshing_ai.agent.orchestrator.approval_workflow import ApprovalWorkflow
from gearmeshing_ai.agent.orchestrator.models import (
    ApprovalDecision,
    ApprovalRequest,
)
from gearmeshing_ai.agent.orchestrator.persistence import PersistenceManager
from gearmeshing_ai.agent.orchestrator.service import OrchestratorService


@pytest.fixture
def persistence_manager() -> PersistenceManager:
    """Create a persistence manager for testing."""
    return PersistenceManager(backend="local")


@pytest.fixture
def orchestrator_service(persistence_manager: PersistenceManager) -> OrchestratorService:
    """Create an OrchestratorService for testing."""
    return OrchestratorService(persistence=persistence_manager)


@pytest.fixture
def approval_workflow(persistence_manager: PersistenceManager) -> ApprovalWorkflow:
    """Create an ApprovalWorkflow for testing."""
    return ApprovalWorkflow(persistence=persistence_manager)


class TestApprovalWorkflowIntegration:
    """Integration tests for approval workflow scenarios."""

    @pytest.mark.asyncio
    async def test_approve_workflow_end_to_end(
        self, approval_workflow: ApprovalWorkflow, persistence_manager: PersistenceManager
    ) -> None:
        """Test complete approve workflow end-to-end."""
        run_id = str(uuid4())
        approval_request = ApprovalRequest(
            run_id=run_id,
            operation="deploy_to_production",
            risk_level="high",
            description="Deploy version 2.0 to production",
        )

        # 1. Pause for approval
        await approval_workflow.pause_for_approval(run_id, approval_request)
        assert run_id in approval_workflow._approval_events

        # 2. Approve workflow
        decision = await approval_workflow.resume_with_approval(
            run_id=run_id,
            approver_id="manager_456",
            reason="Approved for production deployment",
        )

        # 3. Verify decision
        assert decision.decision == ApprovalDecision.APPROVED
        assert decision.approver_id == "manager_456"

        # 4. Verify persisted
        history = await persistence_manager.get_approval_history(run_id=run_id)
        assert len(history) > 0

    @pytest.mark.asyncio
    async def test_reject_workflow_with_alternative_end_to_end(
        self, approval_workflow: ApprovalWorkflow, persistence_manager: PersistenceManager
    ) -> None:
        """Test complete reject workflow with alternative end-to-end."""
        run_id = str(uuid4())
        approval_request = ApprovalRequest(
            run_id=run_id,
            operation="deploy_to_production",
            risk_level="high",
            description="Deploy version 2.0 to production",
        )

        # 1. Pause for approval
        await approval_workflow.pause_for_approval(run_id, approval_request)

        # 2. Reject with alternative
        decision = await approval_workflow.resume_with_rejection(
            run_id=run_id,
            approver_id="qa_lead_456",
            alternative_action="run_command: npm test",
            reason="Tests must pass first - running full test suite",
        )

        # 3. Verify decision
        assert decision.decision == ApprovalDecision.REJECTED
        assert decision.alternative_action == "run_command: npm test"

        # 4. Verify persisted
        history = await persistence_manager.get_approval_history(run_id=run_id)
        assert len(history) > 0

    @pytest.mark.asyncio
    async def test_multiple_approvals_in_workflow(
        self, approval_workflow: ApprovalWorkflow, persistence_manager: PersistenceManager
    ) -> None:
        """Test workflow with multiple approval points."""
        run_id_1 = str(uuid4())
        run_id_2 = str(uuid4())

        # First approval point
        approval_req_1 = ApprovalRequest(
            run_id=run_id_1,
            operation="test_operation_1",
            risk_level="medium",
            description="First operation",
        )
        await approval_workflow.pause_for_approval(run_id_1, approval_req_1)
        await approval_workflow.resume_with_approval(
            run_id=run_id_1,
            approver_id="approver_1",
        )

        # Second approval point
        approval_req_2 = ApprovalRequest(
            run_id=run_id_2,
            operation="test_operation_2",
            risk_level="high",
            description="Second operation",
        )
        await approval_workflow.pause_for_approval(run_id_2, approval_req_2)
        await approval_workflow.resume_with_approval(
            run_id=run_id_2,
            approver_id="approver_2",
        )

        # Verify both approvals
        history_1 = await persistence_manager.get_approval_history(run_id=run_id_1)
        history_2 = await persistence_manager.get_approval_history(run_id=run_id_2)

        assert len(history_1) > 0
        assert len(history_2) > 0

    @pytest.mark.asyncio
    async def test_approval_with_persistence(
        self, approval_workflow: ApprovalWorkflow, persistence_manager: PersistenceManager
    ) -> None:
        """Test approval workflow with state persistence."""
        run_id = str(uuid4())

        # Save approval request
        approval_request = ApprovalRequest(
            run_id=run_id,
            operation="test_operation",
            risk_level="medium",
            description="Test operation",
        )
        await persistence_manager.save_approval_request(run_id, approval_request)

        # Approve
        decision = await approval_workflow.resume_with_approval(
            run_id=run_id,
            approver_id="approver",
        )

        # Persist decision
        await persistence_manager.save_approval_decision(decision)

        # Retrieve history
        history = await persistence_manager.get_approval_history(run_id=run_id)
        assert len(history) > 0
        assert history[0]["approver_id"] == "approver"

    @pytest.mark.asyncio
    async def test_approval_timeout_and_auto_rejection(self, approval_workflow: ApprovalWorkflow) -> None:
        """Test approval timeout and auto-rejection."""
        run_id = str(uuid4())

        # Wait for approval with very short timeout
        decision = await approval_workflow.wait_for_approval(
            run_id=run_id,
            timeout_seconds=0.1,
        )

        # Should timeout and auto-reject
        assert decision is not None
        assert decision.decision == ApprovalDecision.TIMEOUT
        assert decision.approver_id == "system"

    @pytest.mark.asyncio
    async def test_approval_decision_precedence(self, approval_workflow: ApprovalWorkflow) -> None:
        """Test that explicit decision takes precedence over auto-rejection."""
        run_id = str(uuid4())

        # Create approval task
        async def approve_before_timeout():
            await asyncio.sleep(0.05)
            await approval_workflow.resume_with_approval(
                run_id=run_id,
                approver_id="approver",
            )

        # Start approval task
        asyncio.create_task(approve_before_timeout())

        # Wait for approval with longer timeout
        decision = await approval_workflow.wait_for_approval(
            run_id=run_id,
            timeout_seconds=1,
        )

        # Should get explicit approval, not timeout
        assert decision is not None
        assert decision.decision == ApprovalDecision.APPROVED
        assert decision.approver_id == "approver"

    @pytest.mark.asyncio
    async def test_alternative_action_execution_in_rejection(self, orchestrator_service: OrchestratorService) -> None:
        """Test alternative action execution in rejection workflow."""
        run_id = str(uuid4())

        # Execute alternative action
        result = await orchestrator_service._execute_alternative_action("run_command: npm test")

        assert result["status"] == "executed"
        assert result["command"] == "npm test"

    @pytest.mark.asyncio
    async def test_skip_step_alternative_action(self, orchestrator_service: OrchestratorService) -> None:
        """Test skip_step alternative action."""
        run_id = str(uuid4())

        result = await orchestrator_service._execute_alternative_action("skip_step")

        assert result["status"] == "skipped"
        assert result["action"] == "skip_step"

    @pytest.mark.asyncio
    async def test_approval_history_filtering(
        self, approval_workflow: ApprovalWorkflow, persistence_manager: PersistenceManager
    ) -> None:
        """Test approval history filtering by various criteria."""
        # Create multiple approvals
        for i in range(3):
            run_id = str(uuid4())
            await approval_workflow.resume_with_approval(
                run_id=run_id,
                approver_id="approver_1" if i < 2 else "approver_2",
            )
            await persistence_manager.save_approval_decision(approval_workflow._approval_decisions[run_id])

        # Filter by approver
        history = await persistence_manager.get_approval_history(approver_id="approver_1")
        assert len(history) >= 2

        # Filter by status
        history = await persistence_manager.get_approval_history(status="approved")
        assert len(history) >= 3

    @pytest.mark.asyncio
    async def test_workflow_state_persistence_with_approval(
        self, orchestrator_service: OrchestratorService, persistence_manager: PersistenceManager
    ) -> None:
        """Test workflow state persistence with approval."""
        run_id = str(uuid4())

        # Save workflow state
        mock_state = {
            "run_id": run_id,
            "status": "awaiting_approval",
            "context": {"task": "test"},
        }
        await persistence_manager.save_workflow_state(run_id, mock_state)

        # Load workflow state
        loaded_state = await persistence_manager.load_workflow_state(run_id)
        assert loaded_state is not None
        assert loaded_state["run_id"] == run_id
        assert loaded_state["status"] == "awaiting_approval"

    @pytest.mark.asyncio
    async def test_cancellation_workflow(
        self, orchestrator_service: OrchestratorService, persistence_manager: PersistenceManager
    ) -> None:
        """Test workflow cancellation."""
        run_id = str(uuid4())

        # Save cancellation
        cancellation = {
            "run_id": run_id,
            "canceller_id": "user_123",
            "reason": "User requested cancellation",
        }
        await persistence_manager.save_cancellation(cancellation)

        # Verify cancellation was saved
        # (Note: get_cancellations not yet implemented in persistence)
        # This test verifies the interface works

    @pytest.mark.asyncio
    async def test_approval_workflow_cleanup(self, approval_workflow: ApprovalWorkflow) -> None:
        """Test approval workflow cleanup."""
        run_id = str(uuid4())
        approval_request = ApprovalRequest(
            run_id=run_id,
            operation="test",
            risk_level="low",
            description="Test",
        )

        # Pause
        await approval_workflow.pause_for_approval(run_id, approval_request)
        assert run_id in approval_workflow._approval_events

        # Approve
        await approval_workflow.resume_with_approval(
            run_id=run_id,
            approver_id="approver",
        )

        # Cleanup
        await approval_workflow.cleanup(run_id)

        # Event should be removed
        assert run_id not in approval_workflow._approval_events

        # Decision should still be in history
        assert run_id in approval_workflow._approval_decisions
