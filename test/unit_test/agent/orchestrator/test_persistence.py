"""Unit tests for the persistence manager."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from gearmeshing_ai.agent.orchestrator.persistence import PersistenceManager
from gearmeshing_ai.agent.orchestrator.models import (
    ApprovalDecision,
    ApprovalDecisionRecord,
    ApprovalRequest,
    WorkflowCheckpoint,
    WorkflowEvent,
    WorkflowEventType,
)


class TestPersistenceManager:
    """Test suite for PersistenceManager."""

    @pytest.fixture
    def manager(self):
        """Create a persistence manager for testing."""
        return PersistenceManager(backend="database")

    @pytest.mark.asyncio
    async def test_save_and_get_event(self, manager):
        """Test saving and retrieving events."""
        event = WorkflowEvent(
            event_type=WorkflowEventType.WORKFLOW_STARTED,
            run_id="run_123",
            payload={"task": "test"},
        )

        await manager.save_event(event)
        events = await manager.get_events("run_123")

        assert len(events) == 1
        assert events[0].run_id == "run_123"
        assert events[0].event_type == WorkflowEventType.WORKFLOW_STARTED

    @pytest.mark.asyncio
    async def test_get_events_filters_by_run_id(self, manager):
        """Test that get_events filters by run_id."""
        # Save events for different runs
        for i in range(3):
            event = WorkflowEvent(
                event_type=WorkflowEventType.WORKFLOW_STARTED,
                run_id=f"run_{i}",
            )
            await manager.save_event(event)

        # Get events for specific run
        events = await manager.get_events("run_1")

        assert len(events) == 1
        assert events[0].run_id == "run_1"

    @pytest.mark.asyncio
    async def test_save_and_get_approval_request(self, manager):
        """Test saving and retrieving approval requests."""
        request = ApprovalRequest(
            run_id="run_123",
            operation="deploy",
            risk_level="high",
            description="Deploy to production",
        )

        await manager.save_approval_request(request)
        retrieved = await manager.get_approval_request("run_123")

        assert retrieved is not None
        assert retrieved.run_id == "run_123"
        assert retrieved.operation == "deploy"

    @pytest.mark.asyncio
    async def test_save_and_get_approval_decision(self, manager):
        """Test saving and retrieving approval decisions."""
        decision = ApprovalDecisionRecord(
            approval_id="approval_123",
            run_id="run_123",
            decision=ApprovalDecision.APPROVED,
            approver_id="manager_123",
            reason="Approved",
        )

        await manager.save_approval_decision(decision)
        history = await manager.get_approval_history("run_123")

        assert len(history) == 1
        assert history[0].decision == ApprovalDecision.APPROVED

    @pytest.mark.asyncio
    async def test_get_approval_history_multiple_decisions(self, manager):
        """Test getting approval history with multiple decisions."""
        # Save multiple decisions for same run
        for i in range(3):
            decision = ApprovalDecisionRecord(
                approval_id=f"approval_{i}",
                run_id="run_123",
                decision=ApprovalDecision.APPROVED,
                approver_id=f"manager_{i}",
            )
            await manager.save_approval_decision(decision)

        history = await manager.get_approval_history("run_123")

        assert len(history) == 3

    @pytest.mark.asyncio
    async def test_save_and_get_checkpoint(self, manager):
        """Test saving and retrieving checkpoints."""
        checkpoint = WorkflowCheckpoint(
            run_id="run_123",
            state={"step": 1, "data": "test"},
        )

        await manager.save_checkpoint(checkpoint)
        retrieved = await manager.get_checkpoint("run_123")

        assert retrieved is not None
        assert retrieved.run_id == "run_123"
        assert retrieved.state["step"] == 1

    @pytest.mark.asyncio
    async def test_get_latest_checkpoint(self, manager):
        """Test that get_checkpoint returns the latest checkpoint."""
        # Save multiple checkpoints
        for i in range(3):
            checkpoint = WorkflowCheckpoint(
                run_id="run_123",
                state={"step": i},
            )
            await manager.save_checkpoint(checkpoint)

        retrieved = await manager.get_checkpoint("run_123")

        assert retrieved.state["step"] == 2

    @pytest.mark.asyncio
    async def test_delete_checkpoint(self, manager):
        """Test deleting checkpoints."""
        checkpoint = WorkflowCheckpoint(
            run_id="run_123",
            state={"step": 1},
        )

        await manager.save_checkpoint(checkpoint)
        assert await manager.get_checkpoint("run_123") is not None

        await manager.delete_checkpoint("run_123")
        assert await manager.get_checkpoint("run_123") is None

    @pytest.mark.asyncio
    async def test_clear_all_data(self, manager):
        """Test clearing all persisted data."""
        # Save various data
        event = WorkflowEvent(
            event_type=WorkflowEventType.WORKFLOW_STARTED,
            run_id="run_123",
        )
        await manager.save_event(event)

        request = ApprovalRequest(
            run_id="run_123",
            operation="deploy",
            risk_level="high",
            description="Deploy",
        )
        await manager.save_approval_request(request)

        # Clear
        await manager.clear()

        # Verify cleared
        events = await manager.get_events("run_123")
        assert len(events) == 0

        request = await manager.get_approval_request("run_123")
        assert request is None
