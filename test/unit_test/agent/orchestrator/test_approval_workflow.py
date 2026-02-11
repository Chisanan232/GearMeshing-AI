"""
Unit tests for ApprovalWorkflow.

Tests approval pause/resume coordination and alternative action execution.
"""

import pytest
import asyncio
from datetime import UTC, datetime
from uuid import uuid4

from gearmeshing_ai.agent.orchestrator.approval_workflow import ApprovalWorkflow
from gearmeshing_ai.agent.orchestrator.models import (
    ApprovalRequest,
    ApprovalDecision,
)
from gearmeshing_ai.agent.orchestrator.persistence import PersistenceManager


@pytest.fixture
def persistence_manager():
    """Create a persistence manager for testing."""
    return PersistenceManager(backend="local")


@pytest.fixture
def approval_workflow(persistence_manager):
    """Create an ApprovalWorkflow for testing."""
    return ApprovalWorkflow(persistence=persistence_manager)


class TestApprovalWorkflowPauseForApproval:
    """Tests for pause_for_approval method."""

    @pytest.mark.asyncio
    async def test_pause_for_approval_creates_event(self, approval_workflow):
        """Test that pause_for_approval creates an approval event."""
        run_id = str(uuid4())
        approval_request = ApprovalRequest(
            run_id=run_id,
            operation="deploy_to_production",
            risk_level="high",
            description="Deploy version 2.0 to production",
        )

        await approval_workflow.pause_for_approval(run_id, approval_request)

        # Verify event was created
        assert run_id in approval_workflow._approval_events

    @pytest.mark.asyncio
    async def test_pause_for_approval_with_timeout(self, approval_workflow):
        """Test pause_for_approval with custom timeout."""
        run_id = str(uuid4())
        approval_request = ApprovalRequest(
            run_id=run_id,
            operation="test_operation",
            risk_level="medium",
            description="Test operation",
        )

        await approval_workflow.pause_for_approval(
            run_id,
            approval_request,
            timeout_seconds=10,
        )

        assert run_id in approval_workflow._approval_events


class TestApprovalWorkflowResumeWithApproval:
    """Tests for resume_with_approval method."""

    @pytest.mark.asyncio
    async def test_resume_with_approval_creates_record(self, approval_workflow):
        """Test that resume_with_approval creates decision record."""
        run_id = str(uuid4())

        decision = await approval_workflow.resume_with_approval(
            run_id=run_id,
            approver_id="manager_123",
            reason="Approved for production",
        )

        assert decision.run_id == run_id
        assert decision.decision == ApprovalDecision.APPROVED
        assert decision.approver_id == "manager_123"
        assert decision.reason == "Approved for production"

    @pytest.mark.asyncio
    async def test_resume_with_approval_signals_event(self, approval_workflow):
        """Test that resume_with_approval signals the approval event."""
        run_id = str(uuid4())
        approval_request = ApprovalRequest(
            run_id=run_id,
            operation="test",
            risk_level="low",
            description="Test",
        )

        # Pause first
        await approval_workflow.pause_for_approval(run_id, approval_request)

        # Resume with approval
        decision = await approval_workflow.resume_with_approval(
            run_id=run_id,
            approver_id="approver",
        )

        # Verify decision was stored
        assert run_id in approval_workflow._approval_decisions
        assert approval_workflow._approval_decisions[run_id].decision == ApprovalDecision.APPROVED

    @pytest.mark.asyncio
    async def test_resume_with_approval_without_reason(self, approval_workflow):
        """Test resume_with_approval without reason."""
        run_id = str(uuid4())

        decision = await approval_workflow.resume_with_approval(
            run_id=run_id,
            approver_id="approver",
        )

        assert decision.reason is None


class TestApprovalWorkflowResumeWithRejection:
    """Tests for resume_with_rejection method."""

    @pytest.mark.asyncio
    async def test_resume_with_rejection_creates_record(self, approval_workflow):
        """Test that resume_with_rejection creates decision record."""
        run_id = str(uuid4())

        decision = await approval_workflow.resume_with_rejection(
            run_id=run_id,
            approver_id="qa_lead",
            alternative_action="run_command: npm test",
            reason="Tests must pass first",
        )

        assert decision.run_id == run_id
        assert decision.decision == ApprovalDecision.REJECTED
        assert decision.approver_id == "qa_lead"
        assert decision.alternative_action == "run_command: npm test"
        assert decision.reason == "Tests must pass first"

    @pytest.mark.asyncio
    async def test_resume_with_rejection_signals_event(self, approval_workflow):
        """Test that resume_with_rejection signals the approval event."""
        run_id = str(uuid4())
        approval_request = ApprovalRequest(
            run_id=run_id,
            operation="test",
            risk_level="low",
            description="Test",
        )

        # Pause first
        await approval_workflow.pause_for_approval(run_id, approval_request)

        # Resume with rejection
        decision = await approval_workflow.resume_with_rejection(
            run_id=run_id,
            approver_id="qa_lead",
            alternative_action="run_command: npm test",
            reason="Tests must pass",
        )

        # Verify decision was stored
        assert run_id in approval_workflow._approval_decisions
        assert approval_workflow._approval_decisions[run_id].decision == ApprovalDecision.REJECTED


class TestApprovalWorkflowWaitForApproval:
    """Tests for wait_for_approval method."""

    @pytest.mark.asyncio
    async def test_wait_for_approval_timeout(self, approval_workflow):
        """Test wait_for_approval timeout."""
        run_id = str(uuid4())

        decision = await approval_workflow.wait_for_approval(
            run_id=run_id,
            timeout_seconds=0.1,  # Very short timeout
        )

        # Should timeout and auto-reject
        assert decision is not None
        assert decision.decision == ApprovalDecision.TIMEOUT

    @pytest.mark.asyncio
    async def test_wait_for_approval_with_decision(self, approval_workflow):
        """Test wait_for_approval when decision is made."""
        run_id = str(uuid4())

        # Create a task to approve after a short delay
        async def approve_after_delay():
            await asyncio.sleep(0.1)
            await approval_workflow.resume_with_approval(
                run_id=run_id,
                approver_id="approver",
            )

        # Start approval task
        asyncio.create_task(approve_after_delay())

        # Wait for approval
        decision = await approval_workflow.wait_for_approval(
            run_id=run_id,
            timeout_seconds=1,
        )

        assert decision is not None
        assert decision.decision == ApprovalDecision.APPROVED

    @pytest.mark.asyncio
    async def test_wait_for_approval_creates_event_if_not_exists(self, approval_workflow):
        """Test that wait_for_approval creates event if not exists."""
        run_id = str(uuid4())

        # Don't pause first, just wait
        # This should timeout quickly
        decision = await approval_workflow.wait_for_approval(
            run_id=run_id,
            timeout_seconds=0.1,
        )

        assert decision is not None


class TestApprovalWorkflowAutoRejectOnTimeout:
    """Tests for _auto_reject_on_timeout method."""

    @pytest.mark.asyncio
    async def test_auto_reject_on_timeout(self, approval_workflow):
        """Test auto-rejection on timeout."""
        run_id = str(uuid4())

        # Create timeout task
        await approval_workflow._auto_reject_on_timeout(run_id, timeout_seconds=0.1)

        # Wait a bit for the timeout to trigger
        await asyncio.sleep(0.2)

        # Verify auto-rejection
        assert run_id in approval_workflow._approval_decisions
        decision = approval_workflow._approval_decisions[run_id]
        assert decision.decision == ApprovalDecision.TIMEOUT

    @pytest.mark.asyncio
    async def test_auto_reject_skips_if_decision_exists(self, approval_workflow):
        """Test that auto-reject skips if decision already made."""
        run_id = str(uuid4())

        # Make a decision first
        await approval_workflow.resume_with_approval(
            run_id=run_id,
            approver_id="approver",
        )

        # Create timeout task
        await approval_workflow._auto_reject_on_timeout(run_id, timeout_seconds=0.1)

        # Wait a bit
        await asyncio.sleep(0.2)

        # Verify decision is still the original one
        decision = approval_workflow._approval_decisions[run_id]
        assert decision.decision == ApprovalDecision.APPROVED


class TestApprovalWorkflowGetApprovalStatus:
    """Tests for get_approval_status method."""

    @pytest.mark.asyncio
    async def test_get_approval_status_pending(self, approval_workflow):
        """Test getting status of pending approval."""
        run_id = str(uuid4())

        status = await approval_workflow.get_approval_status(run_id)

        assert status["run_id"] == run_id
        assert status["status"] == "pending"

    @pytest.mark.asyncio
    async def test_get_approval_status_approved(self, approval_workflow):
        """Test getting status of approved workflow."""
        run_id = str(uuid4())

        await approval_workflow.resume_with_approval(
            run_id=run_id,
            approver_id="approver",
            reason="Approved",
        )

        status = await approval_workflow.get_approval_status(run_id)

        assert status["run_id"] == run_id
        assert status["status"] == "approved"
        assert status["approver_id"] == "approver"

    @pytest.mark.asyncio
    async def test_get_approval_status_rejected(self, approval_workflow):
        """Test getting status of rejected workflow."""
        run_id = str(uuid4())

        await approval_workflow.resume_with_rejection(
            run_id=run_id,
            approver_id="qa_lead",
            alternative_action="run_command: npm test",
            reason="Tests must pass",
        )

        status = await approval_workflow.get_approval_status(run_id)

        assert status["run_id"] == run_id
        assert status["status"] == "rejected"
        assert status["alternative_action"] == "run_command: npm test"


class TestApprovalWorkflowCleanup:
    """Tests for cleanup method."""

    @pytest.mark.asyncio
    async def test_cleanup_removes_event(self, approval_workflow):
        """Test that cleanup removes approval event."""
        run_id = str(uuid4())
        approval_request = ApprovalRequest(
            run_id=run_id,
            operation="test",
            risk_level="low",
            description="Test",
        )

        await approval_workflow.pause_for_approval(run_id, approval_request)
        assert run_id in approval_workflow._approval_events

        await approval_workflow.cleanup(run_id)
        assert run_id not in approval_workflow._approval_events

    @pytest.mark.asyncio
    async def test_cleanup_keeps_decision_record(self, approval_workflow):
        """Test that cleanup keeps decision record for history."""
        run_id = str(uuid4())

        await approval_workflow.resume_with_approval(
            run_id=run_id,
            approver_id="approver",
        )

        await approval_workflow.cleanup(run_id)

        # Decision should still be in history
        assert run_id in approval_workflow._approval_decisions
