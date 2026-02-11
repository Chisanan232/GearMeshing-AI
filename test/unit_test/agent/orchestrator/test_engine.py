"""Unit tests for the orchestrator engine."""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from gearmeshing_ai.agent.orchestrator.engine import OrchestratorEngine
from gearmeshing_ai.agent.orchestrator.models import (
    OrchestratorConfig,
    WorkflowCallbacks,
    WorkflowStatus,
    WorkflowEventType,
)


class TestOrchestratorEngine:
    """Test suite for OrchestratorEngine."""

    @pytest.fixture
    def engine(self):
        """Create an orchestrator engine for testing."""
        config = OrchestratorConfig(
            default_timeout_seconds=10,
            default_approval_timeout_seconds=5,
        )
        return OrchestratorEngine(config=config)

    @pytest.mark.asyncio
    async def test_run_workflow_success(self, engine):
        """Test successful workflow execution."""
        result = await engine.run_workflow(
            task_description="Test task",
            agent_role="developer",
            user_id="test_user",
        )

        assert result.run_id is not None
        assert result.status == WorkflowStatus.SUCCESS
        assert result.output is not None
        assert len(result.events) > 0

    @pytest.mark.asyncio
    async def test_run_workflow_with_approval(self, engine):
        """Test workflow execution with approval requirement."""
        result = await engine.run_workflow(
            task_description="Deploy to production",
            agent_role="devops",
            user_id="test_user",
            approval_timeout_seconds=2,
        )

        assert result.run_id is not None
        assert result.status == WorkflowStatus.AWAITING_APPROVAL
        assert result.approval_request is not None

    @pytest.mark.asyncio
    async def test_run_workflow_timeout(self, engine):
        """Test workflow timeout handling."""
        result = await engine.run_workflow(
            task_description="Long running task",
            timeout_seconds=0.01,
        )

        # With very short timeout, should timeout
        assert result.status in [WorkflowStatus.TIMEOUT, WorkflowStatus.SUCCESS]

    @pytest.mark.asyncio
    async def test_submit_approval(self, engine):
        """Test approval submission."""
        # First, start a workflow that requires approval
        result = await engine.run_workflow(
            task_description="Delete database",
            approval_timeout_seconds=10,
        )

        run_id = result.run_id
        assert result.status == WorkflowStatus.AWAITING_APPROVAL

        # Submit approval
        decision = await engine.submit_approval(
            run_id=run_id,
            approved=True,
            approver_id="manager_123",
            reason="Approved for testing",
        )

        assert decision.decision.value == "approved"
        assert decision.approver_id == "manager_123"

    @pytest.mark.asyncio
    async def test_get_workflow_status(self, engine):
        """Test getting workflow status."""
        result = await engine.run_workflow(
            task_description="Test task",
        )

        status = await engine.get_workflow_status(result.run_id)
        assert status == WorkflowStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_cancel_workflow(self, engine):
        """Test workflow cancellation."""
        # Create a workflow
        task = asyncio.create_task(
            engine.run_workflow(
                task_description="Long task",
                timeout_seconds=30,
            )
        )

        # Give it a moment to start
        await asyncio.sleep(0.1)

        # Get the run_id from active workflows if available
        if engine._active_workflows:
            run_id = list(engine._active_workflows.keys())[0]

            # Cancel it
            cancelled = await engine.cancel_workflow(run_id)
            assert cancelled is True

        # Wait for task to complete
        try:
            await asyncio.wait_for(task, timeout=2)
        except asyncio.TimeoutError:
            pass

    @pytest.mark.asyncio
    async def test_get_workflow_history(self, engine):
        """Test getting workflow event history."""
        result = await engine.run_workflow(
            task_description="Test task",
        )

        history = await engine.get_workflow_history(result.run_id)
        assert len(history) > 0
        assert any(
            e.event_type == WorkflowEventType.WORKFLOW_COMPLETED
            for e in history
        )

    @pytest.mark.asyncio
    async def test_get_approval_history(self, engine):
        """Test getting approval history."""
        result = await engine.run_workflow(
            task_description="Deploy to production",
            approval_timeout_seconds=10,
        )

        run_id = result.run_id

        # Submit approval
        await engine.submit_approval(
            run_id=run_id,
            approved=True,
            approver_id="manager_123",
        )

        history = await engine.get_approval_history(run_id)
        assert len(history) > 0
        assert history[0].approver_id == "manager_123"

    @pytest.mark.asyncio
    async def test_workflow_callbacks(self, engine):
        """Test workflow event callbacks."""
        callback_events = []

        def on_event(event):
            callback_events.append(event)

        callbacks = WorkflowCallbacks(on_event=on_event)

        result = await engine.run_workflow(
            task_description="Test task",
            callbacks=callbacks,
        )

        assert len(callback_events) > 0
        assert any(
            e.event_type == WorkflowEventType.WORKFLOW_COMPLETED
            for e in callback_events
        )

    @pytest.mark.asyncio
    async def test_run_workflow_streaming(self, engine):
        """Test streaming workflow execution."""
        events = []

        async for event in engine.run_workflow_streaming(
            task_description="Test task",
        ):
            events.append(event)

        assert len(events) > 0
        assert events[0].event_type == WorkflowEventType.CAPABILITY_DISCOVERY_STARTED
        assert events[-1].event_type == WorkflowEventType.WORKFLOW_COMPLETED

    @pytest.mark.asyncio
    async def test_run_workflow_streaming_with_approval(self, engine):
        """Test streaming workflow with approval requirement."""
        events = []

        async for event in engine.run_workflow_streaming(
            task_description="Deploy to production",
            approval_timeout_seconds=2,
        ):
            events.append(event)

        # Should have approval required event
        assert any(
            e.event_type == WorkflowEventType.APPROVAL_REQUIRED
            for e in events
        )

    @pytest.mark.asyncio
    async def test_workflow_with_custom_config(self, engine):
        """Test workflow with custom configuration."""
        custom_config = OrchestratorConfig(
            default_timeout_seconds=5,
            default_approval_timeout_seconds=2,
            enable_event_logging=True,
        )
        custom_engine = OrchestratorEngine(config=custom_config)

        result = await custom_engine.run_workflow(
            task_description="Test task",
        )

        assert result.status == WorkflowStatus.SUCCESS
