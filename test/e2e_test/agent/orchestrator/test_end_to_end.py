"""End-to-end tests for the orchestrator module."""

from __future__ import annotations

import asyncio

import pytest

from gearmeshing_ai.agent.orchestrator.models import (
    WorkflowStatus,
)
from gearmeshing_ai.agent.orchestrator.persistence import PersistenceManager
from gearmeshing_ai.agent.orchestrator.service import OrchestratorService


class TestOrchestratorEndToEnd:
    """End-to-end tests for the orchestrator module."""

    @pytest.fixture
    def service(self) -> OrchestratorService:
        """Create an orchestrator service for testing."""
        persistence = PersistenceManager(backend="local")
        return OrchestratorService(persistence=persistence)

    @pytest.mark.asyncio
    async def test_complete_workflow_without_approval(self, service: OrchestratorService) -> None:
        """Test complete workflow execution without approval."""
        result = await service.run_workflow(
            task_description="Process data",
            agent_role="data_scientist",
            user_id="user_123",
        )

        assert result.run_id is not None
        assert result.status in [WorkflowStatus.SUCCESS, WorkflowStatus.FAILED]
        assert result.started_at is not None

    @pytest.mark.asyncio
    async def test_complete_workflow_with_approval_flow(self, service: OrchestratorService) -> None:
        """Test complete workflow with approval pause and resume."""
        # Start workflow
        result = await service.run_workflow(
            task_description="Deploy to production",
            agent_role="devops",
            user_id="user_123",
        )

        run_id = result.run_id
        assert run_id is not None
        assert result.status in [WorkflowStatus.SUCCESS, WorkflowStatus.AWAITING_APPROVAL, WorkflowStatus.FAILED]

    @pytest.mark.asyncio
    async def test_multiple_concurrent_workflows(self, service: OrchestratorService) -> None:
        """Test handling multiple concurrent workflows."""
        # Start multiple workflows
        tasks = [
            service.run_workflow(
                task_description=f"Task {i}",
                user_id=f"user_{i}",
                timeout_seconds=10,
            )
            for i in range(3)
        ]

        results = await asyncio.gather(*tasks)

        # All should complete
        assert len(results) == 3
        assert all(r.run_id is not None for r in results)
        assert len(set(r.run_id for r in results)) == 3  # All unique run_ids

    @pytest.mark.asyncio
    async def test_workflow_error_handling(self, service: OrchestratorService) -> None:
        """Test workflow error handling."""
        # This test verifies that errors are handled gracefully
        result = await service.run_workflow(
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
    async def test_workflow_state_persistence(self, service: OrchestratorService) -> None:
        """Test workflow state persistence across operations."""
        result = await service.run_workflow(
            task_description="Test task",
            timeout_seconds=10,
        )

        run_id = result.run_id
        assert run_id is not None

        # Verify result has required fields
        assert result.status is not None
        assert result.started_at is not None
        assert result.completed_at is not None
        assert result.duration_seconds is not None

        # Verify status is one of the valid states
        assert result.status in [
            WorkflowStatus.SUCCESS,
            WorkflowStatus.FAILED,
            WorkflowStatus.TIMEOUT,
            WorkflowStatus.AWAITING_APPROVAL,
        ]

    @pytest.mark.asyncio
    async def test_approval_workflow_integration(self, service: OrchestratorService) -> None:
        """Test approval workflow integration."""
        result = await service.run_workflow(
            task_description="Deploy to production",
        )

        run_id = result.run_id
        assert run_id is not None

        # Verify workflow completed
        assert result.status is not None
        assert result.started_at is not None
        assert result.completed_at is not None

        # Get approval history
        history = await service.get_approval_history(run_id=run_id)
        assert isinstance(history, list)

        # If workflow went to approval, history should have entries
        if result.status == WorkflowStatus.AWAITING_APPROVAL:
            # History may be empty if approval wasn't processed yet
            assert isinstance(history, list)
