"""Integration tests for approval workflows."""

import asyncio
import pytest

from gearmeshing_ai.agent.orchestrator.engine import OrchestratorEngine
from gearmeshing_ai.agent.orchestrator.models import (
    ApprovalDecision,
    OrchestratorConfig,
    WorkflowStatus,
    WorkflowEventType,
)
from gearmeshing_ai.agent.orchestrator.persistence import PersistenceManager
from gearmeshing_ai.agent.orchestrator.approval import ApprovalHandler


class TestApprovalWorkflow:
    """Integration tests for approval workflows."""

    @pytest.fixture
    def engine(self):
        """Create an orchestrator engine for testing."""
        config = OrchestratorConfig(
            default_timeout_seconds=10,
            default_approval_timeout_seconds=5,
        )
        return OrchestratorEngine(config=config)

    @pytest.mark.asyncio
    async def test_approval_pause_and_resume(self, engine):
        """Test workflow pause for approval and resume."""
        # Start workflow that requires approval
        result = await engine.run_workflow(
            task_description="Deploy to production",
            approval_timeout_seconds=10,
        )

        run_id = result.run_id
        assert result.status == WorkflowStatus.AWAITING_APPROVAL
        assert result.approval_request is not None

        # Submit approval
        decision = await engine.submit_approval(
            run_id=run_id,
            approved=True,
            approver_id="manager_123",
        )

        assert decision.decision == ApprovalDecision.APPROVED

    @pytest.mark.asyncio
    async def test_approval_rejection(self, engine):
        """Test workflow rejection on approval denial."""
        # Start workflow that requires approval
        result = await engine.run_workflow(
            task_description="Delete database",
            approval_timeout_seconds=10,
        )

        run_id = result.run_id
        assert result.status == WorkflowStatus.AWAITING_APPROVAL

        # Reject approval
        decision = await engine.submit_approval(
            run_id=run_id,
            approved=False,
            approver_id="manager_123",
            reason="Not approved at this time",
        )

        assert decision.decision == ApprovalDecision.REJECTED

    @pytest.mark.asyncio
    async def test_approval_timeout_auto_reject(self, engine):
        """Test approval timeout with auto-reject."""
        # Start workflow with short approval timeout
        result = await engine.run_workflow(
            task_description="Deploy to production",
            approval_timeout_seconds=1,
        )

        run_id = result.run_id
        assert result.status == WorkflowStatus.AWAITING_APPROVAL

        # Simulate timeout by waiting and then checking
        await asyncio.sleep(0.5)
        
        # Try to wait for approval with timeout
        decision = await engine.approval_handler.wait_for_approval(
            run_id=run_id,
            timeout_seconds=1,
        )
        
        assert decision == ApprovalDecision.TIMEOUT

        # Check approval history
        history = await engine.get_approval_history(run_id)
        assert len(history) > 0
        assert history[-1].decision == ApprovalDecision.TIMEOUT

    @pytest.mark.asyncio
    async def test_concurrent_approval_requests(self, engine):
        """Test handling multiple concurrent approval requests."""
        # Start multiple workflows
        tasks = [
            engine.run_workflow(
                task_description=f"Deploy {i}",
                approval_timeout_seconds=10,
            )
            for i in range(3)
        ]

        results = await asyncio.gather(*tasks)

        # All should be awaiting approval
        for result in results:
            assert result.status == WorkflowStatus.AWAITING_APPROVAL

        # Approve all
        for result in results:
            await engine.submit_approval(
                run_id=result.run_id,
                approved=True,
                approver_id="manager_123",
            )

        # Check all approvals
        for result in results:
            history = await engine.get_approval_history(result.run_id)
            assert len(history) > 0
            assert history[0].decision == ApprovalDecision.APPROVED

    @pytest.mark.asyncio
    async def test_approval_event_streaming(self, engine):
        """Test approval events in streaming mode."""
        events = []

        async def collect_events():
            async for event in engine.run_workflow_streaming(
                task_description="Deploy to production",
                approval_timeout_seconds=10,
            ):
                events.append(event)

        # Start streaming in background
        task = asyncio.create_task(collect_events())

        # Give it time to reach approval
        await asyncio.sleep(0.5)

        # Get the run_id from active workflows
        run_id = list(engine._active_workflows.keys())[0]

        # Submit approval
        await engine.submit_approval(
            run_id=run_id,
            approved=True,
            approver_id="manager_123",
        )

        # Wait for task to complete
        try:
            await asyncio.wait_for(task, timeout=5)
        except asyncio.TimeoutError:
            pass

        # Check for approval events
        approval_events = [
            e for e in events
            if e.event_type == WorkflowEventType.APPROVAL_REQUIRED
        ]
        assert len(approval_events) > 0

    @pytest.mark.asyncio
    async def test_approval_with_metadata(self, engine):
        """Test approval with custom metadata."""
        result = await engine.run_workflow(
            task_description="Deploy to production",
            approval_timeout_seconds=10,
        )

        run_id = result.run_id

        # Submit approval with metadata
        decision = await engine.submit_approval(
            run_id=run_id,
            approved=True,
            approver_id="manager_123",
            reason="Approved for testing",
        )

        assert decision.approver_id == "manager_123"
        assert decision.reason == "Approved for testing"

    @pytest.mark.asyncio
    async def test_approval_history_persistence(self, engine):
        """Test that approval history is persisted."""
        result = await engine.run_workflow(
            task_description="Deploy to production",
            approval_timeout_seconds=10,
        )

        run_id = result.run_id

        # Submit multiple decisions
        await engine.submit_approval(
            run_id=run_id,
            approved=True,
            approver_id="manager_123",
        )

        # Get history
        history = await engine.get_approval_history(run_id)

        assert len(history) > 0
        assert history[0].decision == ApprovalDecision.APPROVED

    @pytest.mark.asyncio
    async def test_workflow_without_approval_requirement(self, engine):
        """Test workflow that doesn't require approval."""
        result = await engine.run_workflow(
            task_description="Simple task",
            timeout_seconds=10,
        )

        assert result.status == WorkflowStatus.SUCCESS
        assert result.approval_request is None

    @pytest.mark.asyncio
    async def test_approval_with_different_risk_levels(self, engine):
        """Test approval requests with different risk levels."""
        # High risk operation
        result_high = await engine.run_workflow(
            task_description="Deploy to production",
            approval_timeout_seconds=10,
        )

        assert result_high.status == WorkflowStatus.AWAITING_APPROVAL
        assert result_high.approval_request.risk_level == "high"

        # Low risk operation
        result_low = await engine.run_workflow(
            task_description="Simple task",
            timeout_seconds=10,
        )

        assert result_low.status == WorkflowStatus.SUCCESS
