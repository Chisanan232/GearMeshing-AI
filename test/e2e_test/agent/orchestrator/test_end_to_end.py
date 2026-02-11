"""End-to-end tests for the orchestrator module."""

import asyncio
import pytest

from gearmeshing_ai.agent.orchestrator.engine import OrchestratorEngine
from gearmeshing_ai.agent.orchestrator.models import (
    ApprovalDecision,
    OrchestratorConfig,
    WorkflowStatus,
    WorkflowEventType,
)


class TestOrchestratorEndToEnd:
    """End-to-end tests for the orchestrator module."""

    @pytest.fixture
    def engine(self):
        """Create an orchestrator engine for testing."""
        config = OrchestratorConfig(
            default_timeout_seconds=30,
            default_approval_timeout_seconds=10,
            enable_event_logging=True,
        )
        return OrchestratorEngine(config=config)

    @pytest.mark.asyncio
    async def test_complete_workflow_without_approval(self, engine):
        """Test complete workflow execution without approval."""
        result = await engine.run_workflow(
            task_description="Process data",
            agent_role="data_scientist",
            user_id="user_123",
        )

        assert result.run_id is not None
        assert result.status == WorkflowStatus.SUCCESS
        assert result.output is not None
        assert len(result.events) > 0

        # Verify event sequence
        event_types = [e.event_type for e in result.events]
        assert WorkflowEventType.WORKFLOW_STARTED in event_types
        assert WorkflowEventType.CAPABILITY_DISCOVERY_STARTED in event_types
        assert WorkflowEventType.WORKFLOW_COMPLETED in event_types

    @pytest.mark.asyncio
    async def test_complete_workflow_with_approval_flow(self, engine):
        """Test complete workflow with approval pause and resume."""
        # Start workflow
        result = await engine.run_workflow(
            task_description="Deploy to production",
            agent_role="devops",
            user_id="user_123",
            approval_timeout_seconds=10,
        )

        run_id = result.run_id
        assert result.status == WorkflowStatus.AWAITING_APPROVAL
        assert result.approval_request is not None

        # Verify approval request details
        approval_req = result.approval_request
        assert approval_req.run_id == run_id
        assert approval_req.operation == "risky_operation"
        assert approval_req.risk_level == "high"

        # Submit approval
        decision = await engine.submit_approval(
            run_id=run_id,
            approved=True,
            approver_id="manager_123",
            reason="Approved for production deployment",
        )

        assert decision.decision == ApprovalDecision.APPROVED

        # Get workflow history
        history = await engine.get_workflow_history(run_id)
        assert len(history) > 0

        # Get approval history
        approval_history = await engine.get_approval_history(run_id)
        assert len(approval_history) > 0
        assert approval_history[0].approver_id == "manager_123"

    @pytest.mark.asyncio
    async def test_streaming_workflow_with_approval(self, engine):
        """Test streaming workflow with approval requirement."""
        events = []
        run_id = None

        async def collect_events():
            nonlocal run_id
            async for event in engine.run_workflow_streaming(
                task_description="Deploy to production",
                agent_role="devops",
                user_id="user_123",
                approval_timeout_seconds=10,
            ):
                events.append(event)
                if run_id is None and event.run_id:
                    run_id = event.run_id

        # Start streaming in background
        task = asyncio.create_task(collect_events())

        # Wait for approval event
        await asyncio.sleep(0.5)

        # Submit approval
        if run_id:
            await engine.submit_approval(
                run_id=run_id,
                approved=True,
                approver_id="manager_123",
            )

        # Wait for completion
        try:
            await asyncio.wait_for(task, timeout=5)
        except asyncio.TimeoutError:
            pass

        # Verify events
        assert len(events) > 0
        event_types = [e.event_type for e in events]
        assert WorkflowEventType.APPROVAL_REQUIRED in event_types

    @pytest.mark.asyncio
    async def test_workflow_cancellation(self, engine):
        """Test workflow cancellation."""
        # Start a long-running workflow
        task = asyncio.create_task(
            engine.run_workflow(
                task_description="Long running task",
                timeout_seconds=30,
            )
        )

        # Give it time to start
        await asyncio.sleep(0.1)

        # Get run_id if available
        if engine._active_workflows:
            run_id = list(engine._active_workflows.keys())[0]

            # Cancel it
            cancelled = await engine.cancel_workflow(run_id)
            assert cancelled is True

        # Wait for task
        try:
            await asyncio.wait_for(task, timeout=2)
        except asyncio.TimeoutError:
            pass

    @pytest.mark.asyncio
    async def test_multiple_concurrent_workflows(self, engine):
        """Test handling multiple concurrent workflows."""
        # Start multiple workflows
        tasks = [
            engine.run_workflow(
                task_description=f"Task {i}",
                user_id=f"user_{i}",
                timeout_seconds=10,
            )
            for i in range(5)
        ]

        results = await asyncio.gather(*tasks)

        # All should complete successfully
        assert len(results) == 5
        assert all(r.status == WorkflowStatus.SUCCESS for r in results)
        assert len(set(r.run_id for r in results)) == 5  # All unique run_ids

    @pytest.mark.asyncio
    async def test_workflow_with_callbacks(self, engine):
        """Test workflow execution with event callbacks."""
        callback_log = []

        def on_event(event):
            callback_log.append({
                "type": event.event_type.value,
                "run_id": event.run_id,
            })

        from gearmeshing_ai.agent.orchestrator.models import WorkflowCallbacks

        callbacks = WorkflowCallbacks(on_event=on_event)

        result = await engine.run_workflow(
            task_description="Test task",
            callbacks=callbacks,
        )

        assert result.status == WorkflowStatus.SUCCESS
        assert len(callback_log) > 0

        # Verify callback events
        event_types = [e["type"] for e in callback_log]
        assert "workflow_started" in event_types
        assert "workflow_completed" in event_types

    @pytest.mark.asyncio
    async def test_workflow_error_handling(self, engine):
        """Test workflow error handling."""
        # This test verifies that errors are handled gracefully
        result = await engine.run_workflow(
            task_description="Test task",
            timeout_seconds=10,
        )

        # Should complete (either success or with proper error handling)
        assert result.run_id is not None
        assert result.status in [
            WorkflowStatus.SUCCESS,
            WorkflowStatus.FAILED,
            WorkflowStatus.TIMEOUT,
        ]

    @pytest.mark.asyncio
    async def test_workflow_state_persistence(self, engine):
        """Test workflow state persistence across operations."""
        result = await engine.run_workflow(
            task_description="Test task",
            timeout_seconds=10,
        )

        run_id = result.run_id

        # Get status
        status = await engine.get_workflow_status(run_id)
        assert status == WorkflowStatus.SUCCESS

        # Get history
        history = await engine.get_workflow_history(run_id)
        assert len(history) > 0

        # Verify events are persisted
        event_types = [e.event_type for e in history]
        assert WorkflowEventType.WORKFLOW_COMPLETED in event_types

    @pytest.mark.asyncio
    async def test_approval_timeout_scenario(self, engine):
        """Test approval timeout scenario."""
        result = await engine.run_workflow(
            task_description="Deploy to production",
            approval_timeout_seconds=1,
        )

        run_id = result.run_id
        assert result.status == WorkflowStatus.AWAITING_APPROVAL

        # Simulate timeout by waiting for approval with timeout
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
    async def test_approval_rejection_scenario(self, engine):
        """Test approval rejection scenario."""
        result = await engine.run_workflow(
            task_description="Delete database",
            approval_timeout_seconds=10,
        )

        run_id = result.run_id

        # Reject approval
        decision = await engine.submit_approval(
            run_id=run_id,
            approved=False,
            approver_id="manager_123",
            reason="Not approved at this time",
        )

        assert decision.decision == ApprovalDecision.REJECTED

        # Get approval history
        history = await engine.get_approval_history(run_id)
        assert len(history) > 0
        assert history[0].decision == ApprovalDecision.REJECTED
        assert history[0].reason == "Not approved at this time"
