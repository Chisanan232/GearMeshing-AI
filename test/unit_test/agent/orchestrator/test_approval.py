"""Unit tests for the approval handler."""

import asyncio
import pytest
from datetime import datetime

from gearmeshing_ai.agent.orchestrator.approval import ApprovalHandler
from gearmeshing_ai.agent.orchestrator.models import (
    ApprovalDecision,
    ApprovalRequest,
)
from gearmeshing_ai.agent.orchestrator.persistence import PersistenceManager


class TestApprovalHandler:
    """Test suite for ApprovalHandler."""

    @pytest.fixture
    def handler(self):
        """Create an approval handler for testing."""
        persistence = PersistenceManager()
        return ApprovalHandler(persistence_manager=persistence)

    @pytest.mark.asyncio
    async def test_create_approval_request(self, handler):
        """Test creating an approval request."""
        request = await handler.create_approval_request(
            run_id="run_123",
            operation="deploy",
            risk_level="high",
            description="Deploy to production",
            timeout_seconds=3600,
        )

        assert request.run_id == "run_123"
        assert request.operation == "deploy"
        assert request.risk_level == "high"
        assert request.timeout_seconds == 3600

    @pytest.mark.asyncio
    async def test_resolve_approval_approved(self, handler):
        """Test resolving an approval with approval."""
        # Create request
        await handler.create_approval_request(
            run_id="run_123",
            operation="deploy",
            risk_level="high",
            description="Deploy to production",
        )

        # Resolve with approval
        decision = await handler.resolve_approval(
            run_id="run_123",
            decision=ApprovalDecision.APPROVED,
            approver_id="manager_123",
            reason="Approved",
        )

        assert decision.decision == ApprovalDecision.APPROVED
        assert decision.approver_id == "manager_123"

    @pytest.mark.asyncio
    async def test_resolve_approval_rejected(self, handler):
        """Test resolving an approval with rejection."""
        # Create request
        await handler.create_approval_request(
            run_id="run_123",
            operation="deploy",
            risk_level="high",
            description="Deploy to production",
        )

        # Resolve with rejection
        decision = await handler.resolve_approval(
            run_id="run_123",
            decision=ApprovalDecision.REJECTED,
            approver_id="manager_123",
            reason="Not approved",
        )

        assert decision.decision == ApprovalDecision.REJECTED

    @pytest.mark.asyncio
    async def test_wait_for_approval_approved(self, handler):
        """Test waiting for approval that is approved."""
        # Create request
        await handler.create_approval_request(
            run_id="run_123",
            operation="deploy",
            risk_level="high",
            description="Deploy to production",
        )

        # Start waiting for approval in background
        wait_task = asyncio.create_task(
            handler.wait_for_approval(run_id="run_123", timeout_seconds=5)
        )

        # Give it a moment to start waiting
        await asyncio.sleep(0.1)

        # Resolve approval
        await handler.resolve_approval(
            run_id="run_123",
            decision=ApprovalDecision.APPROVED,
            approver_id="manager_123",
        )

        # Wait for result
        result = await wait_task
        assert result == ApprovalDecision.APPROVED

    @pytest.mark.asyncio
    async def test_wait_for_approval_timeout(self, handler):
        """Test waiting for approval that times out."""
        # Create request
        await handler.create_approval_request(
            run_id="run_123",
            operation="deploy",
            risk_level="high",
            description="Deploy to production",
        )

        # Wait for approval with short timeout
        result = await handler.wait_for_approval(
            run_id="run_123",
            timeout_seconds=0.5,
        )

        assert result == ApprovalDecision.TIMEOUT

    @pytest.mark.asyncio
    async def test_get_approval_request(self, handler):
        """Test getting an approval request."""
        await handler.create_approval_request(
            run_id="run_123",
            operation="deploy",
            risk_level="high",
            description="Deploy to production",
        )

        request = await handler.get_approval_request("run_123")
        assert request is not None
        assert request.run_id == "run_123"

    @pytest.mark.asyncio
    async def test_get_approval_history(self, handler):
        """Test getting approval history."""
        # Create request
        await handler.create_approval_request(
            run_id="run_123",
            operation="deploy",
            risk_level="high",
            description="Deploy to production",
        )

        # Resolve approval
        await handler.resolve_approval(
            run_id="run_123",
            decision=ApprovalDecision.APPROVED,
            approver_id="manager_123",
        )

        # Get history
        history = await handler.get_approval_history("run_123")
        assert len(history) == 1
        assert history[0].decision == ApprovalDecision.APPROVED

    @pytest.mark.asyncio
    async def test_is_approval_pending(self, handler):
        """Test checking if approval is pending."""
        # Initially not pending
        assert not await handler.is_approval_pending("run_123")

        # Create request
        await handler.create_approval_request(
            run_id="run_123",
            operation="deploy",
            risk_level="high",
            description="Deploy to production",
        )

        # Now pending
        assert await handler.is_approval_pending("run_123")

        # Resolve approval
        await handler.resolve_approval(
            run_id="run_123",
            decision=ApprovalDecision.APPROVED,
            approver_id="manager_123",
        )

        # Still pending (cleanup not called)
        assert await handler.is_approval_pending("run_123")

    @pytest.mark.asyncio
    async def test_cleanup(self, handler):
        """Test cleanup of approval state."""
        # Create request
        await handler.create_approval_request(
            run_id="run_123",
            operation="deploy",
            risk_level="high",
            description="Deploy to production",
        )

        assert await handler.is_approval_pending("run_123")

        # Cleanup
        await handler.cleanup("run_123")

        assert not await handler.is_approval_pending("run_123")

    @pytest.mark.asyncio
    async def test_multiple_concurrent_approvals(self, handler):
        """Test handling multiple concurrent approval requests."""
        # Create multiple requests
        for i in range(3):
            await handler.create_approval_request(
                run_id=f"run_{i}",
                operation="deploy",
                risk_level="high",
                description=f"Deploy {i}",
            )

        # Wait for all approvals
        wait_tasks = [
            asyncio.create_task(
                handler.wait_for_approval(run_id=f"run_{i}", timeout_seconds=5)
            )
            for i in range(3)
        ]

        await asyncio.sleep(0.1)

        # Approve all
        for i in range(3):
            await handler.resolve_approval(
                run_id=f"run_{i}",
                decision=ApprovalDecision.APPROVED,
                approver_id=f"manager_{i}",
            )

        # Check results
        results = await asyncio.gather(*wait_tasks)
        assert all(r == ApprovalDecision.APPROVED for r in results)
